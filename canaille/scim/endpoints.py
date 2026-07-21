import json
from functools import wraps
from http import HTTPStatus

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.integrations.flask_oauth2 import current_token
from authlib.integrations.flask_oauth2.errors import (
    _HTTPException as AuthlibHTTPException,
)
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import Blueprint
from flask import abort
from flask import current_app
from flask import request
from pydantic import ValidationError
from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import BulkResponse
from scim2_models import Context
from scim2_models import Error
from scim2_models import ListResponse
from scim2_models import PatchOp
from scim2_models import ResourceType
from scim2_models import ResponseParameters
from scim2_models import Schema
from scim2_models import SearchRequest
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import PreconditionFailed

from canaille.app import models
from canaille.app.flask import csrf
from canaille.backends import Backend
from canaille.core.configuration import Permission

from .casting import group_from_canaille_to_scim_server
from .casting import group_from_scim_to_canaille
from .casting import make_etag
from .casting import user_from_canaille_to_scim_server
from .casting import user_from_scim_to_canaille
from .models import EnterpriseUser
from .models import Group
from .models import User
from .models import get_resource_types
from .models import get_schemas
from .models import get_service_provider_config

bp = Blueprint("scim", __name__, url_prefix="/scim/v2")


class SCIMBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string: str):
        return Backend.instance.get(models.Token, access_token=token_string)


require_oauth = ResourceProtector()
require_oauth.register_token_validator(SCIMBearerTokenValidator())


