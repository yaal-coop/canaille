import datetime
from typing import List
from typing import Optional

from canaille.backends.models import Model
from canaille.core.models import User


class Client(Model):
    """
    OpenID Connect client definition, based on the
    `OAuth 2.0 Dynamic Client Registration protocols
    <https://datatracker.ietf.org/doc/html/rfc7591.html>`_
    and the `OpenID Connect RP-Initiated Logout
    <https://openid.net/specs/openid-connect-rpinitiated-1_0.html>`_
    specifications.
    """

    id: str
    description: Optional[str]
    preconsent: Optional[bool]
    audience: List["Client"]

    client_id: Optional[str]
    """REQUIRED.

    OAuth 2.0 client identifier string.  It SHOULD NOT be currently
    valid for any other registered client, though an authorization
    server MAY issue the same client identifier to multiple instances of
    a registered client at its discretion.
    """

    client_secret: Optional[str]
    """OPTIONAL.

    OAuth 2.0 client secret string.  If issued, this MUST be unique for
    each "client_id" and SHOULD be unique for multiple instances of a
    client using the same "client_id".  This value is used by
    confidential clients to authenticate to the token endpoint, as
    described in OAuth 2.0 [RFC6749], Section 2.3.1.
    """

    client_id_issued_at: Optional[datetime.datetime]
    """OPTIONAL.

    Time at which the client identifier was issued.  The time is
    represented as the number of seconds from 1970-01-01T00:00:00Z as
    measured in UTC until the date/time of issuance.
    """

    client_secret_expires_at: Optional[datetime.datetime]
    """REQUIRED if "client_secret" is issued.

    Time at which the client secret will expire or 0 if it will not
    expire.  The time is represented as the number of seconds from
    1970-01-01T00:00:00Z as measured in UTC until the date/time of
    expiration.
    """

    redirect_uris: List[str]
    """Array of redirection URI strings for use in redirect-based flows such as
    the authorization code and implicit flows.

    As required by Section 2 of OAuth 2.0 [RFC6749], clients using flows
    with redirection MUST register their redirection URI values.
    Authorization servers that support dynamic registration for
    redirect-based flows MUST implement support for this metadata value.
    """

    token_endpoint_auth_method: Optional[str]
    """String indicator of the requested authentication method for the token
    endpoint.  Values defined by this specification are:

    *  "none": The client is a public client as defined in OAuth 2.0,
       Section 2.1, and does not have a client secret.

    *  "client_secret_post": The client uses the HTTP POST parameters
       as defined in OAuth 2.0, Section 2.3.1.

    *  "client_secret_basic": The client uses HTTP Basic as defined in
       OAuth 2.0, Section 2.3.1.

    Additional values can be defined via the IANA "OAuth Token
    Endpoint Authentication Methods" registry established in
    Section 4.2.  Absolute URIs can also be used as values for this
    parameter without being registered.  If unspecified or omitted,
    the default is "client_secret_basic", denoting the HTTP Basic
    authentication scheme as specified in Section 2.3.1 of OAuth 2.0.
    """

    grant_types: List[str]
    """Array of OAuth 2.0 grant type strings that the client can use at the
    token endpoint.  These grant types are defined as follows:

    *  "authorization_code": The authorization code grant type defined
       in OAuth 2.0, Section 4.1.

    *  "implicit": The implicit grant type defined in OAuth 2.0,
       Section 4.2.

    *  "password": The resource owner password credentials grant type
       defined in OAuth 2.0, Section 4.3.

    *  "client_credentials": The client credentials grant type defined
       in OAuth 2.0, Section 4.4.

    *  "refresh_token": The refresh token grant type defined in OAuth
       2.0, Section 6.

    *  "urn:ietf:params:oauth:grant-type:jwt-bearer": The JWT Bearer
       Token Grant Type defined in OAuth JWT Bearer Token Profiles
       [RFC7523].

    *  "urn:ietf:params:oauth:grant-type:saml2-bearer": The SAML 2.0
       Bearer Assertion Grant defined in OAuth SAML 2 Bearer Token
       Profiles [RFC7522].

    If the token endpoint is used in the grant type, the value of this
    parameter MUST be the same as the value of the "grant_type"
    parameter passed to the token endpoint defined in the grant type
    definition.  Authorization servers MAY allow for other values as
    defined in the grant type extension process described in OAuth
    2.0, Section 4.5.  If omitted, the default behavior is that the
    client will use only the "authorization_code" Grant Type.
    """

    response_types: List[str]
    """
    Array of the OAuth 2.0 response type strings that the client can
    use at the authorization endpoint.  These response types are
    defined as follows:

    *  "code": The authorization code response type defined in OAuth
       2.0, Section 4.1.

    *  "token": The implicit response type defined in OAuth 2.0,
       Section 4.2.

    If the authorization endpoint is used by the grant type, the value
    of this parameter MUST be the same as the value of the
    "response_type" parameter passed to the authorization endpoint
    defined in the grant type definition.  Authorization servers MAY
    allow for other values as defined in the grant type extension
    process is described in OAuth 2.0, Section 4.5.  If omitted, the
    default is that the client will use only the "code" response type.
    """

    client_name: Optional[str]
    """Human-readable string name of the client to be presented to the end-user
    during authorization.

    If omitted, the authorization server MAY display the raw "client_id"
    value to the end-user instead.  It is RECOMMENDED that clients
    always send this field. The value of this field MAY be
    internationalized, as described in Section 2.2.
    """

    client_uri: Optional[str]
    """URL string of a web page providing information about the client.

    If present, the server SHOULD display this URL to the end-user in a
    clickable fashion.  It is RECOMMENDED that clients always send this
    field.  The value of this field MUST point to a valid web page.  The
    value of this field MAY be internationalized, as described in
    Section 2.2.
    """

    logo_uri: Optional[str]
    """URL string that references a logo for the client.

    If present, the server SHOULD display this image to the end-user
    during approval. The value of this field MUST point to a valid image
    file.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    scope: List[str]
    """String containing a space-separated list of scope values (as described
    in Section 3.3 of OAuth 2.0 [RFC6749]) that the client can use when
    requesting access tokens.

    The semantics of values in this list are service specific.  If
    omitted, an authorization server MAY register a client with a
    default set of scopes.
    """

    contacts: List[str]
    """Array of strings representing ways to contact people responsible for
    this client, typically email addresses.

    The authorization server MAY make these contact addresses available
    to end-users for support requests for the client.  See Section 6 for
    information on Privacy Considerations.
    """

    tos_uri: Optional[str]
    """URL string that points to a human-readable terms of service document for
    the client that describes a contractual relationship between the end-user
    and the client that the end-user accepts when authorizing the client.

    The authorization server SHOULD display this URL to the end-user if
    it is provided.  The value of this field MUST point to a valid web
    page.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    policy_uri: Optional[str]
    """URL string that points to a human-readable privacy policy document that
    describes how the deployment organization collects, uses, retains, and
    discloses personal data.

    The authorization server SHOULD display this URL to the end-user if
    it is provided.  The value of this field MUST point to a valid web
    page.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    jwks_uri: Optional[str]
    """URL string referencing the client's JSON Web Key (JWK) Set [RFC7517]
    document, which contains the client's public keys.

    The value of this field MUST point to a valid JWK Set document.
    These keys can be used by higher-level protocols that use signing or
    encryption.  For instance, these keys might be used by some
    applications for validating signed requests made to the token
    endpoint when using JWTs for client authentication [RFC7523].  Use
    of this parameter is preferred over the "jwks" parameter, as it
    allows for easier key rotation.  The "jwks_uri" and "jwks"
    parameters MUST NOT both be present in the same request or response.
    """

    jwk: Optional[str]
    """Client's JSON Web Key Set [RFC7517] document value, which contains the
    client's public keys.

    The value of this field MUST be a JSON object containing a valid JWK
    Set.  These keys can be used by higher-level protocols that use
    signing or encryption.  This parameter is intended to be used by
    clients that cannot use the "jwks_uri" parameter, such as native
    clients that cannot host public URLs.  The "jwks_uri" and "jwks"
    parameters MUST NOT both be present in the same request or response.
    """

    software_id: Optional[str]
    """A unique identifier string (e.g., a Universally Unique Identifier
    (UUID)) assigned by the client developer or software publisher used by
    registration endpoints to identify the client software to be dynamically
    registered.

    Unlike "client_id", which is issued by the authorization server and
    SHOULD vary between instances, the "software_id" SHOULD remain the
    same for all instances of the client software.  The "software_id"
    SHOULD remain the same across multiple updates or versions of the
    same piece of software.  The value of this field is not intended to
    be human readable and is usually opaque to the client and
    authorization server.
    """

    software_version: Optional[str]
    """A version identifier string for the client software identified by
    "software_id".

    The value of the "software_version" SHOULD change on any update to
    the client software identified by the same "software_id".  The value
    of this field is intended to be compared using string equality
    matching and no other comparison semantics are defined by this
    specification.  The value of this field is outside the scope of this
    specification, but it is not intended to be human readable and is
    usually opaque to the client and authorization server.  The
    definition of what constitutes an update to client software that
    would trigger a change to this value is specific to the software
    itself and is outside the scope of this specification.
    """

    post_logout_redirect_uris: List[str]
    """OPTIONAL.

    Array of URLs supplied by the RP to which it MAY request that the
    End-User's User Agent be redirected using the
    post_logout_redirect_uri parameter after a logout has been
    performed. These URLs SHOULD use the https scheme and MAY contain
    port, path, and query parameter components; however, they MAY use
    the http scheme, provided that the Client Type is confidential, as
    defined in Section 2.1 of OAuth 2.0 [RFC6749], and provided the OP
    allows the use of http RP URIs.
    """


class AuthorizationCode(Model):
    """OpenID Connect temporary authorization code definition."""

    id: str
    authorization_code_id: str
    code: str
    client: "Client"
    subject: User
    redirect_uri: Optional[str]
    response_type: Optional[str]
    scope: List[str]
    nonce: Optional[str]
    issue_date: datetime.datetime
    lifetime: int
    challenge: Optional[str]
    challenge_method: Optional[str]
    revokation_date: datetime.datetime


class Token(Model):
    """OpenID Connect token definition."""

    id: str
    token_id: str
    access_token: str
    client: "Client"
    subject: User
    type: str
    refresh_token: str
    scope: List[str]
    issue_date: datetime.datetime
    lifetime: int
    revokation_date: datetime.datetime
    audience: List["Client"]


class Consent(Model):
    """Long-term user consent to an application."""

    id: str
    consent_id: str
    subject: User
    client: "Client"
    scope: List[str]
    issue_date: datetime.datetime
    revokation_date: datetime.datetime

    def revoke(self):
        raise NotImplementedError()

    def restore(self):
        raise NotImplementedError()
