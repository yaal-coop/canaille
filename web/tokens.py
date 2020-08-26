from flask import Blueprint, render_template
from .models import Token
from .flaskutils import admin_needed


bp = Blueprint(__name__, "tokens")


@bp.route("/")
@admin_needed()
def index():
    tokens = Token.filter()
    return render_template("token_list.html", tokens=tokens)


@bp.route("/<token_id>", methods=["GET", "POST"])
@admin_needed()
def view(token_id):
    token = Token.get(token_id)
    return render_template("token_view.html", token=token)
