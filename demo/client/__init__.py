import json
import uuid
from http import HTTPStatus
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import requests
from authlib.common.errors import AuthlibBaseError
from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.integrations.flask_oauth2.errors import (
    _HTTPException as AuthlibHTTPException,
)
from authlib.oauth2.rfc7662 import IntrospectTokenValidator
from authlib.oidc.discovery import get_well_known_url
from flask import Blueprint
from flask import Flask
from flask import Response
from flask import abort
from flask import current_app
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from pydantic import ValidationError
from scim2_models import Context
from scim2_models import EnterpriseUser
from scim2_models import Error
from scim2_models import Group
from scim2_models import ListResponse
from scim2_models import ResourceType
from scim2_models import Schema
from scim2_models import SearchRequest
from scim2_models import User
from werkzeug.exceptions import HTTPException

from canaille import csrf
from canaille.scim.models import get_resource_types
from canaille.scim.models import get_schemas
from canaille.scim.models import get_service_provider_config

bp = Blueprint("scim", __name__)
oauth = OAuth()


class SCIMBearerTokenValidator(IntrospectTokenValidator):
    def introspect_token(self, token_string: str):
        url = current_app.config["OAUTH_AUTH_SERVER"] + "/oauth/introspect"
        data = {"token": token_string, "token_type_hint": "access_token"}
        auth = (
            current_app.config["OAUTH_CLIENT_ID"],
            current_app.config["OAUTH_CLIENT_SECRET"],
        )
        resp = requests.post(url, data=data, auth=auth)
        resp.raise_for_status()
        return resp.json()


require_oauth = ResourceProtector()
require_oauth.register_token_validator(SCIMBearerTokenValidator())


class ClientBackend:
    """Simple backend used to test SCIM features."""

    users: list[User[EnterpriseUser]] = []
    groups: list[Group] = []

    def get(self, instance_type, id=None):
        instance_list = self.groups if instance_type == Group else self.users
        if id:
            return next(
                (instance for instance in instance_list if instance.id == id), None
            )
        else:
            return instance_list

    def save(self, instance):
        instance_list = self.groups if isinstance(instance, Group) else self.users
        saved_instance = None
        for i, sinstance in enumerate(instance_list):
            if sinstance.id == instance.id:
                instance_list[i] = instance
                saved_instance = sinstance
                break
        if not saved_instance:
            instance.id = str(uuid.uuid4())
            instance_list.append(instance)

    def delete(self, instance_type, id):
        instance_list = self.groups if instance_type == Group else self.users
        for sinstance in instance_list:
            if sinstance.id == id:
                instance_list.remove(sinstance)
                break


backend = ClientBackend()


