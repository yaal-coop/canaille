from canaille.flaskutils import permissions_needed
from canaille.oidc.models import Token
from flask import Blueprint
from flask_themer import render_template


bp = Blueprint("tokens", __name__, url_prefix="/admin/token")


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    tokens = Token.filter()
    return render_template(
        "oidc/admin/token_list.html", tokens=tokens, menuitem="admin"
    )


@bp.route("/<token_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, token_id):
    token = Token.get(token_id)
    return render_template("oidc/admin/token_view.html", token=token, menuitem="admin")
