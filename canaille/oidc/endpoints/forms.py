import wtforms

from canaille.app import models
from canaille.app.forms import Form
from canaille.app.forms import IDToModel
from canaille.app.forms import email_validator
from canaille.app.forms import is_uri
from canaille.app.forms import unique_values
from canaille.app.i18n import lazy_gettext as _
from canaille.backends import Backend


class AuthorizeForm(Form):
    pass


class LogoutForm(Form):
    answer = wtforms.SubmitField()


def _client_audiences():
    return [
        (client, client.client_name) for client in Backend.instance.query(models.Client)
    ]


class ClientAddForm(Form):
    client_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "Client Name"},
    )
    contacts = wtforms.FieldList(
        wtforms.EmailField(
            _("Contacts"),
            validators=[wtforms.validators.Optional(), email_validator],
            render_kw={"placeholder": "admin@mydomain.example"},
        ),
        min_entries=1,
        validators=[unique_values],
    )
    client_uri = wtforms.URLField(
        _("URI"),
        validators=[
            wtforms.validators.DataRequired(),
            is_uri,
        ],
        render_kw={"placeholder": "https://mydomain.example"},
    )
    redirect_uris = wtforms.FieldList(
        wtforms.URLField(
            _("Redirect URIs"),
            validators=[
                wtforms.validators.DataRequired(),
                is_uri,
            ],
            render_kw={"placeholder": "https://mydomain.example/callback"},
        ),
        min_entries=1,
        validators=[unique_values],
    )
    post_logout_redirect_uris = wtforms.FieldList(
        wtforms.URLField(
            _("Post logout redirect URIs"),
            validators=[
                wtforms.validators.Optional(),
                is_uri,
            ],
            render_kw={
                "placeholder": "https://mydomain.example/you-have-been-disconnected"
            },
        ),
        min_entries=1,
        validators=[unique_values],
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
            ("client_credentials", "client_credentials"),
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
        choices=_client_audiences,
        validate_choice=False,
        coerce=IDToModel("Client"),
    )
    logo_uri = wtforms.URLField(
        _("Logo URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://mydomain.example/logo.png"},
    )
    tos_uri = wtforms.URLField(
        _("Terms of service URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://mydomain.example/tos.html"},
    )
    policy_uri = wtforms.URLField(
        _("Policy URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://mydomain.example/policy.html"},
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
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": ""},
    )
    preconsent = wtforms.BooleanField(
        _("Pre-consent"),
        validators=[wtforms.validators.Optional()],
        default=False,
    )


class TokenRevokationForm(Form):
    pass
