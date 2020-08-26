from flask import Blueprint, render_template
from web.models import Token


bp = Blueprint(__name__, "tokens")


@bp.route("/")
def tokens():
    tokens = Token.filter()
    return render_template("token_list.html", tokens=tokens)
