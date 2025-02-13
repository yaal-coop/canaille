import datetime
from typing import ClassVar

# keep 'List' instead of 'list' for audiences to not break py310 with the memory backend
from typing import List  # noqa: UP035

from canaille.backends.models import Model
from canaille.core.models import User


class Client(Model):
    """OpenID Connect client definition.

    Based on the :rfc:`OAuth 2.0 Dynamic Client Registration protocols <7591>` and the
    `OpenID Connect RP-Initiated Logout <https://openid.net/specs/openid-connect-rpinitiated-1_0.html>`_ specifications.
    """

    identifier_attribute: ClassVar[str] = "client_id"

    description: str | None = None
    trusted: bool | None = False
    # keep 'List' instead of 'list' do not break py310 with the memory backend
    audience: List["Client"] = []  # noqa: UP006

    client_id: str | None
    """REQUIRED.

    OAuth 2.0 client identifier string.  It SHOULD NOT be currently
    valid for any other registered client, though an authorization
    server MAY issue the same client identifier to multiple instances of
    a registered client at its discretion.
    """

    client_secret: str | None = None
    """OPTIONAL.

    OAuth 2.0 client secret string.  If issued, this MUST be unique for
    each "client_id" and SHOULD be unique for multiple instances of a
    client using the same "client_id".  This value is used by
    confidential clients to authenticate to the token endpoint, as
    described in OAuth 2.0 [RFC6749], Section 2.3.1.
    """

    client_id_issued_at: datetime.datetime | None = None
    """OPTIONAL.

    Time at which the client identifier was issued.  The time is
    represented as the number of seconds from 1970-01-01T00:00:00Z as
    measured in UTC until the date/time of issuance.
    """

    client_secret_expires_at: datetime.datetime | None = None
    """REQUIRED if "client_secret" is issued.

    Time at which the client secret will expire or 0 if it will not
    expire.  The time is represented as the number of seconds from
    1970-01-01T00:00:00Z as measured in UTC until the date/time of
    expiration.
    """

    redirect_uris: list[str] = []
    """Array of redirection URI strings for use in redirect-based flows such as
    the authorization code and implicit flows.

    As required by Section 2 of OAuth 2.0 [RFC6749], clients using flows
    with redirection MUST register their redirection URI values.
    Authorization servers that support dynamic registration for
    redirect-based flows MUST implement support for this metadata value.
    """

    token_endpoint_auth_method: str | None = None
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

    token_endpoint_auth_signing_alg: str | None = None
    """JWS [JWS] alg algorithm [JWA] that MUST be used for signing the JWT [JWT]
    used to authenticate the Client at the Token Endpoint for the private_key_jwt
    and client_secret_jwt authentication methods. All Token Requests using these
    authentication methods from this Client MUST be rejected, if the JWT is not
    signed with this algorithm. Servers SHOULD support RS256. The value none MUST
    NOT be used. The default, if omitted, is that any algorithm supported by the
    OP and the RP MAY be used."""

    grant_types: list[str] = ["authorization_code", "refresh_token"]
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

    response_types: list[str] = []
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

    client_name: str | None = None
    """Human-readable string name of the client to be presented to the end-user
    during authorization.

    If omitted, the authorization server MAY display the raw "client_id"
    value to the end-user instead.  It is RECOMMENDED that clients
    always send this field. The value of this field MAY be
    internationalized, as described in Section 2.2.
    """

    client_uri: str | None = None
    """URL string of a web page providing information about the client.

    If present, the server SHOULD display this URL to the end-user in a
    clickable fashion.  It is RECOMMENDED that clients always send this
    field.  The value of this field MUST point to a valid web page.  The
    value of this field MAY be internationalized, as described in
    Section 2.2.
    """

    logo_uri: str | None = None
    """URL string that references a logo for the client.

    If present, the server SHOULD display this image to the end-user
    during approval. The value of this field MUST point to a valid image
    file.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    scope: list[str] = []
    """String containing a space-separated list of scope values (as described
    in Section 3.3 of OAuth 2.0 [RFC6749]) that the client can use when
    requesting access tokens.

    The semantics of values in this list are service specific.  If
    omitted, an authorization server MAY register a client with a
    default set of scopes.
    """

    contacts: list[str] = []
    """Array of strings representing ways to contact people responsible for
    this client, typically email addresses.

    The authorization server MAY make these contact addresses available
    to end-users for support requests for the client.  See Section 6 for
    information on Privacy Considerations.
    """

    tos_uri: str | None = None
    """URL string that points to a human-readable terms of service document for
    the client that describes a contractual relationship between the end-user
    and the client that the end-user accepts when authorizing the client.

    The authorization server SHOULD display this URL to the end-user if
    it is provided.  The value of this field MUST point to a valid web
    page.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    policy_uri: str | None = None
    """URL string that points to a human-readable privacy policy document that
    describes how the deployment organization collects, uses, retains, and
    discloses personal data.

    The authorization server SHOULD display this URL to the end-user if
    it is provided.  The value of this field MUST point to a valid web
    page.  The value of this field MAY be internationalized, as
    described in Section 2.2.
    """

    jwks_uri: str | None = None
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

    jwks: str | None = None
    """Client's JSON Web Key Set [RFC7517] document value, which contains the
    client's public keys.

    The value of this field MUST be a JSON object containing a valid JWK
    Set.  These keys can be used by higher-level protocols that use
    signing or encryption.  This parameter is intended to be used by
    clients that cannot use the "jwks_uri" parameter, such as native
    clients that cannot host public URLs.  The "jwks_uri" and "jwks"
    parameters MUST NOT both be present in the same request or response.
    """

    sector_identifier_uri: str | None = None
    """URL using the https scheme to be used in calculating Pseudonymous Identifiers by the OP.
    The URL references a file with a single JSON array of redirect_uri values.
    Please see Section 5. Providers that use pairwise sub (subject) values SHOULD
    utilize the sector_identifier_uri value provided in the Subject Identifier
    calculation for pairwise identifiers."""

    subject_type: str | None = None
    """subject_type requested for responses to this Client.
    The subject_types_supported discovery parameter contains a
    list of the supported subject_type values for the OP.
    Valid types include pairwise and public."""

    software_id: str | None = None
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

    software_version: str | None = None
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

    post_logout_redirect_uris: list[str] = []
    """Array of URLs supplied by the RP to which it MAY request that the
    End-User's User Agent be redirected using the
    post_logout_redirect_uri parameter after a logout has been
    performed.
    These URLs SHOULD use the https scheme and MAY contain
    port, path, and query parameter components; however, they MAY use
    the http scheme, provided that the Client Type is confidential, as
    defined in Section 2.1 of OAuth 2.0 [RFC6749], and provided the OP
    allows the use of http RP URIs.
    """

    application_type: str = "web"
    """Kind of the application.
    The default, if omitted, is web. The defined values are native or web.
    Web Clients using the OAuth Implicit Grant Type MUST only register URLs
    using the https scheme as redirect_uris; they MUST NOT use localhost as
    the hostname. Native Clients MUST only register redirect_uris using custom
    URI schemes or loopback URLs using the http scheme; loopback URLs use
    localhost or the IP loopback literals 127.0.0.1 or [::1] as the hostname.
    Authorization Servers MAY place additional constraints on Native Clients.
    Authorization Servers MAY reject Redirection URI values using the http scheme,
    other than the loopback case for Native Clients. The Authorization Server
    MUST verify that all the registered redirect_uris conform to these constraints.
    This prevents sharing a Client ID across different types of Clients."""

    id_token_signed_response_alg: str = "RS256"
    """JWS alg algorithm [JWA] REQUIRED for signing the ID Token issued to this Client.
    The value none MUST NOT be used as the ID Token alg value unless the Client uses
    only Response Types that return no ID Token from the Authorization Endpoint
    (such as when only using the Authorization Code Flow). The default, if omitted, is RS256.
    The public key for validating the signature is provided by retrieving the JWK Set referenced
    by the jwks_uri element from OpenID Connect Discovery 1.0 [OpenID.Discovery]."""

    id_token_encrypted_response_alg: str | None = None
    """JWE alg algorithm [JWA] REQUIRED for encrypting the ID Token issued to this Client.
    If this is requested, the response will be signed then encrypted,
    with the result being a Nested JWT, as defined in [JWT]. The default, if omitted,
    is that no encryption is performed."""

    id_token_encrypted_response_enc: str | None = None
    """JWE enc algorithm [JWA] REQUIRED for encrypting the ID Token issued to this Client.
    If id_token_encrypted_response_alg is specified, the default id_token_encrypted_response_enc
    value is A128CBC-HS256. When id_token_encrypted_response_enc is included,
    id_token_encrypted_response_alg MUST also be provided."""

    userinfo_signed_response_alg: str | None = None
    """JWS alg algorithm [JWA] REQUIRED for signing UserInfo Responses.
    If this is specified, the response will be JWT [JWT] serialized, and signed using JWS.
    The default, if omitted, is for the UserInfo Response to return the
    Claims as a UTF-8 [RFC3629] encoded JSON object using the application/json content-type."""

    userinfo_encrypted_response_alg: str | None = None
    """JWE [JWE] alg algorithm [JWA] REQUIRED for encrypting UserInfo Responses. If both
    signing and encryption are requested, the response will be signed then encrypted,
    with the result being a Nested JWT, as defined in [JWT]. The default, if omitted,
    is that no encryption is performed."""

    userinfo_encrypted_response_enc: str | None = None
    """JWE enc algorithm [JWA] REQUIRED for encrypting UserInfo Responses.
    If userinfo_encrypted_response_alg is specified, the default userinfo_encrypted_response_enc
    value is A128CBC-HS256. When userinfo_encrypted_response_enc is included,
    userinfo_encrypted_response_alg MUST also be provided."""

    default_max_age: int | None = None
    """Default Maximum Authentication Age.
    Specifies that the End-User MUST be actively authenticated if the End-User was authenticated
    longer ago than the specified number of seconds. The max_age request parameter overrides
    this default value. If omitted, no default Maximum Authentication Age is specified."""

    require_auth_time: bool = False
    """Boolean value specifying whether the auth_time Claim in the ID Token is REQUIRED.
    It is REQUIRED when the value is true. (If this is false, the auth_time Claim can still
    be dynamically requested as an individual Claim for the ID Token using the claims request
    parameter described in Section 5.5.1 of OpenID Connect Core 1.0 [OpenID.Core].)
    If omitted, the default value is false."""

    default_acr_values: list[str] = []
    """Default requested Authentication Context Class Reference values.
    Array of strings that specifies the default acr values that the OP is being requested
    to use for processing requests from this Client, with the values appearing in order of
    preference. The Authentication Context Class satisfied by the authentication performed
    is returned as the acr Claim Value in the issued ID Token. The acr Claim is requested
    as a Voluntary Claim by this parameter. The acr_values_supported discovery element
    contains a list of the supported acr values supported by the OP. Values specified in
    the acr_values request parameter or an individual acr Claim request override these
    default values."""

    initiate_login_uri: str | None = None
    """URI using the https scheme that a third party can use to initiate a login by the RP,
    as specified in Section 4 of OpenID Connect Core 1.0 [OpenID.Core]. The URI MUST accept
    requests via both GET and POST. The Client MUST understand the login_hint and iss parameters
    and SHOULD support the target_link_uri parameter."""

    request_object_signing_alg: str | None = None
    """JWS [JWS] alg algorithm [JWA] that MUST be used for signing Request Objects sent to the OP.
    All Request Objects from this Client MUST be rejected, if not signed with this algorithm.
    Request Objects are described in Section 6.1 of OpenID Connect Core 1.0 [OpenID.Core].
    This algorithm MUST be used both when the Request Object is passed by value (using the request parameter)
    and when it is passed by reference (using the request_uri parameter). Servers SHOULD support RS256.
    The value none MAY be used. The default, if omitted, is that any algorithm supported by the
    OP and the RP MAY be used."""

    request_object_encryption_alg: str | None = None
    """JWE [JWE] alg algorithm [JWA] the RP is declaring that it may use for encrypting Request Objects sent to the OP.
    This parameter SHOULD be included when symmetric encryption will be used, since this signals to the OP
    that a client_secret value needs to be returned from which the symmetric key will be derived,
    that might not otherwise be returned. The RP MAY still use other supported encryption algorithms
    or send unencrypted Request Objects, even when this parameter is present. If both signing and
    encryption are requested, the Request Object will be signed then encrypted, with the result
    being a Nested JWT, as defined in [JWT]. The default, if omitted, is that the RP is not declaring
    whether it might encrypt any Request Objects."""

    request_object_encryption_enc: str | None = None
    """JWE enc algorithm [JWA] the RP is declaring that it may use for encrypting Request Objects sent to the OP.
    If request_object_encryption_alg is specified, the default request_object_encryption_enc value is A128CBC-HS256.
    When request_object_encryption_enc is included, request_object_encryption_alg MUST also be provided."""

    request_uris: list[str] = []
    """Array of request_uri values that are pre-registered by the RP for use at the OP.
    These URLs MUST use the https scheme unless the target Request Object is signed in a way
    that is verifiable by the OP. Servers MAY cache the contents of the files referenced by these
    URIs and not retrieve them at the time they are used in a request.
    OPs can require that request_uri values used be pre-registered with the
    require_request_uri_registration discovery parameter.
    If the contents of the request file could ever change, these URI values SHOULD include
    the base64url-encoded SHA-256 hash value of the file contents referenced by the URI as
    the value of the URI fragment. If the fragment value used for a URI changes,
    that signals the server that its cached value for that URI with the old fragment
    value is no longer valid."""