def require_permission(permission):
    """Check that user tokens have the required Canaille permission.

    Client tokens (without subject) bypass this check.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_token.subject and not current_token.subject.can(permission):
                err = Error(detail="Insufficient permissions", status=403)
                return err.model_dump(), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


@bp.after_request
def add_scim_content_type(response):
    response.headers["Content-Type"] = "application/scim+json"
    return response


@bp.after_request
def set_etag_header(response):
    """Extract ``ETag`` from ``meta.version`` and handle conditional responses."""
    data = response.get_json(silent=True)
    if meta := (data or {}).get("meta"):
        if version := meta.get("version"):
            response.headers["ETag"] = version
    response.make_conditional(request)
    return response


@bp.before_request
def check_etag():
    """Verify ``If-Match`` on write operations."""
    if request.method not in ("PUT", "PATCH", "DELETE"):
        return
    arg = next(iter(request.view_args.values()), None)
    if not arg:
        return
    if_match = request.headers.get("If-Match")
    if not if_match:
        return
    if if_match.strip() == "*":
        return
    etag = make_etag(arg)
    tags = [t.strip() for t in if_match.split(",")]
    if etag not in tags:
        raise PreconditionFailed("ETag mismatch")


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
    obj = Error.from_validation_error(error.errors()[0])
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


def _query_resources(canaille_model, scim_type, to_scim):
    req = parse_search_request(request)
    total = Backend.instance.count(canaille_model)
    resources = list(
        Backend.instance.query(canaille_model)[req.start_index_0 : req.stop_index_0]
    )
    scim_resources = [to_scim(r) for r in resources]
    list_response = ListResponse[scim_type](
        start_index=req.start_index,
        items_per_page=req.count,
        total_results=total,
        resources=scim_resources,
    )
    return list_response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


def _query_resource(resource, to_scim):
    req = ResponseParameters.model_validate(request.args.to_dict())
    scim_resource = to_scim(resource)
    return scim_resource.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


def _create_resource(scim_type, canaille_model, to_scim, from_scim, data=None):
    req = ResponseParameters.model_validate(request.args.to_dict())
    payload = request.json if data is None else data
    scim_resource = scim_type.model_validate(
        payload, scim_ctx=Context.RESOURCE_CREATION_REQUEST
    )
    resource = from_scim(scim_resource, canaille_model())
    Backend.instance.save(resource)
    resource_name = canaille_model.__name__.lower()
    current_app.logger.security(
        f"SCIM created {resource_name} {resource.id} by client {current_token.client.client_id}"
    )
    response_resource = to_scim(resource)
    return (
        response_resource.model_dump(
            scim_ctx=Context.RESOURCE_CREATION_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
        HTTPStatus.CREATED,
    )


def _replace_resource(resource, scim_type, to_scim, from_scim, data=None):
    req = ResponseParameters.model_validate(request.args.to_dict())
    original = to_scim(resource)
    payload = request.json if data is None else data
    scim_resource = scim_type.model_validate(
        payload,
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    scim_resource.replace(original)
    updated = from_scim(scim_resource, resource)
    Backend.instance.save(updated)
    resource_name = type(resource).__name__.lower()
    current_app.logger.security(
        f"SCIM replaced {resource_name} {updated.id} by client {current_token.client.client_id}"
    )
    response = to_scim(updated)
    return response.model_dump(
        scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


def _patch_resource(resource, scim_type, to_scim, from_scim, data=None):
    req = ResponseParameters.model_validate(request.args.to_dict())
    scim_resource = to_scim(resource)
    payload = request.json if data is None else data
    patch_op = PatchOp[scim_type].model_validate(
        payload, scim_ctx=Context.RESOURCE_PATCH_REQUEST
    )
    modified = patch_op.patch(scim_resource)

    if modified:
        updated = from_scim(scim_resource, resource)
        Backend.instance.save(updated)
        resource_name = type(resource).__name__.lower()
        current_app.logger.security(
            f"SCIM patched {resource_name} {updated.id} by client {current_token.client.client_id}"
        )
        scim_resource = to_scim(updated)

    return scim_resource.model_dump(
        scim_ctx=Context.RESOURCE_PATCH_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


def _delete_resource(resource):
    resource_name = type(resource).__name__.lower()
    current_app.logger.security(
        f"SCIM deleted {resource_name} {resource.id} by client {current_token.client.client_id}"
    )
    Backend.instance.delete(resource)
    return "", HTTPStatus.NO_CONTENT


def get_resource_location_from_path(path):
    return f"{request.url_root}scim/v2{path}"


@bp.route("/Users", methods=["GET"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def query_users():
    return _query_resources(
        models.User, User[EnterpriseUser], user_from_canaille_to_scim_server
    )


@bp.route("/Users/<user:user>", methods=["GET"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def query_user(user):
    return _query_resource(user, user_from_canaille_to_scim_server)


@bp.route("/Groups", methods=["GET"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def query_groups():
    return _query_resources(models.Group, Group, group_from_canaille_to_scim_server)


@bp.route("/Groups/<group:group>", methods=["GET"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def query_group(group):
    return _query_resource(group, group_from_canaille_to_scim_server)


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


@bp.route("/.search", methods=["POST"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def search():
    req = SearchRequest.model_validate(request.json)
    total = Backend.instance.count(models.User) + Backend.instance.count(models.Group)
    users = list(
        Backend.instance.query(models.User)[req.start_index_0 : req.stop_index_0]
    )
    groups = list(
        Backend.instance.query(models.Group)[req.start_index_0 : req.stop_index_0]
    )
    scim_users = [user_from_canaille_to_scim_server(user) for user in users]
    scim_groups = [group_from_canaille_to_scim_server(group) for group in groups]
    resources = scim_users + scim_groups
    list_response = ListResponse[User[EnterpriseUser] | Group](
        start_index=req.start_index,
        items_per_page=req.count,
        total_results=total,
        resources=resources,
    )
    payload = list_response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )
    return payload


@bp.route("/Bulk", methods=["POST"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def bulk():
    req = BulkRequest.model_validate(request.json)
    for operation in req.operations:
        try:
            if operation.method == BulkOperation.Method.post:
                if operation.path == "/Users":
                    result = _create_resource(
                        User[EnterpriseUser],
                        models.User,
                        user_from_canaille_to_scim_server,
                        user_from_scim_to_canaille,
                        data=operation.data,
                    )
                elif operation.path == "/Groups":
                    result = _create_resource(
                        Group,
                        models.Group,
                        group_from_canaille_to_scim_server,
                        group_from_scim_to_canaille,
                        data=operation.data,
                    )
                operation.data = result[0]
                operation.status = result[1]
                operation.location = result[0]["meta"]["location"]
            elif operation.method == BulkOperation.Method.put:
                if operation.path.startswith("/Users"):
                    user = Backend.instance.get(
                        models.User, user_name=operation.data["userName"]
                    )
                    if user:
                        result = _replace_resource(
                            user,
                            User[EnterpriseUser],
                            user_from_canaille_to_scim_server,
                            user_from_scim_to_canaille,
                            data=operation.data,
                        )
                        operation.location = result["meta"]["location"]
                        operation.status = HTTPStatus.OK
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="User not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                        operation.location = get_resource_location_from_path(
                            operation.path
                        )
                elif operation.path.startswith("/Groups"):
                    group = Backend.instance.get(
                        models.Group, display_name=operation.data["displayName"]
                    )
                    if group:
                        result = _replace_resource(
                            group,
                            Group,
                            group_from_canaille_to_scim_server,
                            group_from_scim_to_canaille,
                            data=operation.data,
                        )
                        operation.location = result["meta"]["location"]
                        operation.status = HTTPStatus.OK
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="Group not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                        operation.location = get_resource_location_from_path(
                            operation.path
                        )
            elif operation.method == BulkOperation.Method.patch:
                if operation.path.startswith("/Users"):
                    id = operation.path.split("/")[-1]
                    user = Backend.instance.get(models.User, user_name=id)
                    if user:
                        result = _patch_resource(
                            user,
                            User[EnterpriseUser],
                            user_from_canaille_to_scim_server,
                            user_from_scim_to_canaille,
                            data=operation.data,
                        )
                        operation.location = result["meta"]["location"]
                        operation.status = HTTPStatus.OK
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="User not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                        operation.location = get_resource_location_from_path(
                            operation.path
                        )
                elif operation.path.startswith("/Groups"):
                    id = operation.path.split("/")[-1]
                    group = Backend.instance.get(models.Group, display_name=id)
                    if group:
                        result = _patch_resource(
                            group,
                            Group,
                            group_from_canaille_to_scim_server,
                            group_from_scim_to_canaille,
                            data=operation.data,
                        )
                        operation.location = result["meta"]["location"]
                        operation.status = HTTPStatus.OK
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="Group not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                        operation.location = get_resource_location_from_path(
                            operation.path
                        )
            elif operation.method == BulkOperation.Method.delete:
                if operation.path.startswith("/Users"):
                    id = operation.path.split("/")[-1]
                    user = Backend.instance.get(models.User, user_name=id)
                    if user:
                        result = _delete_resource(user)
                        operation.status = result[1]
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="User not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                elif operation.path.startswith("/Groups"):
                    id = operation.path.split("/")[-1]
                    group = Backend.instance.get(models.Group, display_name=id)
                    if group:
                        result = _delete_resource(group)
                        operation.status = result[1]
                    else:
                        operation.status = HTTPStatus.NOT_FOUND
                        operation.response = Error(
                            detail="Group not found", status=HTTPStatus.NOT_FOUND
                        ).model_dump()
                operation.location = get_resource_location_from_path(operation.path)
        except ValidationError as error:
            operation.status = HTTPStatus.BAD_REQUEST
            operation.response = scim_error_handler(error)[0]
            operation.location = (
                get_resource_location_from_path(operation.path)
                if not operation.method == BulkOperation.Method.post
                else None
            )
        except Exception as error:
            operation.status = HTTPStatus.INTERNAL_SERVER_ERROR
            operation.response = Error(
                detail=str(error), status=HTTPStatus.INTERNAL_SERVER_ERROR
            ).model_dump()
            operation.location = (
                get_resource_location_from_path(operation.path)
                if not operation.method == BulkOperation.Method.post
                else None
            )
    rep = BulkResponse(
        operations=req.operations,
    )
    return (rep.model_dump(scim_ctx=Context.RESOURCE_QUERY_RESPONSE), HTTPStatus.OK)


@bp.route("/Users", methods=["POST"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def create_user():
    return _create_resource(
        User[EnterpriseUser],
        models.User,
        user_from_canaille_to_scim_server,
        user_from_scim_to_canaille,
    )


@bp.route("/Groups", methods=["POST"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def create_group():
    return _create_resource(
        Group,
        models.Group,
        group_from_canaille_to_scim_server,
        group_from_scim_to_canaille,
    )


@bp.route("/Users/<user:user>", methods=["PUT"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def replace_user(user):
    return _replace_resource(
        user,
        User[EnterpriseUser],
        user_from_canaille_to_scim_server,
        user_from_scim_to_canaille,
    )


@bp.route("/Groups/<group:group>", methods=["PUT"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def replace_group(group):
    return _replace_resource(
        group,
        Group,
        group_from_canaille_to_scim_server,
        group_from_scim_to_canaille,
    )


@bp.route("/Users/<user:user>", methods=["PATCH"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def patch_user(user):
    return _patch_resource(
        user,
        User[EnterpriseUser],
        user_from_canaille_to_scim_server,
        user_from_scim_to_canaille,
    )


@bp.route("/Groups/<group:group>", methods=["PATCH"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def patch_group(group):
    return _patch_resource(
        group,
        Group,
        group_from_canaille_to_scim_server,
        group_from_scim_to_canaille,
    )


@bp.route("/Users/<user:user>", methods=["DELETE"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_USERS)
def delete_user(user):
    return _delete_resource(user)


@bp.route("/Groups/<group:group>", methods=["DELETE"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.MANAGE_ALL_GROUPS)
def delete_group(group):
    return _delete_resource(group)


def _resolve_me():
    """Resolve the authenticated user from the token subject."""
    user = current_token.subject
    if not user:
        abort(404)
    return user


@bp.route("/Me", methods=["GET"])
@csrf.exempt
@require_oauth()
def query_me():
    return _query_resource(_resolve_me(), user_from_canaille_to_scim_server)


@bp.route("/Me", methods=["PUT"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.EDIT_SELF)
def replace_me():
    return _replace_resource(
        _resolve_me(),
        User[EnterpriseUser],
        user_from_canaille_to_scim_server,
        user_from_scim_to_canaille,
    )


@bp.route("/Me", methods=["PATCH"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.EDIT_SELF)
def patch_me():
    return _patch_resource(
        _resolve_me(),
        User[EnterpriseUser],
        user_from_canaille_to_scim_server,
        user_from_scim_to_canaille,
    )


@bp.route("/Me", methods=["DELETE"])
@csrf.exempt
@require_oauth()
@require_permission(Permission.DELETE_ACCOUNT)
def delete_me():
    return _delete_resource(_resolve_me())
