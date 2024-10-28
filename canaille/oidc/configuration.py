from pydantic import BaseModel


class JWTMappingSettings(BaseModel):
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


class JWTSettings(BaseModel):
    """JSON Web Token settings. Belong in the ``CANAILLE_OIDC.JWT`` namespace.

    You can generate a RSA keypair with::

        openssl genrsa -out private.pem 4096
        openssl rsa -in private.pem -pubout -outform PEM -out public.pem
    """

    PRIVATE_KEY: str | None = None
    """The private key.

    If :py:data:`None` and debug mode is enabled, then an in-memory key will be used.
    """

    PUBLIC_KEY: str | None = None
    """The public key.

    If :py:data:`None` and debug mode is enabled, then an in-memory key will be used.
    """

    ISS: str | None = None
    """The URI of the identity provider."""

    KTY: str = "RSA"
    """The key type."""

    ALG: str = "RS256"
    """The key algorithm."""

    EXP: int = 3600
    """The time the JWT will be valid, in seconds."""

    MAPPING: JWTMappingSettings | None = JWTMappingSettings()


class OIDCSettings(BaseModel):
    """OpenID Connect settings.

    Belong in the ``CANAILLE_OIDC`` namespace.
    """

    DYNAMIC_CLIENT_REGISTRATION_OPEN: bool = False
    """Whether a token is needed for the RFC7591 dynamical client registration.

    If :py:data:`True`, no token is needed to register a client.
    If :py:data:`False`, dynamical client registration needs a token defined in
    :attr:`DYNAMIC_CLIENT_REGISTRATION_TOKENS`.
    """

    DYNAMIC_CLIENT_REGISTRATION_TOKENS: list[str] | None = None
    """A list of tokens that can be used for dynamic client registration."""

    REQUIRE_NONCE: bool = True
    """Force the nonce exchange during the authentication flows.

    This adds security but may not be supported by all clients.
    """

    JWT: JWTSettings = JWTSettings()
    """JSON Web Token settings."""
