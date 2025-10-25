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
from canaille.oidc.metadata import openid_configuration


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


def _get_algorithm_choices(metadata_key, include_empty=True):
    """Extract algorithm choices from metadata."""
    metadata = openid_configuration()
    algorithms = metadata.get(metadata_key) or []

    choices = []
    if include_empty:
        choices.append(("", _("None")))

    for alg in algorithms:
        if alg:
            choices.append((alg, alg))

    return choices


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

    token_endpoint_auth_signing_alg = wtforms.SelectField(
        _("Token endpoint authentication signing algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices(
            "token_endpoint_auth_signing_alg_values_supported"
        ),
        description=_(
            "JWS algorithm that must be used for signing the JWT used to authenticate the client at the token endpoint for the private_key_jwt and client_secret_jwt authentication methods."
        ),
    )

    sector_identifier_uri = wtforms.URLField(
        _("Sector identifier URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/sector.json"},
        description=_(
            "URL using the https scheme to be used in calculating pseudonymous identifiers by the OP. The URL references a file with a single JSON array of redirect_uri values."
        ),
    )

    subject_type = wtforms.SelectField(
        _("Subject type"),
        validators=[wtforms.validators.Optional()],
        choices=[
            ("", _("None")),
            ("public", "public"),
            ("pairwise", "pairwise"),
        ],
        description=_(
            "Subject identifier type requested for responses to this client. Valid types include pairwise and public."
        ),
    )

    application_type = wtforms.SelectField(
        _("Application type"),
        validators=[wtforms.validators.Optional()],
        choices=[
            ("web", "web"),
            ("native", "native"),
        ],
        default="web",
        description=_(
            "Kind of the application. Web clients must use https redirect URIs. Native clients can use custom URI schemes or http loopback URLs."
        ),
    )

    id_token_signed_response_alg = wtforms.SelectField(
        _("ID Token signed response algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices(
            "id_token_signing_alg_values_supported", include_empty=False
        ),
        default="RS256",
        description=_(
            "JWS algorithm required for signing the ID Token issued to this client. The value 'none' must not be used unless the client uses only response types that return no ID Token from the authorization endpoint."
        ),
    )

    userinfo_signed_response_alg = wtforms.SelectField(
        _("UserInfo signed response algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices("userinfo_signing_alg_values_supported"),
        description=_(
            "JWS algorithm required for signing UserInfo responses. If specified, the response will be JWT serialized and signed using JWS. If omitted, the UserInfo response will return the claims as a UTF-8 encoded JSON object using the application/json content-type."
        ),
    )

    default_max_age = wtforms.IntegerField(
        _("Default maximum authentication age"),
        validators=[wtforms.validators.Optional()],
        render_kw={"placeholder": "3600"},
        description=_(
            "Default maximum authentication age in seconds. Specifies that the end-user must be actively authenticated if the end-user was authenticated longer ago than the specified number of seconds. The max_age request parameter overrides this default value."
        ),
    )

    require_auth_time = wtforms.BooleanField(
        _("Require auth_time claim"),
        default=False,
        description=_(
            "Boolean value specifying whether the auth_time claim in the ID Token is required. It is required when the value is true."
        ),
    )

    default_acr_values = wtforms.FieldList(
        wtforms.StringField(
            _("Default ACR values"),
            validators=[wtforms.validators.Optional()],
            render_kw={"placeholder": "urn:mace:incommon:iap:silver"},
        ),
        min_entries=1,
        validators=[unique_values],
        description=_(
            "Default requested Authentication Context Class Reference values. Array of strings that specifies the default acr values that the OP is being requested to use for processing requests from this client, with the values appearing in order of preference."
        ),
    )

    initiate_login_uri = wtforms.URLField(
        _("Initiate login URI"),
        validators=[
            wtforms.validators.Optional(),
            is_uri,
        ],
        render_kw={"placeholder": "https://client.example/login"},
        description=_(
            "URI using the https scheme that a third party can use to initiate a login by the RP. The URI must accept requests via both GET and POST."
        ),
    )

    request_object_signing_alg = wtforms.SelectField(
        _("Request object signing algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices(
            "request_object_signing_alg_values_supported"
        ),
        description=_(
            "JWS algorithm that must be used for signing request objects sent to the OP. All request objects from this client must be rejected if not signed with this algorithm. This algorithm must be used both when the request object is passed by value (using the request parameter) and when it is passed by reference (using the request_uri parameter)."
        ),
    )

    request_uris = wtforms.FieldList(
        wtforms.URLField(
            _("Request URIs"),
            validators=[
                wtforms.validators.Optional(),
                is_uri,
            ],
            render_kw={
                "placeholder": "https://client.example/request.jwt#GkurKxf5T0Y-mnPFCHqWOMiZi4VS138cQO_V7PZHAdM"
            },
        ),
        min_entries=1,
        validators=[unique_values],
        description=_(
            "Array of request_uri values that are pre-registered by the RP for use at the OP. These URLs must use the https scheme unless the target request object is signed in a way that is verifiable by the OP. Servers may cache the contents of the files referenced by these URIs."
        ),
    )

    require_signed_request_object = wtforms.BooleanField(
        _("Require signed request object"),
        default=False,
        description=_(
            "Indicates whether authorization request needs to be protected as a request object and provided through either request or request_uri parameter."
        ),
    )


class TokenRevokationForm(Form):
    pass
