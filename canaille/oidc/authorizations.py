from canaille.flaskutils import permissions_needed
from canaille.oidc.models import AuthorizationCode
from flask import Blueprint
from flask_themer import render_template


bp = Blueprint("authorizations", __name__, url_prefix="/admin/authorization")


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    authorizations = AuthorizationCode.all()
    return render_template(
        "oidc/admin/authorization_list.html",
        authorizations=authorizations,
        menuitem="admin",
    )


@bp.route("/<authorization_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, authorization_id):
    authorization = AuthorizationCode.get(authorization_id)
    return render_template(
        "oidc/admin/authorization_view.html",
        authorization=authorization,
        menuitem="admin",
    )
