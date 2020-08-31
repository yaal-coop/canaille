from flask import Blueprint, render_template
from oidc_ldap_bridge.models import Token
from oidc_ldap_bridge.flaskutils import admin_needed


bp = Blueprint(__name__, "tokens")


@bp.route("/")
@admin_needed()
def index():
    tokens = Token.filter()
    return render_template("admin/token_list.html", tokens=tokens)


@bp.route("/<token_id>", methods=["GET", "POST"])
@admin_needed()
def view(token_id):
    token = Token.get(token_id)
    return render_template("admin/token_view.html", token=token)
