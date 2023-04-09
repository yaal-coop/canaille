from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from canaille.oidc.models import AuthorizationCode
from flask import abort
from flask import Blueprint
from flask import request
from flask_themer import render_template


bp = Blueprint("authorizations", __name__, url_prefix="/admin/authorization")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def index(user):
    table_form = TableForm(AuthorizationCode, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/admin/authorization_list.html",
        menuitem="admin",
        table_form=table_form,
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
