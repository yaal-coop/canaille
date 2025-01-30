from flask import current_app
from flask import url_for
from httpx import Client as httpx_client
from scim2_client import SCIMClientError
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import ChangePassword
from scim2_models import EnterpriseUser
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import Group
from scim2_models import Meta
from scim2_models import Mutability
from scim2_models import Patch
from scim2_models import Required
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SchemaExtension
from scim2_models import SearchRequest
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import User

from canaille.app import DOCUMENTATION_URL
from canaille.app import models
from canaille.backends import Backend

# At the difference of SCIM User, Canaille User need a 'family_name'
# (because the LDAP 'sn' is mandatory) and the 'user_name'
# attribute is immutable (because it is part of the LDAP DN).
user_schema = User.to_schema()
user_schema["name"].required = Required.true
user_schema["name"]["familyName"].required = Required.true
user_schema["userName"].mutability = Mutability.immutable
User = Resource.from_schema(user_schema)

# At the difference of the SCIM Group, Canaille Group must have a display_name.
# and 'members' cannot be null.
group_schema = Group.to_schema()
group_schema["displayName"].required = Required.true
group_schema["displayName"].mutability = Mutability.immutable
group_schema["members"].required = Required.true
group_schema["members"]["value"].required = Required.true
group_schema["members"]["$ref"].required = Required.true
Group = Resource.from_schema(group_schema)


def get_service_provider_config():
    return ServiceProviderConfig(
        meta=Meta(
            resource_type="ServiceProviderConfig",
            location=url_for("scim.query_service_provider_config", _external=True),
        ),
        documentation_uri=DOCUMENTATION_URL,
        patch=Patch(supported=False),
        bulk=Bulk(supported=False, max_operations=0, max_payload_size=0),
        change_password=ChangePassword(supported=True),
        filter=Filter(supported=False, max_results=0),
        sort=Sort(supported=False),
        etag=ETag(supported=False),
        authentication_schemes=[
            AuthenticationScheme(
                name="OAuth Bearer Token",
                description="Authentication scheme using the OAuth Bearer Token Standard",
                spec_uri="http://www.rfc-editor.org/info/rfc6750",
                documentation_uri=DOCUMENTATION_URL,
                type="oauthbearertoken",
                primary=True,
            ),
        ],
    )


def get_resource_types():
    """Return the resource types implemented by Canaille."""
    return {
        "User": ResourceType(
            id="User",
            name="User",
            endpoint=url_for("scim.query_users", _external=True),
            description="User accounts",
            schema_="urn:ietf:params:scim:schemas:core:2.0:User",
            schema_extensions=[
                SchemaExtension(
                    schema_="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    required=True,
                )
            ],
            meta=Meta(
                resource_type="ResourceType",
                location=url_for(
                    "scim.query_resource_type",
                    resource_type_name="User",
                    _external=True,
                ),
            ),
        ),
        "Group": ResourceType(
            id="Group",
            name="Group",
            endpoint=url_for("scim.query_groups", _external=True),
            description="Group management",
            schema_="urn:ietf:params:scim:schemas:core:2.0:Group",
            meta=Meta(
                resource_type="ResourceType",
                location=url_for(
                    "scim.query_resource_type",
                    resource_type_name="Group",
                    _external=True,
                ),
            ),
        ),
    }


def get_schemas():
    schemas = {
        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig": ServiceProviderConfig.to_schema(),
        "urn:ietf:params:scim:schemas:core:2.0:ResourceType": ResourceType.to_schema(),
        "urn:ietf:params:scim:schemas:core:2.0:Schema": Schema.to_schema(),
        "urn:ietf:params:scim:schemas:core:2.0:User": User.to_schema(),
        "urn:ietf:params:scim:schemas:core:2.0:Group": Group.to_schema(),
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": EnterpriseUser.to_schema(),
    }
    for schema_id, schema in schemas.items():
        schema.meta = Meta(
            resource_type="Schema",
            location=url_for("scim.query_schema", schema_id=schema_id, _external=True),
        )
    return schemas


def user_from_canaille_to_scim(
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
        id=user.id,
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


# TODO : Rajouter external id dans function custom


def user_from_scim_to_canaille(scim_user: User, user):
    user.user_name = scim_user.user_name
    user.password = scim_user.password
    user.preferred_language = scim_user.preferred_language
    user.formatted_name = scim_user.name.formatted if scim_user.name else None
    user.family_name = scim_user.name.family_name if scim_user.name else None
    user.given_name = scim_user.name.given_name if scim_user.name else None
    user.display_name = scim_user.display_name
    user.title = scim_user.title
    user.profile_url = scim_user.profile_url
    user.emails = [email.value for email in scim_user.emails or []] or None
    user.phone_numbers = [
        phone_number.value for phone_number in scim_user.phone_numbers or []
    ] or None
    user.formatted_address = (
        scim_user.addresses[0].formatted if scim_user.addresses else None
    )
    user.street = scim_user.addresses[0].street_address if scim_user.addresses else None
    user.postal_code = (
        scim_user.addresses[0].postal_code if scim_user.addresses else None
    )
    user.locality = scim_user.addresses[0].locality if scim_user.addresses else None
    user.region = scim_user.addresses[0].region if scim_user.addresses else None
    # TODO: delete the photo
    # if scim_user.photos and scim_user.photos[0].value:
    #    user.photo = scim_user.photos[0].value
    user.employee_number = (
        scim_user[EnterpriseUser].employee_number if scim_user[EnterpriseUser] else None
    )
    user.organization = (
        scim_user[EnterpriseUser].organization if scim_user[EnterpriseUser] else None
    )
    user.department = (
        scim_user[EnterpriseUser].department if scim_user[EnterpriseUser] else None
    )
    user.groups = [
        Backend.instance.get(models.Group, group.value)
        for group in scim_user.groups or []
        if group.value
    ]
    return user


def group_from_canaille_to_scim(group, group_class=Group):
    return group_class(
        id=group.id,
        meta=Meta(
            resource_type="Group",
            created=group.created,
            last_modified=group.last_modified,
            location=url_for("scim.query_group", group=group, _external=True),
        ),
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


def group_from_scim_to_canaille(scim_group: Group, group):
    group.display_name = scim_group.display_name

    members = []
    for member in scim_group.members or []:
        # extract the user identifier from scim/v2/Users/<identifier>
        identifier = member.ref.split("/")[-1]
        members.append(Backend.instance.get(models.User, identifier))

    group.members = members

    return group


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

    req = SearchRequest(filter=f'userName eq "{user.user_name}"')
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
        scim_user = user_from_canaille_to_scim(user, User, EnterpriseUser)
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
    groups = scim.query(Group)

    scim_group = None
    if groups.resources:
        scim_group = next(
            (
                mygroup
                for mygroup in groups.resources
                if mygroup.display_name == group.display_name
            ),
            None,
        )

    if method == "delete" and scim_group:
        try:
            scim.delete(Group, scim_group.id)
        except Exception:
            current_app.logger.warning(
                f"SCIM Group {group.display_name} delete for client {client_name} failed"
            )
    elif method == "save":  # pragma: no branch
        # TODO : récupérer infos chaque member pour constituer l'objet
        group = group_from_canaille_to_scim(group, Group)
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
