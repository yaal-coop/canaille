import datetime
from typing import List
from typing import Optional


class User:
    """
    User model, based on the `SCIM User schema
    <https://datatracker.ietf.org/doc/html/rfc7643#section-4.1>`_,
    `Entreprise User Schema Extension
    <https://datatracker.ietf.org/doc/html/rfc7643#section-4.3>`_
    and `SCIM Password Management Extension
    <https://datatracker.ietf.org/doc/html/draft-hunt-scim-password-mgmt-00.html>`_
    draft.
    Attribute description is based on SCIM and put there for
    information purpose. The description may not fit the current
    implementation in Canaille.
    """

    id: str
    """A unique identifier for a SCIM resource as defined by the service
    provider.

    Each representation of the resource MUST include a non-empty "id"
    value.  This identifier MUST be unique across the SCIM service
    provider's entire set of resources.  It MUST be a stable, non-
    reassignable identifier that does not change when the same resource
    is returned in subsequent requests.  The value of the "id" attribute
    is always issued by the service provider and MUST NOT be specified
    by the client.  The string "bulkId" is a reserved keyword and MUST
    NOT be used within any unique identifier value.  The attribute
    characteristics are "caseExact" as "true", a mutability of
    "readOnly", and a "returned" characteristic of "always".  See
    Section 9 for additional considerations regarding privacy.
    """

    user_name: Optional[str]
    """A service provider's unique identifier for the user, typically used by
    the user to directly authenticate to the service provider.

    Often displayed to the user as their unique identifier within the
    system (as opposed to "id" or "externalId", which are generally
    opaque and not user-friendly identifiers).  Each User MUST include a
    non-empty userName value.  This identifier MUST be unique across the
    service provider's entire set of Users.  This attribute is REQUIRED
    and is case insensitive.
    """

    password: Optional[str]
    """
    This attribute is intended to be used as a means to set, replace,
    or compare (i.e., filter for equality) a password.  The cleartext
    value or the hashed value of a password SHALL NOT be returnable by
    a service provider.  If a service provider holds the value
    locally, the value SHOULD be hashed.  When a password is set or
    changed by the client, the cleartext password SHOULD be processed
    by the service provider as follows:

    *  Prepare the cleartext value for international language
       comparison.  See Section 7.8 of [RFC7644].

    *  Validate the value against server password policy.  Note: The
       definition and enforcement of password policy are beyond the
       scope of this document.

    *  Ensure that the value is encrypted (e.g., hashed).  See
       Section 9.2 for acceptable hashing and encryption handling when
       storing or persisting for provisioning workflow reasons.

    A service provider that immediately passes the cleartext value on
    to another system or programming interface MUST pass the value
    directly over a secured connection (e.g., Transport Layer Security
    (TLS)).  If the value needs to be temporarily persisted for a
    period of time (e.g., because of a workflow) before provisioning,
    then the value MUST be protected by some method, such as
    encryption.

    Testing for an equality match MAY be supported if there is an
    existing stored hashed value.  When testing for equality, the
    service provider:

    *  Prepares the filter value for international language
       comparison.  See Section 7.8 of [RFC7644].

    *  Generates the salted hash of the filter value and tests for a
       match with the locally held value.

    The mutability of the password attribute is "writeOnly",
    indicating that the value MUST NOT be returned by a service
    provider in any form (the attribute characteristic "returned" is
    "never").
    """

    preferred_language: Optional[str]
    """Indicates the user's preferred written or spoken languages and is
    generally used for selecting a localized user interface.

    The value indicates the set of natural languages that are preferred.
    The format of the value is the same as the HTTP Accept-Language
    header field (not including "Accept-Language:") and is specified in
    Section 5.3.5 of [RFC7231].  The intent of this value is to enable
    cloud applications to perform matching of language tags [RFC4647] to
    the user's language preferences, regardless of what may be indicated
    by a user agent (which might be shared), or in an interaction that
    does not involve a user (such as in a delegated OAuth 2.0 [RFC6749]
    style interaction) where normal HTTP Accept-Language header
    negotiation cannot take place.
    """

    family_name: Optional[str]
    """The family name of the User, or last name in most Western languages
    (e.g., "Jensen" given the full name "Ms. Barbara Jane Jensen, III")."""

    given_name: Optional[str]
    """The given name of the User, or first name in most Western languages
    (e.g., "Barbara" given the full name "Ms. Barbara Jane Jensen, III")."""

    formatted_name: Optional[str]
    """The full name, including all middle names, titles, and suffixes as
    appropriate, formatted for display (e.g., "Ms. Barbara Jane Jensen,
    III")."""

    display_name: Optional[str]
    """The name of the user, suitable for display to end-users.

    Each user returned MAY include a non-empty displayName value.  The
    name SHOULD be the full name of the User being described, if known
    (e.g., "Babs Jensen" or "Ms. Barbara J Jensen, III") but MAY be a
    username or handle, if that is all that is available (e.g.,
    "bjensen").  The value provided SHOULD be the primary textual label
    by which this User is normally displayed by the service provider
    when presenting it to end-users.
    """

    emails: List[str]
    """Email addresses for the User.

    The value SHOULD be specified according to [RFC5321].  Service
    providers SHOULD canonicalize the value according to [RFC5321],
    e.g., "bjensen@example.com" instead of "bjensen@EXAMPLE.COM".  The
    "display" sub-attribute MAY be used to return the canonicalized
    representation of the email value. The "type" sub-attribute is used
    to provide a classification meaningful to the (human) user.  The
    user interface should encourage the use of basic values of "work",
    "home", and "other" and MAY allow additional type values to be used
    at the discretion of SCIM clients.
    """

    phone_numbers: List[str]
    """Phone numbers for the user.

    The value SHOULD be specified according to the format defined in
    [RFC3966], e.g., 'tel:+1-201-555-0123'.  Service providers SHOULD
    canonicalize the value according to [RFC3966] format, when
    appropriate.  The "display" sub-attribute MAY be used to return the
    canonicalized representation of the phone number value.  The sub-
    attribute "type" often has typical values of "work", "home",
    "mobile", "fax", "pager", and "other" and MAY allow more types to be
    defined by the SCIM clients.
    """

    formatted_address: Optional[str]
    """The full mailing address, formatted for display or use with a mailing
    label.

    This attribute MAY contain newlines.
    """

    street: Optional[str]
    """The full street address component, which may include house number,
    street name, P.O.

    box, and multi-line extended street address information.  This
    attribute MAY contain newlines.
    """

    postal_code: Optional[str]
    """The zip code or postal code component."""

    locality: Optional[str]
    """The city or locality component."""

    region: Optional[str]
    """The state or region component."""

    photo: Optional[str]
    """A URI that is a uniform resource locator (as defined in Section 1.1.3 of
    [RFC3986]) that points to a resource location representing the user's
    image.

    The resource MUST be a file (e.g.,
    a GIF, JPEG, or PNG image file) rather than a web page containing
    an image.  Service providers MAY return the same image in
    different sizes, although it is recognized that no standard for
    describing images of various sizes currently exists.  Note that
    this attribute SHOULD NOT be used to send down arbitrary photos
    taken by this user; instead, profile photos of the user that are
    suitable for display when describing the user should be sent.
    Instead of the standard canonical values for type, this attribute
    defines the following canonical values to represent popular photo
    sizes: "photo" and "thumbnail".
    """

    profile_url: Optional[str]
    """A URI that is a uniform resource locator (as defined in Section 1.1.3 of
    [RFC3986]) and that points to a location representing the user's online
    profile (e.g., a web page).

    URIs are canonicalized per Section 6.2 of [RFC3986].
    """

    title: Optional[str]
    """The user's title, such as "Vice President"."""

    organization: Optional[str]
    """Identifies the name of an organization."""

    employee_number: Optional[str]
    """A string identifier, typically numeric or alphanumeric, assigned to a
    person, typically based on order of hire or association with an
    organization."""

    department: Optional[str]
    """Identifies the name of a department."""

    last_modified: Optional[datetime.datetime]
    """The most recent DateTime that the details of this resource were updated
    at the service provider.

    If this resource has never been modified since its initial creation,
    the value MUST be the same as the value of "created".
    """

    groups: List["Group"]
    """A list of groups to which the user belongs, either through direct
    membership, through nested groups, or dynamically calculated.

    The values are meant to enable expression of common group-based or
    role-based access control models, although no explicit authorization
    model is defined.  It is intended that the semantics of group
    membership and any behavior or authorization granted as a result of
    membership are defined by the service provider.  The canonical types
    "direct" and "indirect" are defined to describe how the group
    membership was derived.  Direct group membership indicates that the
    user is directly associated with the group and SHOULD indicate that
    clients may modify membership through the "Group" resource. Indirect
    membership indicates that user membership is transitive or dynamic
    and implies that clients cannot modify indirect group membership
    through the "Group" resource but MAY modify direct group membership
    through the "Group" resource, which may influence indirect
    memberships.  If the SCIM service provider exposes a "Group"
    resource, the "value" sub-attribute MUST be the "id", and the "$ref"
    sub-attribute must be the URI of the corresponding "Group" resources
    to which the user belongs.  Since this attribute has a mutability of
    "readOnly", group membership changes MUST be applied via the "Group"
    Resource (Section 4.2).  This attribute has a mutability of
    "readOnly".
    """

    lock_date: Optional[datetime.datetime]
    """A DateTime indicating when the resource was locked."""

    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs) -> Optional["User"]:
        raise NotImplementedError()

    def has_password(self) -> bool:
        """Checks wether a password has been set for the user."""
        raise NotImplementedError()

    def check_password(self, password: str) -> bool:
        """Checks if the password matches the user password in the database."""
        raise NotImplementedError()

    def set_password(self, password: str):
        """Sets a password for the user."""
        raise NotImplementedError()

    def can_read(self, field: str):
        return field in self.read | self.write

    @property
    def preferred_email(self):
        return self.emails[0] if self.emails else None

    def __getattr__(self, name):
        if name.startswith("can_") and name != "can_read":
            permission = name[4:]
            return permission in self.permissions

        return super().__getattr__(name)

    @property
    def locked(self) -> bool:
        """Wether the user account has been locked or has expired."""
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )


