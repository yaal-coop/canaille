from typing import List
from typing import Optional

from pydantic import BaseModel


class JWTMappingSettings(BaseModel):
    """Mapping between the user model and the JWT fields.

    Fiels are evaluated with jinja.
    A ``user`` var is available.
    """

    SUB: Optional[str] = "{{ user.user_name }}"
    NAME: Optional[str] = "{{ user.formatted_name }}"
    PHONE_NUMBER: Optional[str] = "{{ user.phone_numbers[0] }}"
    EMAIL: Optional[str] = "{{ user.preferred_email }}"
    GIVEN_NAME: Optional[str] = "{{ user.given_name }}"
    FAMILY_NAME: Optional[str] = "{{ user.family_name }}"
    PREFERRED_USERNAME: Optional[str] = "{{ user.display_name }}"
    LOCALE: Optional[str] = "{{ user.preferred_language }}"
    ADDRESS: Optional[str] = "{{ user.formatted_address }}"
    PICTURE: Optional[str] = (
        "{% if user.photo %}{{ url_for('core.account.photo', user=user, field='photo', _external=True) }}{% endif %}"
    )
    WEBSITE: Optional[str] = "{{ user.profile_url }}"


class JWTSettings(BaseModel):
    """JSON Web Token settings. Belong in the ``CANAILLE_OIDC.JWT`` namespace.

    You can generate a RSA keypair with::

        openssl genrsa -out private.pem 4096
        openssl rsa -in private.pem -pubout -outform PEM -out public.pem
    """

    PRIVATE_KEY: Optional[str] = None
    """The private key.

    If :py:data:`None` and debug mode is enabled, then an in-memory key will be used.
    """

    PUBLIC_KEY: Optional[str] = None
    """The public key.

    If :py:data:`None` and debug mode is enabled, then an in-memory key will be used.
    """

    ISS: Optional[str] = None
    """The URI of the identity provider."""

    KTY: str = "RSA"
    """The key type."""

    ALG: str = "RS256"
    """The key algorithm."""

    EXP: int = 3600
    """The time the JWT will be valid, in seconds."""

    MAPPING: Optional[JWTMappingSettings] = None


class OIDCSettings(BaseModel):
    """OpenID Connect settings.

    Belong in the ``CANAILLE_OIDC`` namespace.
    """

    DYNAMIC_CLIENT_REGISTRATION_OPEN: bool = False
    """Wether a token is needed for the RFC7591 dynamical client registration.

    If :py:data:`True`, no token is needed to register a client.
    If :py:data:`False`, dynamical client registration needs a token defined in :attr:`DYNAMIC_CLIENT_REGISTRATION_TOKENS`.
    """

    DYNAMIC_CLIENT_REGISTRATION_TOKENS: Optional[List[str]] = None
    """A list of tokens that can be used for dynamic client registration."""

    REQUIRE_NONCE: bool = True
    """Force the nonce exchange during the authentication flows.

    This adds security but may not be supported by all clients.
    """

    JWT: Optional[JWTSettings] = None
    """JSON Web Token settings."""
