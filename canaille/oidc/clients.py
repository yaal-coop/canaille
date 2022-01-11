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
    clients = Client.filter()
    return render_template(
        "oidc/admin/client_list.html", clients=clients, menuitem="admin"
    )


def client_audiences():
    return [(client.dn, client.name) for client in Client.filter()]


class ClientAdd(FlaskForm):
    name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "Client Name"},
    )
    contact = wtforms.EmailField(
        _("Contact"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "admin@mydomain.tld"},
    )
    uri = wtforms.URLField(
        _("URI"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld"},
    )
    redirect_uris = wtforms.URLField(
        _("Redirect URIs"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld/callback"},
    )
    grant_type = wtforms.SelectMultipleField(
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
    response_type = wtforms.SelectMultipleField(
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
    jwk_uri = wtforms.URLField(
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
        issue_date=client_id_issued_at,
        name=form["name"].data,
        contact=form["contact"].data,
        uri=form["uri"].data,
        grant_type=form["grant_type"].data,
        redirect_uris=[form["redirect_uris"].data],
        response_type=form["response_type"].data,
        scope=form["scope"].data.split(" "),
        token_endpoint_auth_method=form["token_endpoint_auth_method"].data,
        logo_uri=form["logo_uri"].data,
        tos_uri=form["tos_uri"].data,
        policy_uri=form["policy_uri"].data,
        software_id=form["software_id"].data,
        software_version=form["software_version"].data,
        jwk=form["jwk"].data,
        jwk_uri=form["jwk_uri"].data,
        preconsent=form["preconsent"].data,
        secret=""
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
    client = Client.get(client_id) or abort(404)
    data = dict(client)
    data["scope"] = " ".join(data["scope"])
    data["redirect_uris"] = data["redirect_uris"][0]
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

    else:
        client.update(
            name=form["name"].data,
            contact=form["contact"].data,
            uri=form["uri"].data,
            grant_type=form["grant_type"].data,
            redirect_uris=[form["redirect_uris"].data],
            response_type=form["response_type"].data,
            scope=form["scope"].data.split(" "),
            token_endpoint_auth_method=form["token_endpoint_auth_method"].data,
            logo_uri=form["logo_uri"].data,
            tos_uri=form["tos_uri"].data,
            policy_uri=form["policy_uri"].data,
            software_id=form["software_id"].data,
            software_version=form["software_version"].data,
            jwk=form["jwk"].data,
            jwk_uri=form["jwk_uri"].data,
            audience=form["audience"].data,
            preconsent=form["preconsent"].data,
        )
        client.save()
        flash(
            _("The client has been edited."),
            "success",
        )

    return render_template(
        "oidc/admin/client_edit.html", form=form, client=client, menuitem="admin"
    )


def client_delete(client_id):
    client = Client.get(client_id) or abort(404)
    flash(
        _("The client has been deleted."),
        "success",
    )
    client.delete()
    return redirect(url_for("oidc.clients.index"))
