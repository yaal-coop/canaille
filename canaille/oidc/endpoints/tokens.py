import datetime

from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import url_for

from canaille.app import models
from canaille.app.flask import render_htmx_template
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.oidc.installation import generate_keypair

from .forms import TokenRevokationForm

bp = Blueprint("tokens", __name__, url_prefix="/admin/token")


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_oidc")
def index(user):
    table_form = TableForm(models.Token, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/token_list.html", menuitem="admin", table_form=table_form
    )


@bp.route("/<token:token>", methods=["GET", "POST"])
@user_needed("manage_oidc")
def view(user, token):
    form = TokenRevokationForm(request.form or None)

    if request.form and form.validate():
        if request.form.get("action") == "confirm-revoke":
            return render_template("oidc/modals/revoke-token.html", token=token)

        elif request.form.get("action") == "revoke":
            token.revokation_date = datetime.datetime.now(datetime.timezone.utc)
            Backend.instance.save(token)
            current_app.logger.security(
                f"Revoked token for {token.subject.user_name} in client {token.client.client_name} by {user.user_name}"
            )
            flash(_("The token has successfully been revoked."), "success")

        else:
            abort(400, f"bad form action: {request.form.get('action')}")

    return render_template(
        "oidc/token_view.html",
        token=token,
        menuitem="admin",
        form=form,
    )


@bp.route("/rotate-keys", methods=["GET"])
@user_needed("manage_oidc")
def rotate_keys(user):
    config_keys = current_app.config["CANAILLE_OIDC"]["JWT"]
    
    private_key, public_key = generate_keypair()
    new_private_key = private_key.decode()
    new_public_key = public_key.decode()
    
    config_keys["OLD_PRIVATE_KEY"] = config_keys["PRIVATE_KEY"]
    config_keys["OLD_PUBLIC_KEY"] = config_keys["PUBLIC_KEY"]
    
    config_keys["PRIVATE_KEY"] = new_private_key
    config_keys["PUBLIC_KEY"] = new_public_key
    flash(
        _(
            "The signing keys were changed successfully."
        ),
        "success",
        )
    
    return redirect(url_for("oidc.tokens.index"))