def setup_routes(app):
    @app.route("/")
    @app.route("/tos")
    @app.route("/policy")
    def index():
        return render_template(
            "index.html", user=session.get("user"), name=app.config["NAME"]
        )

    @app.route("/register")
    def register():
        return oauth.canaille.authorize_redirect(
            url_for("register_callback", _external=True), prompt="create"
        )

    @app.route("/register_callback")
    def register_callback():
        try:
            token = oauth.canaille.authorize_access_token()
            session["user"] = token.get("userinfo")
            session["id_token"] = token["id_token"]
            flash("You account has been successfully created.", "success")
        except AuthlibBaseError as exc:
            flash(f"An error happened during registration: {exc.description}", "error")

        return redirect(url_for("index"))

    @app.route("/login")
    def login():
        return oauth.canaille.authorize_redirect(
            url_for("login_callback", _external=True)
        )

    @app.route("/login_callback")
    def login_callback():
        try:
            token = oauth.canaille.authorize_access_token()
            session["user"] = token.get("userinfo")
            session["id_token"] = token["id_token"]
            flash("You have been successfully logged in.", "success")
        except AuthlibBaseError as exc:
            flash(f"An error happened during login: {exc.description}", "error")

        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        oauth.canaille.load_server_metadata()
        end_session_endpoint = oauth.canaille.server_metadata.get(
            "end_session_endpoint"
        )
        end_session_url = set_parameter_in_url_query(
            end_session_endpoint,
            client_id=current_app.config["OAUTH_CLIENT_ID"],
            id_token_hint=session["id_token"],
            post_logout_redirect_uri=url_for("logout_callback", _external=True),
        )
        return redirect(end_session_url)

    @app.route("/logout_callback")
    def logout_callback():
        try:
            del session["user"]
        except KeyError:
            pass

        flash("You have been successfully logged out", "success")
        return redirect(url_for("index"))

    @bp.route("/Users")
    @csrf.exempt
    @require_oauth()
    def query_users():
        req = parse_search_request(request)
        users = backend.get(User[EnterpriseUser])[req.start_index_0 : req.stop_index_0]
        total = len(users)
        list_response = ListResponse[User[EnterpriseUser]](
            start_index=req.start_index,
            items_per_page=req.count,
            total_results=total,
            resources=users,
        )
        payload = list_response.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        )
        return payload

    @bp.route("/Users/<string:id>", methods=["GET"])
    @csrf.exempt
    @require_oauth()
    def query_user(id):
        user = backend.get(User[EnterpriseUser], id)
        if user:
            return user.model_dump(
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
        user = User[EnterpriseUser].model_validate(
            request.json, scim_ctx=Context.RESOURCE_CREATION_REQUEST
        )
        backend.save(user)
        payload = user.model_dump_json(scim_ctx=Context.RESOURCE_CREATION_RESPONSE)
        return Response(payload, status=HTTPStatus.CREATED)

    @bp.route("/Users/<string:id>", methods=["PUT"])
    @csrf.exempt
    @require_oauth()
    def replace_user(id):
        original_scim_user = backend.get(User[EnterpriseUser], id)
        request_scim_user = User[EnterpriseUser].model_validate(
            request.json,
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=original_scim_user,
        )
        request_scim_user.id = original_scim_user.id
        backend.save(request_scim_user)
        payload = request_scim_user.model_dump(
            scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
        )
        return payload

    @bp.route("/Users/<string:id>", methods=["DELETE"])
    @csrf.exempt
    @require_oauth()
    def delete_user(id):
        backend.delete(User[EnterpriseUser], id)
        return "", HTTPStatus.NO_CONTENT

    @bp.route("/Groups", methods=["POST"])
    @csrf.exempt
    @require_oauth()
    def create_group():
        request_group = Group.model_validate(
            request.json, scim_ctx=Context.RESOURCE_CREATION_REQUEST
        )
        backend.save(request_group)
        payload = request_group.model_dump_json(
            scim_ctx=Context.RESOURCE_CREATION_RESPONSE
        )
        return Response(payload, status=HTTPStatus.CREATED)

    @bp.route("/Groups", methods=["GET"])
    @csrf.exempt
    @require_oauth()
    def query_groups():
        req = parse_search_request(request)
        groups = backend.get(Group)[req.start_index_0 : req.stop_index_0]
        total = len(groups)
        list_response = ListResponse[Group](
            start_index=req.start_index,
            items_per_page=req.count,
            total_results=total,
            resources=groups,
        )
        payload = list_response.model_dump(
            scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        )
        return payload

    @bp.route("/Groups/<string:id>", methods=["GET"])
    @csrf.exempt
    @require_oauth()
    def query_group(id):
        group = backend.get(Group, id)
        if group:
            return group.model_dump(
                scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
            )

    @bp.route("/Groups/<string:id>", methods=["PUT"])
    @csrf.exempt
    @require_oauth()
    def replace_group(id):
        group = backend.get(Group, id)
        request_group = Group.model_validate(
            request.json,
            scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
            original=group,
        )
        request_group.id = group.id
        backend.save(request_group)
        payload = request_group.model_dump(
            scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE
        )
        return payload

    @bp.route("/Groups/<string:id>", methods=["DELETE"])
    @csrf.exempt
    @require_oauth()
    def delete_group(id):
        backend.delete(Group, id)
        return "", HTTPStatus.NO_CONTENT

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

    app.register_blueprint(bp)


def setup_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="canaille",
        client_id=app.config["OAUTH_CLIENT_ID"],
        client_secret=app.config["OAUTH_CLIENT_SECRET"],
        server_metadata_url=get_well_known_url(
            app.config["OAUTH_AUTH_SERVER"], external=True
        ),
        client_kwargs={"scope": "openid profile email phone address groups"},
    )


def create_app():
    app = Flask(__name__)
    app.config.from_envvar("CONFIG")
    app.static_folder = "../../canaille/static"

    setup_routes(app)
    setup_oauth(app)
    return app


def set_parameter_in_url_query(url, **kwargs):
    split = list(urlsplit(url))

    parameters = "&".join(f"{key}={value}" for key, value in kwargs.items())

    if split[3]:
        split[3] = f"{split[3]}&{parameters}"
    else:
        split[3] = parameters

    return urlunsplit(split)


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
