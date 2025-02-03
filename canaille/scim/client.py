from blinker import signal
from flask import current_app
from httpx import Client as httpx_client
from scim2_client import SCIMClientError
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_models import SearchRequest

from canaille.app import models
from canaille.backends import Backend
from canaille.scim.models import group_from_canaille_to_scim
from canaille.scim.models import user_from_canaille_to_scim


def user_from_canaille_to_scim_client(user, user_class, enterprise_user_class):
    scim_user = user_from_canaille_to_scim(user, user_class, enterprise_user_class)
    scim_user.external_id = user.id
    return scim_user


def group_from_canaille_to_scim_client(group, group_class, scim_client):
    scim_group = group_from_canaille_to_scim(group, group_class)
    scim_group.external_id = group.id

    distant_members = []
    User = scim_client.get_resource_model("User")
    for member in group.members:
        req = SearchRequest(filter=f'externalId eq "{member.id}"')
        response = scim_client.query(User, search_request=req)
        if response.resources:
            distant_members.append(response.resources[0])

    scim_group.members = [
        group_class.Members(
            value=user.id,
            type="User",
            display=user.display_name,
            ref=user.meta.location,
        )
        for user in distant_members or []
    ] or None

    return scim_group


def initiate_scim_client(client):
    if not client:  # pragma: no cover
        return None

    client_httpx = httpx_client(
        base_url=client.client_uri,
        headers={"Authorization": f"Bearer {client.get_access_token().access_token}"},
    )
    scim = SyncSCIMClient(client_httpx)
    try:
        scim.discover()
    except SCIMClientError:
        current_app.logger.info(
            f"SCIM protocol not supported by client {client.client_name}"
        )
        return None
    return scim


def execute_scim_user_action(scim, user, client_name, method):
    User = scim.get_resource_model("User")

    req = SearchRequest(filter=f'externalId eq "{user.id}"')
    response = scim.query(User, search_request=req)
    distant_scim_user = response.resources[0] if response.resources else None

    if method == "delete" and distant_scim_user:
        try:
            scim.delete(User, distant_scim_user.id)
        except:
            current_app.logger.warning(
                f"SCIM User {user.user_name} delete for client {client_name} failed"
            )
    elif method == "save":
        EnterpriseUser = User.get_extension_model("EnterpriseUser")
        scim_user = user_from_canaille_to_scim_client(user, User, EnterpriseUser)
        if not distant_scim_user:
            try:
                scim.create(scim_user)
            except Exception:
                current_app.logger.warning(
                    f"SCIM User {user.user_name} creation for client {client_name} failed"
                )
        else:
            scim_user.id = distant_scim_user.id
            try:
                scim.replace(scim_user)
            except Exception:
                current_app.logger.warning(
                    f"SCIM User {user.user_name} update for client {client_name} failed"
                )


def propagate_user_scim_modification(user, method):
    for client in get_clients(user):
        scim = initiate_scim_client(client)
        if scim:
            execute_scim_user_action(scim, user, client.client_name, method)


def execute_scim_group_action(scim, group, client_name, method):
    Group = scim.get_resource_model("Group")

    req = SearchRequest(filter=f'externalId eq "{group.id}"')
    response = scim.query(Group, search_request=req)
    scim_group = response.resources[0] if response.resources else None

    if method == "delete" and scim_group:
        try:
            scim.delete(Group, scim_group.id)
        except Exception:
            current_app.logger.warning(
                f"SCIM Group {group.display_name} delete for client {client_name} failed"
            )
    elif method == "save":  # pragma: no branch
        group = group_from_canaille_to_scim_client(group, Group, scim)
        if not scim_group:
            try:
                scim.create(group)
            except Exception:
                current_app.logger.warning(
                    f"SCIM Group {group.display_name} creation for client {client_name} failed"
                )
        else:
            group.id = scim_group.id
            try:
                scim.replace(group)
            except Exception:
                current_app.logger.warning(
                    f"SCIM Group {group.display_name} update for client {client_name} failed"
                )


def propagate_group_scim_modification(group, method):
    notifiable_clients = set()
    for member in group.members:
        notifiable_clients.update(get_clients(member))

    for client in notifiable_clients:
        scim = initiate_scim_client(client)
        if scim:
            execute_scim_group_action(scim, group, client.client_name, method)


def get_clients(user):
    consents = Backend.instance.query(models.Consent, subject=user)
    consented_clients = {t.client for t in consents}
    preconsented_clients = [
        client
        for client in Backend.instance.query(models.Client)
        if client.preconsent and client not in consented_clients
    ]
    return list(consented_clients) + list(preconsented_clients)


def after_user_save(user):
    propagate_user_scim_modification(user, method="save")

    for group in set(user.old_groups) ^ set(user.groups):
        Backend.instance.reload(group)
        propagate_group_scim_modification(group, "save")


def before_user_delete(user):
    propagate_user_scim_modification(user, method="delete")


def after_user_delete(user):
    for group in user.groups:
        Backend.instance.reload(group)
        propagate_group_scim_modification(group, "save")


def after_group_save(group):
    propagate_group_scim_modification(group, method="save")


def before_group_delete(group):
    propagate_group_scim_modification(group, method="delete")


def setup_scim_signals():
    signal("after_user_save").connect(after_user_save)
    signal("before_user_delete").connect(before_user_delete)
    signal("after_user_delete").connect(after_user_delete)
    signal("after_group_save").connect(after_group_save)
    signal("before_group_delete").connect(before_group_delete)
