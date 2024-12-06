from http import HTTPStatus

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import Blueprint
from flask import Response
from flask import abort
from flask import request
from flask import url_for
from scim2_models import Address
from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import ChangePassword
from scim2_models import Context
from scim2_models import Email
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import Group
from scim2_models import GroupMember
from scim2_models import GroupMembership
from scim2_models import ListResponse
from scim2_models import Meta
from scim2_models import Name
from scim2_models import Patch
from scim2_models import PhoneNumber
from scim2_models import Photo
from scim2_models import Required
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import User
from werkzeug.exceptions import HTTPException

from canaille import csrf
from canaille.app import models
from canaille.backends import Backend

bp = Blueprint("scim", __name__, url_prefix="/scim")

# At the difference of the SCIM Group, Canaille Group must have a display_name
group_schema = Group.to_schema()
group_schema.attributes[0].required = Required.true
Group = Resource.from_schema(group_schema)


class SCIMBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string: str):
        token = Backend.instance.get(models.Token, access_token=token_string)
        return token if token and not token.subject else None


require_oauth = ResourceProtector()
require_oauth.register_token_validator(SCIMBearerTokenValidator())


@bp.after_request
def add_scim_content_type(response):
    response.headers["Content-Type"] = "application/scim+json"
    return response


@bp.errorhandler(HTTPException)
def scim_error_handler(error):
    return Error(detail=str(error), status=error.code).model_dump(), error.code


def parse_search_request(request) -> SearchRequest:
    """Create a SearchRequest object from the request arguments."""
    max_nb_items_per_page = 1000
    count = (
        min(request.args["count"], max_nb_items_per_page)
        if request.args.get("count")
        else None
    )
    req = SearchRequest(
        attributes=request.args.get("attributes"),
        excluded_attributes=request.args.get("excludedAttributes"),
        start_index=request.args.get("startIndex"),
        count=count,
    )
    return req


