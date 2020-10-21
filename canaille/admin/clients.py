import datetime
import wtforms
import wtforms.fields.html5
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm
from flask_babel import gettext
from werkzeug.security import gen_salt
from canaille.models import Client
from canaille.flaskutils import admin_needed


bp = Blueprint(__name__, "clients")


@bp.route("/")
@admin_needed()
def index():
    clients = Client.filter()
    return render_template("admin/client_list.html", clients=clients, menuitem="admin")


class ClientAdd(FlaskForm):
    oauthClientName = wtforms.StringField(
        gettext("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "Client Name"},
    )
    oauthClientContact = wtforms.fields.html5.EmailField(
        gettext("Contact"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "admin@mydomain.tld"},
    )
    oauthClientURI = wtforms.fields.html5.URLField(
        gettext("URI"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld"},
    )
    oauthRedirectURIs = wtforms.fields.html5.URLField(
        gettext("Redirect URIs"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "https://mydomain.tld/callback"},
    )
    oauthGrantType = wtforms.SelectMultipleField(
        gettext("Grant types"),
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
    oauthScope = wtforms.StringField(
        gettext("Scope"),
        validators=[wtforms.validators.Optional()],
        default="openid profile email",
        render_kw={"placeholder": "openid profile"},
    )
    oauthResponseType = wtforms.SelectMultipleField(
        gettext("Response types"),
        validators=[wtforms.validators.DataRequired()],
        choices=[("code", "code"), ("token", "token"), ("id_token", "id_token")],
        default=["code"],
    )
    oauthTokenEndpointAuthMethod = wtforms.SelectField(
        gettext("Token Endpoint Auth Method"),
        validators=[wtforms.validators.DataRequired()],
        choices=[
            ("client_secret_basic", "client_secret_basic"),
            ("client_secret_post", "client_secret_post"),
            ("none", "none"),
        ],
        default="client_secret_basic",
    )
    oauthLogoURI = wtforms.fields.html5.URLField(
        gettext("Logo URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/logo.png"},
    )
    oauthTermsOfServiceURI = wtforms.fields.html5.URLField(
        gettext("Terms of service URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/tos.html"},
    )
    oauthPolicyURI = wtforms.fields.html5.URLField(
        gettext("Policy URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "https://mydomain.tld/policy.html"},
    )
    oauthSoftwareID = wtforms.StringField(
        gettext("Software ID"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "xyz"},
    )
    oauthSoftwareVersion = wtforms.StringField(
        gettext("Software Version"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "1.0"},
    )
    oauthJWK = wtforms.StringField(
        gettext("JWK"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": ""},
    )
    oauthJWKURI = wtforms.fields.html5.URLField(
        gettext("JKW URI"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": ""},
    )


@bp.route("/add", methods=["GET", "POST"])
@admin_needed()
def add():
    form = ClientAdd(request.form or None)

    if not request.form:
        return render_template("admin/client_add.html", form=form, menuitem="admin")

    if not form.validate():
        flash(
            gettext("The client has not been added. Please check your information."),
            "error",
        )
        return render_template("admin/client_add.html", form=form, menuitem="admin")

    client_id = gen_salt(24)
    client_id_issued_at = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
    client = Client(
        oauthClientID=client_id,
        oauthIssueDate=client_id_issued_at,
        oauthClientName=form["oauthClientName"].data,
        oauthClientContact=form["oauthClientContact"].data,
        oauthClientURI=form["oauthClientURI"].data,
        oauthGrantType=form["oauthGrantType"].data,
        oauthRedirectURIs=[form["oauthRedirectURIs"].data],
        oauthResponseType=form["oauthResponseType"].data,
        oauthScope=form["oauthScope"].data.split(" "),
        oauthTokenEndpointAuthMethod=form["oauthTokenEndpointAuthMethod"].data,
        oauthLogoURI=form["oauthLogoURI"].data,
        oauthTermsOfServiceURI=form["oauthTermsOfServiceURI"].data,
        oauthPolicyURI=form["oauthPolicyURI"].data,
        oauthSoftwareID=form["oauthSoftwareID"].data,
        oauthSoftwareVersion=form["oauthSoftwareVersion"].data,
        oauthJWK=form["oauthJWK"].data,
        oauthJWKURI=form["oauthJWKURI"].data,
        oauthClientSecret=""
        if form["oauthTokenEndpointAuthMethod"].data == "none"
        else gen_salt(48),
    )
    client.save()
    flash(
        gettext("The client has been created."),
        "success",
    )

    return redirect(url_for("canaille.admin.clients.edit", client_id=client_id))


@bp.route("/edit/<client_id>", methods=["GET", "POST"])
@admin_needed()
def edit(client_id):
    client = Client.get(client_id)
    data = dict(client)
    data["oauthScope"] = " ".join(data["oauthScope"])
    data["oauthRedirectURIs"] = data["oauthRedirectURIs"][0]
    form = ClientAdd(request.form or None, data=data, client=client)

    if not request.form:
        return render_template(
            "admin/client_edit.html", form=form, client=client, menuitem="admin"
        )

    if not form.validate():
        flash(
            gettext("The client has not been edited. Please check your information."),
            "error",
        )

    else:
        client.update(
            oauthClientName=form["oauthClientName"].data,
            oauthClientContact=form["oauthClientContact"].data,
            oauthClientURI=form["oauthClientURI"].data,
            oauthGrantType=form["oauthGrantType"].data,
            oauthRedirectURIs=[form["oauthRedirectURIs"].data],
            oauthResponseType=form["oauthResponseType"].data,
            oauthScope=form["oauthScope"].data.split(" "),
            oauthTokenEndpointAuthMethod=form["oauthTokenEndpointAuthMethod"].data,
            oauthLogoURI=form["oauthLogoURI"].data,
            oauthTermsOfServiceURI=form["oauthTermsOfServiceURI"].data,
            oauthPolicyURI=form["oauthPolicyURI"].data,
            oauthSoftwareID=form["oauthSoftwareID"].data,
            oauthSoftwareVersion=form["oauthSoftwareVersion"].data,
            oauthJWK=form["oauthJWK"].data,
            oauthJWKURI=form["oauthJWKURI"].data,
        )
        client.save()
        flash(
            gettext("The client has been edited."),
            "success",
        )

    return render_template(
        "admin/client_edit.html", form=form, client=client, menuitem="admin"
    )
