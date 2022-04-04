from canaille.flaskutils import permissions_needed
from canaille.models import User
from canaille.oidc.models import Client
from canaille.oidc.models import Token
from flask import abort
from flask import Blueprint
from flask_themer import render_template


bp = Blueprint("tokens", __name__, url_prefix="/admin/token")


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    tokens = Token.all()
    items = (
        (token, Client.get(token.client), User.get(dn=token.subject))
        for token in tokens
    )
    return render_template("oidc/admin/token_list.html", items=items, menuitem="admin")


@bp.route("/<token_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, token_id):
    token = Token.get(token_id=token_id)

    if not token:
        abort(404)

    token_client = Client.get(token.client)
    token_user = User.get(dn=token.subject)
    token_audience = [Client.get(aud) for aud in token.audience]
    return render_template(
        "oidc/admin/token_view.html",
        token=token,
        token_client=token_client,
        token_user=token_user,
        token_audience=token_audience,
        menuitem="admin",
    )
