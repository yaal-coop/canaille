import json
from flask import Blueprint, jsonify, current_app


bp = Blueprint(__name__, "home")


@bp.route("/oauth-authorization-server")
def oauth_authorization_server():
    with open(current_app.config["OAUTH2_METADATA_FILE"]) as fd:
        return jsonify(json.load(fd))


@bp.route("/openid-configuration")
def openid_configuration():
    with open(current_app.config["OIDC_METADATA_FILE"]) as fd:
        return jsonify(json.load(fd))
