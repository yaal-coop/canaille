from flask import Blueprint
from flask import jsonify
from flask import request

from ..oauth import oauth_authorization_server
from ..oauth import openid_configuration

bp = Blueprint("home", __name__, url_prefix="/.well-known")


@bp.route("/oauth-authorization-server")
def oauth_authorization_server_endpoint():
    return jsonify(
        {
            key: val
            for key, val in oauth_authorization_server().items()
            if val is not None
        }
    )


@bp.route("/openid-configuration")
def openid_configuration_endpoint():
    return jsonify(
        {key: val for key, val in openid_configuration().items() if val is not None}
    )


@bp.route("/webfinger")
def webfinger():
    return jsonify(
        {
            "links": [
                {
                    "href": openid_configuration()["issuer"],
                    "rel": "http://openid.net/specs/connect/1.0/issuer",
                }
            ],
            "subject": request.args["resource"],
        }
    )
