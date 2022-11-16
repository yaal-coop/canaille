import datetime

import wtforms
from canaille.flaskutils import permissions_needed
from canaille.oidc.models import Client
from flask import abort
from flask import Blueprint
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from flask_babel import lazy_gettext as _
from flask_themer import render_template
from flask_wtf import FlaskForm
from werkzeug.security import gen_salt


bp = Blueprint("clients", __name__, url_prefix="/admin/client")


@bp.route("/")
@permissions_needed("manage_oidc")
def index(user):
    clients = Client.all()
    return render_template(
        "oidc/admin/client_list.html", clients=clients, menuitem="admin"
    )


def client_audiences():
    return [(client.dn, client.client_name) for client in Client.all()]


class ClientAdd(FlaskForm):
    client_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "Client Name"},
    )
    contacts = wtforms.EmailField(
        _("Contact"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "admin@mydomain.tld"},
    )
    client_uri = wtforms.URLField(
        _("URI"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld"},
    )
    redirect_uris = wtforms.URLField(
        _("Redirect URIs"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld/callback"},
    )
    post_logout_redirect_uris = wtforms.URLField(
        _("Post logout redirect URIs"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/you-have-been-disconnected"},
    )
    grant_types = wtforms.SelectMultipleField(
        _("Grant types"),
        validators=[wtforms.validators.DataRequired()],
        choices=[
            ("password", "password"),
            ("authorization_code", "authorization_code"),
            ("implicit", "implicit"),
            ("hybrid", "hybrid"),
            ("refresh_token", "refresh_token"),
        ],
        default=["authorization_code", "refresh_token"],
    )
    scope = wtforms.StringField(
        _("Scope"),
        validators=[wtforms.validators.Optional()],
        default="openid profile email",
        render_kw={"placeholder": "openid profile"},
    )
    response_types = wtforms.SelectMultipleField(
        _("Response types"),
        validators=[wtforms.validators.DataRequired()],
        choices=[("code", "code"), ("token", "token"), ("id_token", "id_token")],
        default=["code"],
    )
    token_endpoint_auth_method = wtforms.SelectField(
        _("Token Endpoint Auth Method"),
        validators=[wtforms.validators.DataRequired()],
        choices=[
            ("client_secret_basic", "client_secret_basic"),
            ("client_secret_post", "client_secret_post"),
            ("none", "none"),
        ],
        default="client_secret_basic",
    )
    audience = wtforms.SelectMultipleField(
        _("Token audiences"),
        validators=[wtforms.validators.Optional()],
        choices=client_audiences,
        validate_choice=False,
    )
    logo_uri = wtforms.URLField(
        _("Logo URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/logo.png"},
    )
    tos_uri = wtforms.URLField(
        _("Terms of service URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/tos.html"},
    )
    policy_uri = wtforms.URLField(
        _("Policy URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/policy.html"},
    )
    software_id = wtforms.StringField(
        _("Software ID"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "xyz"},
    )
    software_version = wtforms.StringField(
        _("Software Version"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "1.0"},
    )
    jwk = wtforms.StringField(
        _("JWK"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": ""},
    )
    jwks_uri = wtforms.URLField(
        _("JKW URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": ""},
    )
    preconsent = wtforms.BooleanField(
        _("Pre-consent"),
        validators=[wtforms.validators.Optional()],
        default=False,
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
    data["redirect_uris"] = data["redirect_uris"][0]
    data["contacts"] = data["contacts"][0]
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