class Group:
    """
    User model, based on the `SCIM Group schema
    <https://datatracker.ietf.org/doc/html/rfc7643#section-4.2>`_.
    """

    id: str
    """A unique identifier for a SCIM resource as defined by the service
    provider.

    Each representation of the resource MUST include a non-empty "id"
    value.  This identifier MUST be unique across the SCIM service
    provider's entire set of resources.  It MUST be a stable, non-
    reassignable identifier that does not change when the same resource
    is returned in subsequent requests.  The value of the "id" attribute
    is always issued by the service provider and MUST NOT be specified
    by the client.  The string "bulkId" is a reserved keyword and MUST
    NOT be used within any unique identifier value.  The attribute
    characteristics are "caseExact" as "true", a mutability of
    "readOnly", and a "returned" characteristic of "always".  See
    Section 9 for additional considerations regarding privacy.
    """

    display_name: str
    """A human-readable name for the Group.

    REQUIRED.
    """

    members: List["User"]
    """A list of members of the Group.

    While values MAY be added or removed, sub-attributes of members are
    "immutable".  The "value" sub-attribute contains the value of an
    "id" attribute of a SCIM resource, and the "$ref" sub-attribute must
    be the URI of a SCIM resource such as a "User", or a "Group".  The
    intention of the "Group" type is to allow the service provider to
    support nested groups.  Service providers MAY require clients to
    provide a non-empty value by setting the "required" attribute
    characteristic of a sub-attribute of the "members" attribute in the
    "Group" resource schema.
    """

    description: Optional[str]
