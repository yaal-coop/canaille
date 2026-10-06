import json
from dataclasses import dataclass
from dataclasses import field

from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import Blueprint
from flask import Response
from flask import current_app
from flask import request
from flask import url_for
from scim2_models import ForbiddenException
from scim2_models import NotFoundException
from scim2_models import SCIMException
from scim2_models import UnauthorizedException
from scim2_server.handler import ScimHandler
from scim2_server.requests import ScimRequest
from scim2_server.routing import Operation
from scim2_server.service import ScimService

from canaille.app import models
from canaille.app.flask import csrf
from canaille.backends import Backend
from canaille.core.configuration import Permission

from .models import get_provider
from .storage import CanailleStorage

bp = Blueprint("scim", __name__, url_prefix="/scim/v2")


READ_SCOPES = {
    "User": {"scim:users:read", "scim:users:write", "scim:read", "scim:write"},
    "Group": {"scim:groups:read", "scim:groups:write", "scim:read", "scim:write"},
}
WRITE_SCOPES = {
    "User": {"scim:users:write", "scim:write"},
    "Group": {"scim:groups:write", "scim:write"},
}
ME_SCOPE = "scim:me"

READ_OPERATIONS = {Operation.query, Operation.search, Operation.search_with_body}
DISCOVERY_OPERATIONS = {
    Operation.service_provider_config,
    Operation.resource_types,
    Operation.resource_type,
    Operation.schemas,
    Operation.schema,
}


class SCIMBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string: str):
        token = Backend.instance.get(models.Token, access_token=token_string)
        if token and token.subject and token.subject.locked:
            return None
        return token


require_oauth = ResourceProtector()
require_oauth.register_token_validator(SCIMBearerTokenValidator())


@dataclass
class Subject:
    """The token of a request, with the permissions of its user loaded in advance."""

    token: "models.Token | None" = None
    permissions: set[Permission] = field(default_factory=set)

    @classmethod
    def of(cls, token):
        user = token.subject if token else None
        permissions = {p for p in Permission if user.can(p)} if user else set()
        return cls(token, permissions)

    @property
    def user(self):
        return self.token.subject if self.token else None

    @property
    def scopes(self):
        return set(self.token.scope or []) if self.token else set()


class CanailleService(ScimService):
    """Check the rights of the tokens, and serve /Me with the user of the token."""

    def me_target(self, request):
        if ME_SCOPE not in request.subject.scopes:
            raise ForbiddenException(detail=f"The {ME_SCOPE} scope is required")
        if not request.subject.user:
            raise NotFoundException(detail="The token has no user")
        return self.get_resource_type("User"), request.subject.user.id

    def authorize(self, request, target, resource_type):
        if request.subject.user:
            self._authorize_user(request.subject, target, resource_type)
            return

        scopes = (READ_SCOPES if target.operation in READ_OPERATIONS else WRITE_SCOPES)[
            resource_type.id
        ]
        if not scopes & request.subject.scopes:
            raise ForbiddenException(
                detail="The token is not allowed to access this resource type"
            )

    @staticmethod
    def _authorize_user(subject, target, resource_type):
        """Let a user token act on its own user only."""
        if ME_SCOPE not in subject.scopes:
            raise ForbiddenException(detail=f"The {ME_SCOPE} scope is required")

        if resource_type.id != "User" or target.resource_id != subject.user.id:
            raise ForbiddenException(detail="User tokens can only access their user")

        if target.operation in (Operation.replace, Operation.patch):
            needed = {Permission.EDIT_SELF}
        elif target.operation is Operation.delete:
            needed = {Permission.DELETE_ACCOUNT, Permission.MANAGE_USERS}
        else:
            return

        if not needed & subject.permissions:
            raise ForbiddenException(detail="Insufficient permissions")


def _authenticate(scim_request, service):
    """Return the token of a request, or None for the discovery endpoints."""
    if service.match(scim_request).operation in DISCOVERY_OPERATIONS:
        return None
    try:
        return require_oauth.acquire_token()
    except OAuth2Error as error:
        raise UnauthorizedException(detail=error.description or error.error) from error


@bp.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@csrf.exempt
def scim(path):
    service = CanailleService(get_provider())
    scim_request = ScimRequest(
        method=request.method,
        base_url=url_for("scim.scim", path="", _external=True).rstrip("/"),
        path=f"/{path}",
        query=request.args.to_dict(),
        headers=list(request.headers.items()),
        body=request.get_data(),
    )
    try:
        token = _authenticate(scim_request, service)
        scim_request.subject = Subject.of(token)
        handler = ScimHandler(service, CanailleStorage(token))
        response = handler.handle(scim_request)
    except Exception as exception:
        if not isinstance(exception, SCIMException):
            current_app.logger.exception(exception)
        response = service.error_response(exception)

    body = "" if response.body is None else json.dumps(response.body)
    return Response(body, status=response.status, headers=response.headers)
