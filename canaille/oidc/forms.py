import wtforms
from canaille.oidc.models import Client
from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm


class LogoutForm(FlaskForm):
    answer = wtforms.SubmitField()


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
