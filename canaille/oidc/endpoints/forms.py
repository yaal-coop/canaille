import json

import wtforms
from joserfc.jwk import KeySet

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


def is_jwks(form, field):
    try:
        payload = json.loads(field.data)
    except json.decoder.JSONDecodeError as exc:
        raise wtforms.ValidationError(
            _("This value is not a valid JSON string.")
        ) from exc

    try:
        KeySet.import_key_set(payload)
    except (KeyError, ValueError) as exc:
        raise wtforms.ValidationError(_("This value is not a valid JWK.")) from exc


def _client_audiences():
    return [
        (client, client.client_name) for client in Backend.instance.query(models.Client)
    ]


class ClientAddForm(Form):
    client_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "Client Name"},
        description=_(
            "This is the name that will be displayed on the web interface, and notably on the consent page."
        ),
    )

    contacts = wtforms.FieldList(
        wtforms.EmailField(
            _("Contacts"),
            validators=[wtforms.validators.Optional(), email_validator],
            render_kw={"placeholder": "admin@client.example"},
        ),
        min_entries=1,
        validators=[unique_values],
        description=_(
            "Those are the email addresses of people responsible for the client."
        ),
    )

    client_uri = wtforms.URLField(
        _("URI"),
        validators=[
            wtforms.validators.DataRequired(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example"},
        description=_(
            "URL string of a web page providing information about the client."
        ),
    )

    redirect_uris = wtforms.FieldList(
        wtforms.URLField(
            _("Redirect URIs"),
            validators=[
                wtforms.validators.DataRequired(),
                is_uri,
            ],
            render_kw={"placeholder": "https://client.example/oauth/callback"},
        ),
        min_entries=1,
        validators=[unique_values],
        description=_(
            "URIs for use in redirect-based flows such as the authorization code and implicit flows."
        ),
    )
    post_logout_redirect_uris = wtforms.FieldList(
        wtforms.URLField(
            _("Post logout redirect URIs"),
            validators=[
                wtforms.validators.Optional(),
                is_uri,
            ],
            render_kw={"placeholder": "https://client.example/oauth/logout-callback"},
        ),
        min_entries=1,
        validators=[unique_values],
        description=_(
            "URIs that the client may redirect users to after logging them out."
        ),
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
            ("urn:ietf:params:oauth:grant-type:jwt-bearer", "jwt-bearer"),
        ],
        default=["authorization_code", "refresh_token"],
        description=_("Grant types that the client can use at the token endpoint."),
    )

    scope = wtforms.StringField(
        _("Scope"),
        validators=[wtforms.validators.DataRequired()],
        default="openid profile email",
        render_kw={"placeholder": "openid profile"},
        description=_("Kind of information that the client can request about users."),
    )

    response_types = wtforms.SelectMultipleField(
        _("Response types"),
        validators=[wtforms.validators.DataRequired()],
        choices=[("code", "code"), ("token", "token"), ("id_token", "id_token")],
        default=["code"],
        description=_(
            "Response types that the client can use at the authorization endpoint."
        ),
    )

    token_endpoint_auth_method = wtforms.SelectField(
        _("Token endpoint authentication method"),
        validators=[wtforms.validators.DataRequired()],
        choices=[
            ("client_secret_basic", "client_secret_basic"),
            ("client_secret_post", "client_secret_post"),
            ("client_secret_jwt", "client_secret_jwt"),
            ("private_key_jwt", "private_key_jwt"),
            ("none", "none"),
        ],
        default="client_secret_basic",
        description=_(
            "Authentication method that the client will use at the token endpoint."
        ),
    )

    audience = wtforms.SelectMultipleField(
        _("Token audiences"),
        validators=[wtforms.validators.Optional()],
        choices=_client_audiences,
        validate_choice=False,
        coerce=IDToModel("Client"),
        description=_(
            "The other clients that are intended to use the tokens emitted by this client."
        ),
    )

    logo_uri = wtforms.URLField(
        _("Logo URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/logo.png"},
        description=_("An URL for the logo of this client."),
    )

    tos_uri = wtforms.URLField(
        _("Terms of service URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/tos.html"},
        description=_("URL to the terms of service of the client."),
    )

    policy_uri = wtforms.URLField(
        _("Policy URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/policy.html"},
        description=_("URL to the privacy policy of the client."),
    )

    software_id = wtforms.StringField(
        _("Software ID"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "xyz"},
        description=_(
            "Unique identifier for this client, that should be stable in time and common for all identity providers."
        ),
    )

    software_version = wtforms.StringField(
        _("Software Version"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "1.0"},
        description=_("The version of the client."),
    )

    jwks = wtforms.StringField(
        _("JSON Web Keys"),
        validators=[wtforms.validators.Optional(), is_jwks],
        render_kw={"placeholder": ""},
        description=_("The public JSON Web Keys of the client."),
    )

    jwks_uri = wtforms.URLField(
        _("JSON Web Keys URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/oauth/jwks.json"},
        description=_("The URI that points to the public JSON Web Keys of the client."),
    )

    trusted = wtforms.BooleanField(
        _("Trusted"),
        validators=[wtforms.validators.Optional()],
        default=False,
        description=_("Whether the clients needs to display consent dialogs."),
    )


class TokenRevokationForm(Form):
    pass
