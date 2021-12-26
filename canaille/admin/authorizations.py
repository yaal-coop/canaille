from canaille.flaskutils import permissions_needed
from canaille.models import AuthorizationCode
from flask import Blueprint
from flask_themer import render_template


bp = Blueprint("authorizations", __name__)


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    authorizations = AuthorizationCode.filter()
    return render_template(
        "admin/authorization_list.html", authorizations=authorizations
    )


@bp.route("/<authorization_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, authorization_id):
    authorization = AuthorizationCode.get(authorization_id)
    return render_template(
        "admin/authorization_view.html", authorization=authorization, menuitem="admin"
    )
