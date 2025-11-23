import datetime
from datetime import timedelta

from flask import Blueprint
from flask import abort
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.app.flask import render_htmx_template
from canaille.app.flask import user_needed
from canaille.app.forms import TableForm
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend

from ..jose import build_client_management_token
from .forms import ClientAddForm
from .forms import ClientEditForm

bp = Blueprint("clients", __name__, url_prefix="/admin/client")

TOKEN_LIFETIME = 3600


@bp.route("/", methods=["GET", "POST"])
@user_needed("manage_oidc")
def index(user):
    table_form = TableForm(models.Client, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/client_list.html", menuitem="admin", table_form=table_form
    )


@bp.route("/add", methods=["GET", "POST"])
@user_needed("manage_oidc")
def add(user):
    form = ClientAddForm(request.form or None)

    registration_token = build_client_management_token(
        "client:register", timedelta(seconds=TOKEN_LIFETIME)
    )

    if request.form.get("action") == "new-registration-token":
        flash(_("A new registration token has been generated."), "info")
        return render_template(
            "oidc/client_add.html",
            form=form,
            registration_token=registration_token,
            menuitem="admin",
        )

    if not request.form or form.handle_fieldlist_operation():
        return render_template(
            "oidc/client_add.html",
            form=form,
            registration_token=registration_token,
            menuitem="admin",
        )

    if not form.validate():
        flash(
            _("The client has not been added. Please check your information."),
            "error",
        )
        return render_template(
            "oidc/client_add.html",
            form=form,
            registration_token=registration_token,
            menuitem="admin",
        )

    client_id = gen_salt(24)
    client_id_issued_at = datetime.datetime.now(datetime.timezone.utc)
    client = models.Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        client_name=form["client_name"].data,
        contacts=form["contacts"].data,
        client_uri=form["client_uri"].data,
        redirect_uris=form["redirect_uris"].data,
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=["openid", "profile", "email"],
        token_endpoint_auth_method="client_secret_basic",
        client_secret=gen_salt(48),
        application_type="web",
        id_token_signed_response_alg="RS256",
    )
    Backend.instance.save(client)
    client.audience = [client]
    Backend.instance.save(client)
    flash(
        _("The client has been created."),
        "success",
    )

    return redirect(url_for("oidc.clients.edit", client=client))


@bp.route("/edit/<client:client>", methods=["GET", "POST"])
@user_needed("manage_oidc")
def edit(user, client):
    if request.form.get("action") == "confirm-delete":
        return render_template("oidc/modals/delete-client.html", client=client)

    if request.form and request.form.get("action") == "delete":
        return client_delete(client)

    if request.form and request.form.get("action") == "new-access-token":
        return client_new_token(client)

    return client_edit(client)


def client_edit(client):
    data = {attribute: getattr(client, attribute) for attribute in client.attributes}
    if data["scope"]:
        data["scope"] = " ".join(data["scope"])
    form = ClientEditForm(request.form or None, data=data, client=client)

    management_token = build_client_management_token(
        "client:manage", timedelta(seconds=TOKEN_LIFETIME), client.client_id
    )

    if request.form.get("action") == "new-management-token":
        flash(_("A new management token has been generated."), "info")
        return render_template(
            "oidc/client_edit.html",
            form=form,
            client=client,
            management_token=management_token,
            menuitem="admin",
        )

    if not request.form or form.handle_fieldlist_operation():
        return render_template(
            "oidc/client_edit.html",
            form=form,
            client=client,
            management_token=management_token,
            menuitem="admin",
        )

    if not form.validate():
        flash(
            _("The client has not been edited. Please check your information."),
            "error",
        )
        return render_template(
            "oidc/client_edit.html",
            form=form,
            client=client,
            management_token=management_token,
            menuitem="admin",
        )

    Backend.instance.update(
        client,
        client_name=form["client_name"].data,
        contacts=form["contacts"].data,
        client_uri=form["client_uri"].data,
        redirect_uris=form["redirect_uris"].data,
        post_logout_redirect_uris=form["post_logout_redirect_uris"].data,
        grant_types=form["grant_types"].data,
        scope=form["scope"].data.split(" "),
        response_types=form["response_types"].data,
        token_endpoint_auth_method=form["token_endpoint_auth_method"].data,
        audience=form["audience"].data,
        logo_uri=form["logo_uri"].data,
        tos_uri=form["tos_uri"].data,
        policy_uri=form["policy_uri"].data,
        software_id=form["software_id"].data,
        software_version=form["software_version"].data,
        jwks=form["jwks"].data,
        jwks_uri=form["jwks_uri"].data,
        token_endpoint_auth_signing_alg=form["token_endpoint_auth_signing_alg"].data
        or None,
        sector_identifier_uri=form["sector_identifier_uri"].data or None,
        subject_type=form["subject_type"].data or None,
        application_type=form["application_type"].data or None,
        id_token_signed_response_alg=form["id_token_signed_response_alg"].data,
        userinfo_signed_response_alg=form["userinfo_signed_response_alg"].data or None,
        default_max_age=form["default_max_age"].data,
        require_auth_time=form["require_auth_time"].data,
        default_acr_values=[v for v in form["default_acr_values"].data if v] or None,
        initiate_login_uri=form["initiate_login_uri"].data or None,
        request_object_signing_alg=form["request_object_signing_alg"].data or None,
        request_uris=[v for v in form["request_uris"].data if v] or None,
        require_signed_request_object=form["require_signed_request_object"].data,
    )
    Backend.instance.save(client)
    flash(
        _("The client has been edited."),
        "success",
    )
    return redirect(url_for("oidc.clients.edit", client=client))


def client_delete(client):
    flash(
        _("The client has been deleted."),
        "success",
    )
    Backend.instance.delete(client)
    return redirect(url_for("oidc.clients.index"))


def client_new_token(client):
    flash(
        _(f"A token have been created for the client {client.client_name}"),
        "success",
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    token = models.Token(
        token_id=gen_salt(48),
        type="access_token",
        access_token=gen_salt(48),
        issue_date=now,
        lifetime=TOKEN_LIFETIME,
        scope=client.scope,
        client=client,
        audience=client.audience,
    )
    Backend.instance.save(token)
    return redirect(url_for("oidc.tokens.view", token=token))
