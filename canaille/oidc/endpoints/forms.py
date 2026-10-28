import json

import wtforms
from flask import current_app
from joserfc.jwk import KeySet
from wtforms_htmx_components import ComboboxMultiField

from canaille.app import models
from canaille.app.combobox import ChipsWidget
from canaille.app.combobox import ListboxWidget
from canaille.app.forms import DateTimeUTCField
from canaille.app.forms import Form
from canaille.app.forms import email_validator
from canaille.app.forms import fieldlist_buttons
from canaille.app.forms import is_uri
from canaille.app.forms import unique_values
from canaille.app.i18n import lazy_gettext as _
from canaille.backends import Backend
from canaille.core.endpoints.forms import describe_user
from canaille.oidc.jose import supported_signing_algorithms
from canaille.oidc.jose import supported_verification_algorithms
from canaille.oidc.models import OWNED_CLIENT_FORBIDDEN_GRANT_TYPES
from canaille.oidc.models import managed_owners
from canaille.oidc.models import owns_group
from canaille.oidc.utils import SCOPE_DETAILS


class AuthorizeForm(Form):
    answer = wtforms.ButtonField()


class LogoutForm(Form):
    answer = wtforms.ButtonField()


class DeviceForm(Form):
    """User code entry form for the RFC 8628 device verification endpoint."""

    user_code = wtforms.StringField(
        _("Code"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"autocomplete": "off", "autofocus": True},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_code_type = current_app.config["CANAILLE_OIDC"]["DEVICE_USER_CODE_TYPE"]
        self.user_code.render_kw = {
            **self.user_code.render_kw,
            "placeholder": "019-450-730"
            if user_code_type == "digital"
            else "WDJB-MJHT",
        }


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


def _get_algorithm_choices(algorithms, include_empty=True):
    """Build the choices for a JWS algorithm field."""
    choices = []
    if include_empty:
        choices.append(wtforms.SelectChoice(value="", label=_("None")))

    for alg in algorithms:
        choices.append(wtforms.SelectChoice(value=alg, label=alg))

    return choices


def describe_group(group):
    """Return the name of ``group``, telling it is a group."""
    return str(_("%(name)s (group)", name=group.display_name))


USER_SCOPES = {"openid", *SCOPE_DETAILS}
"""The scopes that users who cannot manage all clients can give to their clients."""


OWNER_MODELS = {
    "user": ("User", ["user_name", "formatted_name", "emails"], describe_user),
    "group": ("Group", ["display_name"], describe_group),
}
"""The models that can own a client, by the prefix of their combobox values."""


def owners_combobox():
    """Return a combobox field that picks users and groups as client owners.

    The values are the model prefix and the instance id, like ``user:<id>``.
    """

    def suggest(query, form):
        if not form.user.can("manage_oidc"):
            if not form.user.can("manage_own_groups"):
                return

            for group in Backend.instance.fuzzy(
                models.Group, query, ["display_name"], owners=form.user
            ):
                yield wtforms.SelectChoice(f"group:{group.id}", describe_group(group))
            return

        for prefix, (model_name, attributes, describe) in OWNER_MODELS.items():
            model = getattr(models, model_name)
            for instance in Backend.instance.fuzzy(model, query, attributes):
                yield wtforms.SelectChoice(
                    f"{prefix}:{instance.id}", describe(instance)
                )

    def coerce(value):
        prefix, _separator, instance_id = value.partition(":")
        if prefix in OWNER_MODELS:
            model = getattr(models, OWNER_MODELS[prefix][0])
            if instance := Backend.instance.get(model, id=instance_id):
                return instance

        raise ValueError(value)

    def value_for(owner):
        prefix = "group" if isinstance(owner, models.Group) else "user"
        return f"{prefix}:{owner.id}"

    def label_for(value):
        try:
            owner = coerce(value)
        except ValueError:
            return value

        prefix = value.partition(":")[0]
        return OWNER_MODELS[prefix][2](owner)

    return ComboboxMultiField(
        _("Owners"),
        suggest=suggest,
        label_for=label_for,
        coerce=coerce,
        value_for=value_for,
        search_label=_("Search"),
        listbox_widget=ListboxWidget(),
        chips_widget=ChipsWidget(),
        placeholder=_("Jane Doe, admins …"),
        description=_(
            "The users or groups who own this client. "
            "For group owners: the group owner can edit the client, "
            "while group members can use it for authentication. "
            "Leave empty for a global client accessible to all users."
        ),
    )


def is_shareable_with(owner, user):
    """Tell whether ``user`` can add ``owner`` to, or remove it from, a client they own."""
    return owner == user or (
        isinstance(owner, models.Group) and owns_group(user, owner)
    )


def audience_combobox():
    """Return a combobox field that picks the clients intended to use the tokens.

    The users who cannot manage all clients only find the clients they can edit.
    The edited client is not suggested, as it is always part of its audience.
    """

    def suggest(query, form):
        filter = (
            {}
            if form.user.can("manage_oidc")
            else {"owners": managed_owners(form.user)}
        )
        for client in Backend.instance.fuzzy(
            models.Client, query, ["client_name", "client_id"], **filter
        ):
            if client != form.client:
                yield wtforms.SelectChoice(client.id, client.client_name)

    def coerce(client_id):
        if client := Backend.instance.get(models.Client, id=client_id):
            return client

        raise ValueError(client_id)

    def label_for(client_id):
        client = Backend.instance.get(models.Client, id=client_id)
        return client.client_name if client else client_id

    return ComboboxMultiField(
        _("Token audiences"),
        suggest=suggest,
        label_for=label_for,
        coerce=coerce,
        value_for=lambda client: client.id,
        search_label=_("Search"),
        listbox_widget=ListboxWidget(),
        chips_widget=ChipsWidget(),
        placeholder=_("Client name …"),
        description=_(
            "The other clients that are intended to use the tokens emitted by this client."
        ),
    )


class ClientAddForm(Form):
    owners = owners_combobox()

    def __init__(self, *args, user, client=None, **kwargs):
        self.user = user
        self.client = client
        super().__init__(*args, **kwargs)
        if not user.can("manage_oidc"):
            self.owners.description = _(
                "You and the groups you own that own this client. "
                "The group members can use the client."
            )

    def validate_owners(self, field):
        """Let the users who cannot manage all clients share them with their groups only.

        They cannot add themselves back, so they lose the edition with the groups they lose.
        """
        if self.user.can("manage_oidc"):
            return

        previous = set(self.client.owners) if self.client else {self.user}
        added = set(field.data) - previous
        removed = previous - set(field.data)
        if self.user in added or not all(
            is_shareable_with(owner, self.user) for owner in added | removed
        ):
            raise wtforms.ValidationError(
                _(
                    "You can only add the groups you own, "
                    "and remove yourself or the groups you own."
                )
            )

        if not any(is_shareable_with(owner, self.user) for owner in field.data):
            raise wtforms.ValidationError(
                _("You would not be able to edit this client anymore.")
            )

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
    add_contacts, del_contacts = fieldlist_buttons("contacts")

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
    add_redirect_uris, del_redirect_uris = fieldlist_buttons("redirect_uris")


class ClientEditForm(ClientAddForm):
    """Complete form for editing a client with all metadata fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.user.can("manage_oidc"):
            self.grant_types.choices = {
                value: label
                for value, label in self.grant_types.choices.items()
                if value not in OWNED_CLIENT_FORBIDDEN_GRANT_TYPES
            }
            self.scope.description = _(
                "Kind of information that the client can request about users. "
                "You can pick among: {scopes}."
            ).format(scopes=" ".join(sorted(USER_SCOPES)))

    def validate_scope(self, field):
        """Let the users who cannot manage all clients add the scopes users can consent to only."""
        if self.user.can("manage_oidc"):
            return

        added = set(field.data.split()) - set(self.client.scope or [])
        if forbidden := added - USER_SCOPES:
            raise wtforms.ValidationError(
                _("You cannot add the {scopes} scopes.").format(
                    scopes=", ".join(sorted(forbidden))
                )
            )

    def validate_audience(self, field):
        """Let the users who cannot manage all clients pick the clients they can edit only."""
        if self.user.can("manage_oidc"):
            return

        changed = set(self.client.audience) ^ set(field.data)
        if not all(client.is_editable_by(self.user) for client in changed):
            raise wtforms.ValidationError(
                _("You can only add or remove the clients you can edit.")
            )

    def validate_grant_types(self, field):
        owners = self.owners.data
        forbidden = OWNED_CLIENT_FORBIDDEN_GRANT_TYPES & set(field.data)
        if owners and forbidden:
            raise wtforms.ValidationError(
                _(
                    "Clients with owners cannot use the {grant_types} grant types."
                ).format(grant_types=", ".join(sorted(forbidden)))
            )

    client_secret_expires_at = DateTimeUTCField(
        _("Secret expiration"),
        validators=[wtforms.validators.Optional()],
        format=[
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ],
        description=_(
            "Date after which the client secret cannot be used to authenticate anymore. Leave this empty so the secret never expires."
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
    add_post_logout_redirect_uris, del_post_logout_redirect_uris = fieldlist_buttons(
        "post_logout_redirect_uris"
    )

    grant_types = wtforms.SelectMultipleField(
        _("Grant types"),
        validators=[wtforms.validators.DataRequired()],
        choices={
            "password": "password",
            "authorization_code": "authorization_code",
            "implicit": "implicit",
            "hybrid": "hybrid",
            "refresh_token": "refresh_token",
            "client_credentials": "client_credentials",
            "urn:ietf:params:oauth:grant-type:jwt-bearer": "jwt-bearer",
            "urn:ietf:params:oauth:grant-type:device_code": "device_code",
        },
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
        choices={"code": "code", "token": "token", "id_token": "id_token"},
        default=["code"],
        description=_(
            "Response types that the client can use at the authorization endpoint."
        ),
    )

    token_endpoint_auth_method = wtforms.SelectField(
        _("Token endpoint authentication method"),
        validators=[wtforms.validators.DataRequired()],
        choices={
            "client_secret_basic": "client_secret_basic",
            "client_secret_post": "client_secret_post",
            "client_secret_jwt": "client_secret_jwt",
            "private_key_jwt": "private_key_jwt",
            "none": "none",
        },
        default="client_secret_basic",
        description=_(
            "Authentication method that the client will use at the token endpoint."
        ),
    )

    audience = audience_combobox()

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
            supported_verification_algorithms(excluded=["none"])
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
            wtforms.SelectChoice(value="", label=_("None")),
            wtforms.SelectChoice(value="public", label="public"),
            wtforms.SelectChoice(value="pairwise", label="pairwise"),
        ],
        description=_(
            "Subject identifier type requested for responses to this client. Valid types include pairwise and public."
        ),
    )

    application_type = wtforms.SelectField(
        _("Application type"),
        validators=[wtforms.validators.Optional()],
        choices={"web": "web", "native": "native"},
        default="web",
        description=_(
            "Kind of the application. Web clients must use https redirect URIs. Native clients can use custom URI schemes or http loopback URLs."
        ),
    )

    id_token_signed_response_alg = wtforms.SelectField(
        _("ID Token signed response algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices(
            supported_signing_algorithms(), include_empty=False
        ),
        default="RS256",
        description=_(
            "JWS algorithm required for signing the ID Token issued to this client. The value 'none' must not be used unless the client uses only response types that return no ID Token from the authorization endpoint."
        ),
    )

    userinfo_signed_response_alg = wtforms.SelectField(
        _("UserInfo signed response algorithm"),
        validators=[wtforms.validators.Optional()],
        choices=lambda: _get_algorithm_choices(supported_signing_algorithms()),
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
    add_default_acr_values, del_default_acr_values = fieldlist_buttons(
        "default_acr_values"
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
        choices=lambda: _get_algorithm_choices(supported_verification_algorithms()),
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
    add_request_uris, del_request_uris = fieldlist_buttons("request_uris")

    require_signed_request_object = wtforms.BooleanField(
        _("Require signed request object"),
        default=False,
        description=_(
            "Indicates whether authorization request needs to be protected as a request object and provided through either request or request_uri parameter."
        ),
    )


class TokenRevokationForm(Form):
    pass
