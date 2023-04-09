import datetime

from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from canaille.oidc.models import Token
from flask import abort
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template

bp = Blueprint("tokens", __name__, url_prefix="/admin/token")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def index(user):
    table_form = TableForm(Token, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/admin/token_list.html", menuitem="admin", table_form=table_form
    )


@bp.route("/<token_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def view(user, token_id):
    token = Token.get(token_id=token_id)

    if not token:
        abort(404)

    return render_template(
        "oidc/admin/token_view.html",
        token=token,
        menuitem="admin",
    )


@bp.route("/<token_id>/revoke", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def revoke(user, token_id):
    token = Token.get(token_id=token_id)

    if not token:
        abort(404)

    token.revokation_date = datetime.datetime.now(datetime.timezone.utc)
    token.save()
    flash(_("The token has successfully been revoked."), "success")

    return redirect(url_for("oidc.tokens.view", token_id=token_id))
