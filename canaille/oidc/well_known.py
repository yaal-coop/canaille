import json

from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request


bp = Blueprint("home", __name__, url_prefix="/.well-known")


def cached_oauth_authorization_server():
    if "oauth_authorization_server" not in g:
        with open(current_app.config["OAUTH2_METADATA_FILE"]) as fd:
            g.oauth_authorization_server = json.load(fd)
    return g.oauth_authorization_server


def cached_openid_configuration():
    if "openid_configuration" not in g:
        with open(current_app.config["OIDC_METADATA_FILE"]) as fd:
            g.openid_configuration = json.load(fd)
    return g.openid_configuration


@bp.route("/oauth-authorization-server")
def oauth_authorization_server():
    return jsonify(cached_oauth_authorization_server())


@bp.route("/openid-configuration")
def openid_configuration():
    return jsonify(cached_openid_configuration())


@bp.route("/webfinger")
def webfinger():
    return jsonify(
        {
            "links": [
                {
                    "href": cached_openid_configuration()["issuer"],
                    "rel": "http://openid.net/specs/connect/1.0/issuer",
                }
            ],
            "subject": request.args["resource"],
        }
    )