class AuthorizationCode(Model):
    """OpenID Connect temporary authorization code definition."""

    identifier_attribute: ClassVar[str] = "authorization_code_id"

    authorization_code_id: str
    code: str
    client: "Client"
    subject: User
    redirect_uri: str | None
    response_type: str | None
    scope: list[str]
    nonce: str | None
    issue_date: datetime.datetime
    lifetime: int
    challenge: str | None
    challenge_method: str | None
    revokation_date: datetime.datetime


class Token(Model):
    """OpenID Connect token definition."""

    identifier_attribute: ClassVar[str] = "token_id"

    token_id: str
    access_token: str
    client: "Client"
    subject: User | None
    type: str
    refresh_token: str
    scope: list[str]
    issue_date: datetime.datetime
    lifetime: int
    revokation_date: datetime.datetime
    # keep 'List' instead of 'list' do not break py310 with the memory backend
    audience: List["Client"]  # noqa: UP006


class Consent(Model):
    """Long-term user consent to an application."""

    identifier_attribute: ClassVar[str] = "consent_id"

    consent_id: str
    subject: User
    client: "Client"
    scope: list[str]
    issue_date: datetime.datetime
    revokation_date: datetime.datetime

    def revoke(self):
        raise NotImplementedError()

    def restore(self):
        raise NotImplementedError()
