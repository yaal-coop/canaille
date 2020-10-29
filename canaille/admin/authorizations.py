from flask import Blueprint, render_template
from canaille.models import AuthorizationCode
from canaille.flaskutils import admin_needed


bp = Blueprint(__name__, "authorizations")


@bp.route("/")
@admin_needed()
def index(user):
    authorizations = AuthorizationCode.filter()
    return render_template(
        "admin/authorization_list.html", authorizations=authorizations
    )


@bp.route("/<authorization_id>", methods=["GET", "POST"])
@admin_needed()
def view(user, authorization_id):
    authorization = AuthorizationCode.get(authorization_id)
    return render_template(
        "admin/authorization_view.html", authorization=authorization, menuitem="admin"
    )