def get_resource_types():
    """The resource types implemented by Canaille."""

    return {
        "User": ResourceType(
            id="User",
            name="User",
            endpoint=url_for("scim.query_users", _external=True),
            description="User accounts",
            schema_="urn:ietf:params:scim:schemas:core:2.0:User",
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


def user_from_canaille_to_scim(user):
    scim_user = User[EnterpriseUser](
        meta=Meta(
            resource_type="User",
            created=user.created,
            last_modified=user.last_modified,
            location=url_for("scim.query_user", user=user, _external=True),
        ),
        id=user.id,
        user_name=user.user_name,
        # password=user.password,
        preferred_language=user.preferred_language,
        name=Name(
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
            Email(
                value=email,
                primary=email == user.emails[0],
            )
            for email in user.emails or []
        ]
        or None,
        phone_numbers=[
            PhoneNumber(
                value=phone_number, primary=phone_number == user.phone_numbers[0]
            )
            for phone_number in user.phone_numbers or []
        ]
        or None,
        addresses=[
            Address(
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
            Photo(
                value=url_for(
                    "core.account.photo", user=user, field="photo", _external=True
                ),
                primary=True,
                type=Photo.Type.photo,
            )
        ]
        if user.photo
        else None,
        groups=[
            GroupMembership(
                value=group.id,
                display=group.display_name,
                ref=url_for("scim.query_group", group=group, _external=True),
            )
            for group in user.groups or []
        ]
        or None,
    )
    scim_user[EnterpriseUser] = EnterpriseUser(
        employee_number=user.employee_number,
        organization=user.organization,
        department=user.department,
    )
    return scim_user


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


def group_from_canaille_to_scim(group):
    return Group(
        id=group.id,
        meta=Meta(
            resource_type="Group",
            created=group.created,
            last_modified=group.last_modified,
            location=url_for("scim.query_group", group=group, _external=True),
        ),
        display_name=group.display_name,
        members=[
            GroupMember(
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
        Backend.instance.get(models.User, member.value)
    group.members = members

    return group


@bp.route("/Users", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_users():
    req = parse_search_request(request)
    start_index_1 = req.start_index or 1
    start_index_0 = (start_index_1 - 1) or None
    stop_index_0 = (start_index_1 + req.count - 1) if req.count else None
    users = list(Backend.instance.query(models.User)[start_index_0:stop_index_0])
    total = len(users)
    scim_users = [user_from_canaille_to_scim(user) for user in users]
    list_response = ListResponse[User[EnterpriseUser]](
        start_index=start_index_1,
        items_per_page=req.count,
        total_results=total,
        resources=scim_users,
    )
    payload = list_response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
    )
    return payload


@bp.route("/Users/<user:user>", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_user(user):
    scim_user = user_from_canaille_to_scim(user)
    return scim_user.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
    )


@bp.route("/Groups", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_groups():
    req = parse_search_request(request)
    start_index_1 = req.start_index or 1
    start_index_0 = (start_index_1 - 1) or None
    stop_index_0 = (start_index_1 + req.count - 1) if req.count else None
    groups = list(Backend.instance.query(models.group)[start_index_0:stop_index_0])
    total = len(groups)
    scim_groups = [group_from_canaille_to_scim(group) for group in groups]
    list_response = ListResponse[Group](
        start_index=start_index_1,
        items_per_page=req.count,
        total_results=total,
        resources=scim_groups,
    )
    payload = list_response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
    )
    return payload


@bp.route("/Groups/<group:group>", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_group(group):
    scim_group = group_from_canaille_to_scim(group)
    return scim_group.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
    )


@bp.route("/Schemas", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_schemas():
    req = parse_search_request(request)
    start_index_1 = req.start_index or 1
    start_index_0 = (start_index_1 - 1) or None
    stop_index_0 = (start_index_1 + req.count - 1) if req.count else None
    schemas = list(get_schemas().values())[start_index_0:stop_index_0]
    response = ListResponse[Schema](
        total_results=len(schemas),
        items_per_page=req.count or len(schemas),
        start_index=start_index_1,
        resources=schemas,
    )
    return response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@bp.route("/Schemas/<string:schema_id>", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_schema(schema_id):
    schema = get_schemas().get(schema_id)
    if not schema:
        abort(404)

    return schema.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@bp.route("/ResourceTypes", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_resource_types():
    req = parse_search_request(request)
    start_index_1 = req.start_index or 1
    start_index_0 = (start_index_1 - 1) or None
    stop_index_0 = (start_index_1 + req.count - 1) if req.count else None
    resource_types = list(get_resource_types().values())[start_index_0:stop_index_0]
    response = ListResponse[ResourceType](
        total_results=len(resource_types),
        items_per_page=req.count or len(resource_types),
        start_index=start_index_1,
        resources=resource_types,
    )
    return response.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@bp.route("/ResourceTypes/<string:resource_type_name>", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_resource_type(resource_type_name):
    resource_type = get_resource_types().get(resource_type_name)
    if not resource_type:
        abort(404)

    return resource_type.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@bp.route("/ServiceProviderConfig", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_service_provider_config():
    spc = ServiceProviderConfig(
        meta=Meta(
            resource_type="ServiceProviderConfig",
            location=url_for("scim.query_service_provider_config", _external=True),
        ),
        documentation_uri="https://canaille.readthedocs.io",
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
                documentation_uri="https://canaille.readthedocs.io",
                type="oauthbearertoken",
                primary=True,
            ),
        ],
    )
    return spc.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE)


@bp.route("/Users", methods=["POST"])
@csrf.exempt
@require_oauth()
def create_user():
    request_user = User[EnterpriseUser].model_validate(
        request.json, scim_ctx=Context.RESOURCE_CREATION_REQUEST
    )
    user = user_from_scim_to_canaille(request_user, models.User())
    Backend.instance.save(user)
    response_user = user_from_canaille_to_scim(user)
    payload = response_user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE)
    return Response(payload, status=HTTPStatus.CREATED)


@bp.route("/Groups", methods=["POST"])
@csrf.exempt
@require_oauth()
def create_group():
    request_group = Group.model_validate(
        request.json, scim_ctx=Context.RESOURCE_CREATION_REQUEST
    )
    group = group_from_scim_to_canaille(request_group, models.Group())
    Backend.instance.save(group)
    response_group = group_from_canaille_to_scim(group)
    payload = response_group.model_dump_json(
        scim_ctx=Context.RESOURCE_CREATION_RESPONSE
    )
    return Response(payload, status=HTTPStatus.CREATED)


@bp.route("/Users/<user:user>", methods=["PUT"])
@csrf.exempt
@require_oauth()
def replace_user(user):
    request_user = User[EnterpriseUser].model_validate(
        request.json, scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST
    )
    user = user_from_scim_to_canaille(request_user, user)
    Backend.instance.save(user)
    response_user = user_from_canaille_to_scim(user)
    payload = response_user.model_dump(scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE)
    return payload


@bp.route("/Groups/<group:group>", methods=["PUT"])
@csrf.exempt
@require_oauth()
def replace_group(group):
    request_group = Group.model_validate(
        request.json, scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST
    )
    group = group_from_scim_to_canaille(request_group, group)
    Backend.instance.save(group)
    response_group = group_from_canaille_to_scim(group)
    payload = response_group.model_dump(scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE)
    return payload


@bp.route("/Users/<user:user>", methods=["DELETE"])
@csrf.exempt
@require_oauth()
def delete_user(user):
    Backend.instance.delete(user)
    return "", HTTPStatus.NO_CONTENT


@bp.route("/Groups/<group:group>", methods=["DELETE"])
@csrf.exempt
@require_oauth()
def delete_group(group):
    Backend.instance.delete(group)
    return "", HTTPStatus.NO_CONTENT
