import datetime

from canaille.flaskutils import permissions_needed
from canaille.oidc.forms import ClientAdd
from canaille.oidc.models import Client
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


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    clients = Client.all()
    return render_template(
        "oidc/admin/client_list.html", clients=clients, menuitem="admin"
    )


@bp.route("/add", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def add(user):
    form = ClientAdd(request.form or None)

    if not request.form:
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
    client_id_issued_at = datetime.datetime.now()
    client = Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        client_name=form["client_name"].data,
        contacts=[form["contacts"].data],
        client_uri=form["client_uri"].data,
        grant_types=form["grant_types"].data,
        redirect_uris=[form["redirect_uris"].data],
        post_logout_redirect_uris=[form["post_logout_redirect_uris"].data],
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
    client.audience = [client.dn]
    client.save()
    flash(
        _("The client has been created."),
        "success",
    )

    return redirect(url_for("oidc.clients.edit", client_id=client_id))


@bp.route("/edit/<client_id>", methods=["GET", "POST"])
@permissions_needed("manage_oidc")
def edit(user, client_id):
    if request.method == "GET" or request.form.get("action") == "edit":
        return client_edit(client_id)

    if request.form.get("action") == "delete":
        return client_delete(client_id)

    abort(400)


def client_edit(client_id):
    client = Client.get(client_id)

    if not client:
        abort(404)

    data = dict(client)
    data["scope"] = " ".join(data["scope"])
    data["redirect_uris"] = data["redirect_uris"][0] if data["redirect_uris"] else ""
    data["contacts"] = data["contacts"][0] if data["contacts"] else ""
    data["post_logout_redirect_uris"] = (
        data["post_logout_redirect_uris"][0]
        if data["post_logout_redirect_uris"]
        else ""
    )
    data["preconsent"] = client.preconsent
    form = ClientAdd(request.form or None, data=data, client=client)

    if not request.form:
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
        contacts=[form["contacts"].data],
        client_uri=form["client_uri"].data,
        grant_types=form["grant_types"].data,
        redirect_uris=[form["redirect_uris"].data],
        post_logout_redirect_uris=[form["post_logout_redirect_uris"].data],
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
        audience=form["audience"].data,
        preconsent=form["preconsent"].data,
    )
    client.save()
    flash(
        _("The client has been edited."),
        "success",
    )
    return redirect(url_for("oidc.clients.edit", client_id=client_id))


def client_delete(client_id):
    client = Client.get(client_id)

    if not client:
        abort(404)

    flash(
        _("The client has been deleted."),
        "success",
    )
    client.delete()
    return redirect(url_for("oidc.clients.index"))
