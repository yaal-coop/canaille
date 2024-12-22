from flask import Blueprint
from flask import abort
from flask import request

from canaille.app import models
from canaille.app.flask import render_htmx_template
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.app.templating import render_template

bp = Blueprint("authorizations", __name__, url_prefix="/admin/authorization")


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_oidc")
def index(user):
    table_form = TableForm(models.AuthorizationCode, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/authorization_list.html",
        menuitem="admin",
        table_form=table_form,
    )


@bp.route("/<authorizationcode:authorization>", methods=["GET", "POST"])
@user_needed("manage_oidc")
def view(user, authorization):
    return render_template(
        "oidc/authorization_view.html",
        authorization=authorization,
        menuitem="admin",
    )
