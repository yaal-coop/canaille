from flask import current_app
from flask import url_for
from httpx import Client as httpx_client
from scim2_client import SCIMClientError
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_models import EnterpriseUser
from scim2_models import Group
from scim2_models import Meta
from scim2_models import SearchRequest
from scim2_models import User

from canaille.app import models
from canaille.backends import Backend


def user_from_canaille_to_scim_client(
    user, user_class=User, enterprise_user_class=EnterpriseUser
):
    # allow to use custom SCIM user classes if needed
    scim_user_class = user_class if user_class != User else User[EnterpriseUser]
    scim_user = scim_user_class(
        meta=Meta(
            resource_type="User",
            created=user.created,
            last_modified=user.last_modified,
            location=url_for("scim.query_user", user=user, _external=True),
        ),
        external_id=user.id,
        user_name=user.user_name,
        preferred_language=user.preferred_language,
        name=user_class.Name(
            formatted=user.formatted_name,
            family_name=user.family_name,
            given_name=user.given_name,
        )
        if (user.formatted_name or user.family_name or user.given_name)
        else None,
        display_name=user.display_name,
        title=user.title,
        profile_url=user.profile_url,
        emails=[
            user_class.Emails(
                value=email,
                primary=email == user.emails[0],
            )
            for email in user.emails or []
        ]
        or None,
        phone_numbers=[
            user_class.PhoneNumbers(
                value=phone_number, primary=phone_number == user.phone_numbers[0]
            )
            for phone_number in user.phone_numbers or []
        ]
        or None,
        addresses=[
            user_class.Addresses(
                formatted=user.formatted_address,
                street_address=user.street,
                postal_code=user.postal_code,
                locality=user.locality,
                region=user.region,
                primary=True,
            )
        ]
        if (
            user.formatted_address
            or user.street
            or user.postal_code
            or user.locality
            or user.region
        )
        else None,
        photos=[
            user_class.Photos(
                value=url_for(
                    "core.account.photo", user=user, field="photo", _external=True
                ),
                primary=True,
                type=user_class.Photos.Type.photo,
            )
        ]
        if user.photo
        else None,
        groups=[
            user_class.Groups(
                value=group.id,
                display=group.display_name,
                ref=url_for("scim.query_group", group=group, _external=True),
            )
            for group in user.groups or []
        ]
        or None,
    )
    if enterprise_user_class:
        scim_user[enterprise_user_class] = enterprise_user_class(
            employee_number=user.employee_number,
            organization=user.organization,
            department=user.department,
        )
    return scim_user


def group_from_canaille_to_scim_client(group, group_class=Group):
    return group_class(
        meta=Meta(
            resource_type="Group",
            created=group.created,
            last_modified=group.last_modified,
            location=url_for("scim.query_group", group=group, _external=True),
        ),
        external_id=group.id,
        display_name=group.display_name,
        members=[
            group_class.Members(
                value=user.id,
                type="User",
                display=user.display_name,
                ref=url_for("scim.query_user", user=user, _external=True),
            )
            for user in group.members or []
        ]
        or None,
    )


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
        # TODO : récupérer infos chaque member pour constituer l'objet
        group = group_from_canaille_to_scim_client(group, Group)
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
        if isinstance(member, models.User):
            notifiable_clients.update(get_clients(member))

    for client in notifiable_clients:
        scim = initiate_scim_client(client)
        if scim:
            execute_scim_group_action(scim, group, client.client_name, method)


def get_clients(user):
    if user.id:
        consents = Backend.instance.query(models.Consent, subject=user)
        consented_clients = {t.client for t in consents}
        preconsented_clients = [
            client
            for client in Backend.instance.query(models.Client)
            if client.preconsent and client not in consented_clients
        ]
        return list(consented_clients) + list(preconsented_clients)
    return []
