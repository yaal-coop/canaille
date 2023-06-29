import datetime

from canaille.app import models
from canaille.app.flask import permissions_needed
from canaille.app.flask import render_htmx_template
from canaille.app.forms import TableForm
from canaille.oidc.forms import ClientAddForm
from flask import abort
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template
from werkzeug.security import gen_salt


bp = Blueprint("clients", __name__, url_prefix="/admin/client")


@bp.route("/", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def index(user):
    table_form = TableForm(models.Client, formdata=request.form)
    if request.form and request.form.get("page") and not table_form.validate():
        abort(404)

    return render_htmx_template(
        "oidc/admin/client_list.html", menuitem="admin", table_form=table_form
    )


@bp.route("/add", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def add(user):
    form = ClientAddForm(request.form or None)

    if not request.form or form.form_control():
        return render_template(
            "oidc/admin/client_add.html", form=form, menuitem="admin"
        )

    if not form.validate():
        flash(
            _("The client has not been added. Please check your information."),
            "error",
        )
        return render_template(
            "oidc/admin/client_add.html", form=form, menuitem="admin"
        )

    client_id = gen_salt(24)
    client_id_issued_at = datetime.datetime.now(datetime.timezone.utc)
    client = models.Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        client_name=form["client_name"].data,
        contacts=form["contacts"].data,
        client_uri=form["client_uri"].data,
        grant_types=form["grant_types"].data,
        redirect_uris=form["redirect_uris"].data,
        post_logout_redirect_uris=form["post_logout_redirect_uris"].data,
        response_types=form["response_types"].data,
        scope=form["scope"].data.split(" "),
        token_endpoint_auth_method=form["token_endpoint_auth_method"].data,
        logo_uri=form["logo_uri"].data,
        tos_uri=form["tos_uri"].data,
        policy_uri=form["policy_uri"].data,
        software_id=form["software_id"].data,
        software_version=form["software_version"].data,
        jwk=form["jwk"].data,
        jwks_uri=form["jwks_uri"].data,
        preconsent=form["preconsent"].data,
        client_secret=""
        if form["token_endpoint_auth_method"].data == "none"
        else gen_salt(48),
    )
    client.audience = [client]
    client.save()
    flash(
        _("The client has been created."),
        "success",
    )

    return redirect(url_for("oidc.clients.edit", client=client))


@bp.route("/edit/<client:client>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def edit(user, client):
    if request.form and request.form.get("action") == "delete":
        return client_delete(client)
    return client_edit(client)


def client_edit(client):
    data = {attribute: getattr(client, attribute) for attribute in client.attributes}
    data["scope"] = " ".join(data["scope"])
    data["preconsent"] = client.preconsent
    form = ClientAddForm(request.form or None, data=data, client=client)

    if not request.form or form.form_control():
        return render_template(
            "oidc/admin/client_edit.html", form=form, client=client, menuitem="admin"
        )

    if not form.validate():
        flash(
            _("The client has not been edited. Please check your information."),
            "error",
        )
        return render_template(
            "oidc/admin/client_edit.html", form=form, client=client, menuitem="admin"
        )

    client.update(
        client_name=form["client_name"].data,
        contacts=form["contacts"].data,
        client_uri=form["client_uri"].data,
        grant_types=form["grant_types"].data,
        redirect_uris=form["redirect_uris"].data,
        post_logout_redirect_uris=form["post_logout_redirect_uris"].data,
        response_types=form["response_types"].data,
        scope=form["scope"].data.split(" "),
        token_endpoint_auth_method=form["token_endpoint_auth_method"].data,
        logo_uri=form["logo_uri"].data,
        tos_uri=form["tos_uri"].data,
        policy_uri=form["policy_uri"].data,
        software_id=form["software_id"].data,
        software_version=form["software_version"].data,
        jwk=form["jwk"].data,
        jwks_uri=form["jwks_uri"].data,
        audience=[models.Client.get(id=id) for id in form["audience"].data],
        preconsent=form["preconsent"].data,
    )
    client.save()
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
    client.delete()
    return redirect(url_for("oidc.clients.index"))
