from flask import Blueprint, render_template
from .models import AuthorizationCode
from .flaskutils import admin_needed


bp = Blueprint(__name__, "authorizations")


@bp.route("/")
@admin_needed()
def index():
    authorizations = AuthorizationCode.filter()
    return render_template("authorization_list.html", authorizations=authorizations)


@bp.route("/<authorization_id>", methods=["GET", "POST"])
@admin_needed()
def view(authorization_id):
    authorization = AuthorizationCode.get(authorization_id)
    return render_template("authorization_view.html", authorization=authorization)
