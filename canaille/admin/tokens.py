from flask import Blueprint, render_template
from canaille.models import Token
from canaille.flaskutils import admin_needed


bp = Blueprint(__name__, "tokens")


@bp.route("/")
@admin_needed()
def index(user):
    tokens = Token.filter()
    return render_template("admin/token_list.html", tokens=tokens, menuitem="admin")


@bp.route("/<token_id>", methods=["GET", "POST"])
@admin_needed()
def view(user, token_id):
    token = Token.get(token_id)
    return render_template("admin/token_view.html", token=token, menuitem="admin")
