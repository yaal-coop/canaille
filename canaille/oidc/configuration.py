from canaille.app.configuration import BaseModel
from canaille.app.configuration import CommaSeparatedList


class UserInfoMappingSettings(BaseModel):
    """Mapping between the user model and the JWT fields.

    Fields are evaluated with jinja.
    A ``user`` var is available.
    """

    SUB: str | None = "{{ user.user_name }}"
    NAME: str | None = (
        "{% if user.formatted_name %}{{ user.formatted_name }}{% endif %}"
    )
    PHONE_NUMBER: str | None = (
        "{% if user.phone_numbers %}{{ user.phone_numbers[0] }}{% endif %}"
    )
    EMAIL: str | None = (
        "{% if user.preferred_email %}{{ user.preferred_email }}{% endif %}"
    )
    GIVEN_NAME: str | None = "{% if user.given_name %}{{ user.given_name }}{% endif %}"
    FAMILY_NAME: str | None = (
        "{% if user.family_name %}{{ user.family_name }}{% endif %}"
    )
    PREFERRED_USERNAME: str | None = (
        "{% if user.display_name %}{{ user.display_name }}{% endif %}"
    )
    LOCALE: str | None = (
        "{% if user.preferred_language %}{{ user.preferred_language }}{% endif %}"
    )
    ADDRESS: str | None = (
        "{% if user.formatted_address %}{{ user.formatted_address }}{% endif %}"
    )
    PICTURE: str | None = (
        "{% if user.photo %}{{ url_for('core.account.photo', user=user, field='photo', _external=True) }}{% endif %}"
    )
    WEBSITE: str | None = "{% if user.profile_url %}{{ user.profile_url }}{% endif %}"
    UPDATED_AT: str | None = (
        "{% if user.last_modified %}{{ user.last_modified.timestamp() }}{% endif %}"
    )


class OIDCSettings(BaseModel):
    """OpenID Connect settings.

    Belong in the ``CANAILLE_OIDC`` namespace.
    """

    ENABLE_OIDC: bool = True
    """Whether the Single Sign-On feature and the OpenID Connect API is enabled."""

    DYNAMIC_CLIENT_REGISTRATION_OPEN: bool = False
    """Whether a token is needed for the RFC7591 dynamical client registration.

    If :py:data:`True`, no token is needed to register a client.
    If :py:data:`False`, dynamical client registration needs a token defined in
    :attr:`DYNAMIC_CLIENT_REGISTRATION_TOKENS`.
    """

    DYNAMIC_CLIENT_REGISTRATION_TOKENS: CommaSeparatedList | None = None
    """A list of tokens that can be used for dynamic client registration."""

    REQUIRE_NONCE: bool = True
    """Force the nonce exchange during the authentication flows.

    This adds security but may not be supported by all clients.
    """

    ACTIVE_JWKS: list[dict[str, str]] | None = None
    """The active JSON Web Keys Set.

    Those keys are used to sign and verify JWTs."""

    INACTIVE_JWKS: list[dict[str, str]] | None = None
    """The inactive JSON Web Keys Set.

    Those keys are only used to verify JWTs."""

    USERINFO_MAPPING: UserInfoMappingSettings | None = UserInfoMappingSettings()
    """"Attribute mapping used to build an OIDC UserInfo object.

    UserInfo is used to fill the id_token and the userinfo endpoint."""

    TRUSTED_DOMAINS: CommaSeparatedList = [".localhost", "127.0.0.1"]
    """Trusted domains for automatic client trust.

    Clients with a :attr:`~canaille.oidc.basemodels.Client.client_uri` matching
    these domains will be automatically considered as trusted and will not
    display the consent page to users.
    This is particularly useful for development environments.

    Supports these patterns:

    - Exact match: ``example.com`` matches ``example.com``
    - Wildcard match: ``.example.com`` matches ``example.com`` and all its subdomains

    Examples:

    - ``[".localhost", "127.0.0.1"]`` (default for development)
    - ``[".dev.company.com", "staging.company.com"]``
    - ``[".local", "localhost"]``
    """
