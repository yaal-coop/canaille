import json
from http import HTTPStatus

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.integrations.flask_oauth2.errors import (
    _HTTPException as AuthlibHTTPException,
)
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import Blueprint
from flask import Response
from flask import abort
from flask import request
from pydantic import ValidationError
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SearchRequest
from werkzeug.exceptions import HTTPException

from canaille import csrf
from canaille.app import models
from canaille.backends import Backend

from .models import Group
from .models import User
from .models import get_resource_types
from .models import get_schemas
from .models import get_service_provider_config
from .models import group_from_canaille_to_scim
from .models import group_from_scim_to_canaille
from .models import user_from_canaille_to_scim
from .models import user_from_scim_to_canaille

bp = Blueprint("scim", __name__, url_prefix="/scim/v2")


class SCIMBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string: str):
        token = Backend.instance.get(models.Token, access_token=token_string)
        # At the moment, only client tokens are allowed, and not user tokens
        return token if token and not token.subject else None


require_oauth = ResourceProtector()
require_oauth.register_token_validator(SCIMBearerTokenValidator())


@bp.after_request
def add_scim_content_type(response):
    response.headers["Content-Type"] = "application/scim+json"
    return response


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    obj = Error(detail=str(error), status=error.code)
    return obj.model_dump(), obj.status


@bp.errorhandler(AuthlibHTTPException)
def oauth2_error(error):
    body = json.loads(error.body)
    obj = Error(
        detail=f"{body['error']}: {body['error_description']}"
        if "error_description" in body
        else body["error"],
        status=error.code,
    )
    return obj.model_dump(), error.code


@bp.errorhandler(ValidationError)
def scim_error_handler(error):
    error_details = error.errors()[0]
    obj = Error(status=400, detail=error_details["msg"])
    # TODO: maybe the Pydantic <=> SCIM error code mapping could go in scim2_models
    obj.scim_type = (
        "invalidValue" if error_details["type"] == "required_error" else None
    )

    return obj.model_dump(), obj.status


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


@bp.route("/Users", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_users():
    req = parse_search_request(request)
    users = list(
        Backend.instance.query(models.User)[req.start_index_0 : req.stop_index_0]
    )
    total = len(users)
    scim_users = [user_from_canaille_to_scim(user) for user in users]
    list_response = ListResponse[User[EnterpriseUser]](
        start_index=req.start_index,
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
    groups = list(
        Backend.instance.query(models.group)[req.start_index_0 : req.stop_index_0]
    )
    total = len(groups)
    scim_groups = [group_from_canaille_to_scim(group) for group in groups]
    list_response = ListResponse[Group](
        start_index=req.start_index,
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
    schemas = list(get_schemas().values())[req.start_index_0 : req.stop_index_0]
    response = ListResponse[Schema](
        total_results=len(schemas),
        items_per_page=req.count or len(schemas),
        start_index=req.start_index,
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
    resource_types = list(get_resource_types().values())[
        req.start_index_0 : req.stop_index_0
    ]
    response = ListResponse[ResourceType](
        total_results=len(resource_types),
        items_per_page=req.count or len(resource_types),
        start_index=req.start_index,
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
    spc = get_service_provider_config()
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
    original_scim_user = user_from_canaille_to_scim(user)
    request_scim_user = User[EnterpriseUser].model_validate(
        request.json,
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
        original=original_scim_user,
    )
    updated_user = user_from_scim_to_canaille(request_scim_user, user)
    Backend.instance.save(updated_user)
    response_scim_user = user_from_canaille_to_scim(updated_user)
    payload = response_scim_user.model_dump(
        scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
    )
    return payload


@bp.route("/Groups/<group:group>", methods=["PUT"])
@csrf.exempt
@require_oauth()
def replace_group(group):
    original_scim_group = group_from_canaille_to_scim(group)
    request_scim_group = Group.model_validate(
        request.json,
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
        original=original_scim_group,
    )
    updated_group = group_from_scim_to_canaille(request_scim_group, group)
    Backend.instance.save(updated_group)
    response_group = group_from_canaille_to_scim(updated_group)
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
