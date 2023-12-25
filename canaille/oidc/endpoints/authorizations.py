from canaille.app import models
from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from canaille.app.themes import render_template
from flask import abort
from flask import Blueprint
from flask import request


bp = Blueprint("authorizations", __name__, url_prefix="/admin/authorization")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def index(user):
    table_form = TableForm(models.AuthorizationCode, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "authorization_list.html",
        menuitem="admin",
        table_form=table_form,
    )


@bp.route("/<authorizationcode:authorization>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, authorization):
    return render_template(
        "authorization_view.html",
        authorization=authorization,
        menuitem="admin",
    )
