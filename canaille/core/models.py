import datetime
import secrets
from typing import Annotated
from typing import ClassVar

from flask import current_app
from pydantic import TypeAdapter

from canaille.backends.models import Model
from canaille.core.configuration import Permission
from canaille.core.mails import send_one_time_password_mail
from canaille.core.sms import send_one_time_password_sms

HOTP_LOOK_AHEAD_WINDOW = 10
OTP_DIGITS = 6
OTP_VALIDITY = 600
SEND_NEW_OTP_DELAY = 10

PASSWORD_MIN_DELAY = 2
PASSWORD_MAX_DELAY = 600
PASSWORD_FAILURE_COUNT_INTERVAL = 600


class User(Model):
    """User model, based on the `SCIM User schema
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

    identifier_attribute: ClassVar[str] = "user_name"

    user_name: str
    """A service provider's unique identifier for the user, typically used by
    the user to directly authenticate to the service provider.

    Often displayed to the user as their unique identifier within the
    system (as opposed to "id" or "externalId", which are generally
    opaque and not user-friendly identifiers).  Each User MUST include a
    non-empty userName value.  This identifier MUST be unique across the
    service provider's entire set of Users.  This attribute is REQUIRED
    and is case insensitive.
    """

    password_failure_timestamps: list[datetime.datetime] = []
    """This attribute stores the timestamps of the user's failed
    authentications.

    It's currently used by the intruder lockout delay system.
    """

    password: str | None = None
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

    password_last_update: datetime.datetime | None = None
    """Specifies the last time the user password was changed.
    By default, the date of creation of the password is retained.
    """

    preferred_language: str | None = None
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

    family_name: str | None = None
    """The family name of the User, or last name in most Western languages
    (e.g., "Jensen" given the full name "Ms. Barbara Jane Jensen, III")."""

    given_name: str | None = None
    """The given name of the User, or first name in most Western languages
    (e.g., "Barbara" given the full name "Ms. Barbara Jane Jensen, III")."""

    formatted_name: str | None = None
    """The full name, including all middle names, titles, and suffixes as
    appropriate, formatted for display (e.g., "Ms. Barbara Jane Jensen,
    III")."""

    display_name: str | None = None
    """The name of the user, suitable for display to end-users.

    Each user returned MAY include a non-empty displayName value.  The
    name SHOULD be the full name of the User being described, if known
    (e.g., "Babs Jensen" or "Ms. Barbara J Jensen, III") but MAY be a
    username or handle, if that is all that is available (e.g.,
    "bjensen").  The value provided SHOULD be the primary textual label
    by which this User is normally displayed by the service provider
    when presenting it to end-users.
    """

    emails: list[str] = []
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

    phone_numbers: list[str] = []
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

    formatted_address: str | None = None
    """The full mailing address, formatted for display or use with a mailing
    label.

    This attribute MAY contain newlines.
    """

    street: str | None = None
    """The full street address component, which may include house number,
    street name, P.O.

    box, and multi-line extended street address information.  This
    attribute MAY contain newlines.
    """

    postal_code: str | None = None
    """The zip code or postal code component."""

    locality: str | None = None
    """The city or locality component."""

    region: str | None = None
    """The state or region component."""

    photo: str | None = None
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

    profile_url: str | None = None
    """A URI that is a uniform resource locator (as defined in Section 1.1.3 of
    [RFC3986]) and that points to a location representing the user's online
    profile (e.g., a web page).

    URIs are canonicalized per Section 6.2 of [RFC3986].
    """

    title: str | None = None
    """The user's title, such as "Vice President"."""

    organization: str | None = None
    """Identifies the name of an organization."""

    employee_number: str | None = None
    """A string identifier, typically numeric or alphanumeric, assigned to a
    person, typically based on order of hire or association with an
    organization."""

    department: str | None = None
    """Identifies the name of a department."""

    groups: list[Annotated["Group", {"backref": "members"}]] = []
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

    lock_date: datetime.datetime | None = None
    """A DateTime indicating when the resource was locked."""

    last_otp_login: datetime.datetime | None = None
    """A DateTime indicating when the user last logged in with a one-time password.
    This attribute is currently used to check whether the user has activated one-time password authentication or not."""

    secret_token: str | None = None
    """Unique token generated for each user, used for
    multi-factor authentication."""

    hotp_counter: int | None = None
    """HMAC-based One Time Password counter, used for
    multi-factor authentication."""

    one_time_password: str | None = None
    """One time password used for email or sms multi-factor authentication."""

    one_time_password_emission_date: datetime.datetime | None = None
    """A DateTime indicating when the user last emitted an email or sms one-time password."""

    _readable_fields = None
    _writable_fields = None
    _permissions = None

    def has_password(self) -> bool:
        """Check whether a password has been set for the user."""
        return self.password is not None

    def can_read(self, field: str):
        return field in self.readable_fields | self.writable_fields

    @property
    def preferred_email(self):
        return self.emails[0] if self.emails else None

    def __getattribute__(self, name):
        prefix = "can_"

        try:
            return super().__getattribute__(name)

        except AttributeError:
            if name.startswith(prefix) and name != "can_read":
                return self.can(name[len(prefix) :])
            raise

    def can(self, *permissions: Permission):
        """Whether or not the user has the
        :class:`~canaille.core.configuration.Permission` according to the
        :class:`configuration <canaille.core.configuration.ACLSettings>`."""
        if self._permissions is None:
            self._permissions = set()
            acls = current_app.config["CANAILLE"]["ACL"].values()
            for details in acls:
                if self.match_filter(details["FILTER"]):
                    self._permissions |= set(details["PERMISSIONS"])

        return set(permissions).issubset(self._permissions)

    @property
    def locked(self) -> bool:
        """Whether the user account has been locked or has expired."""
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )

    def reload(self):
        self._readable = None
        self._writable = None
        self._permissions = None
        yield

    @property
    def readable_fields(self):
        """The fields the user can read according to the :class:`configuration
        <canaille.core.configuration.ACLSettings>` configuration.

        This does not include the :attr:`writable
        <canaille.core.models.User.writable_fields>` fields.
        """
        if self._readable_fields is None:
            self._readable_fields = set()
            acls = current_app.config["CANAILLE"]["ACL"].values()
            for details in acls:
                if self.match_filter(details["FILTER"]):
                    self._readable_fields |= set(details["READ"])

        return self._readable_fields

    @property
    def writable_fields(self):
        """The fields the user can write according to the :class:`configuration
        <canaille.core.configuration.ACLSettings>`."""
        if self._writable_fields is None:
            self._writable_fields = set()
            acls = current_app.config["CANAILLE"]["ACL"].values()
            for details in acls:
                if self.match_filter(details["FILTER"]):
                    self._writable_fields |= set(details["WRITE"])
        return self._writable_fields

    def initialize_otp(self):
        self.secret_token = secrets.token_hex(32)
        self.last_otp_login = None
        if current_app.features.otp_method == "HOTP":
            self.hotp_counter = 1

    def generate_otp(self, counter_delta=0):
        import otpauth

        method = current_app.features.otp_method
        if method == "TOTP":
            totp = otpauth.TOTP(bytes(self.secret_token, "utf-8"))
            return totp.string_code(totp.generate())
        elif method == "HOTP":
            hotp = otpauth.HOTP(bytes(self.secret_token, "utf-8"))
            return hotp.string_code(hotp.generate(self.hotp_counter + counter_delta))
        else:  # pragma: no cover
            raise RuntimeError("Invalid one-time password method")

    def generate_sms_or_mail_otp(self):
        otp = string_code(secrets.randbelow(10**OTP_DIGITS), OTP_DIGITS)
        self.one_time_password = otp
        self.one_time_password_emission_date = datetime.datetime.now(
            datetime.timezone.utc
        )
        return otp

    def generate_and_send_otp_mail(self):
        otp = self.generate_sms_or_mail_otp()
        if send_one_time_password_mail(self.preferred_email, otp):
            return otp
        return False

    def generate_and_send_otp_sms(self):
        otp = self.generate_sms_or_mail_otp()
        if send_one_time_password_sms(self.phone_numbers[0], otp):
            return otp
        return False

    def get_otp_authentication_setup_uri(self):
        import otpauth

        method = current_app.features.otp_method
        if method == "TOTP":
            return otpauth.TOTP(bytes(self.secret_token, "utf-8")).to_uri(
                label=self.user_name, issuer=current_app.config["CANAILLE"]["NAME"]
            )
        elif method == "HOTP":
            return otpauth.HOTP(bytes(self.secret_token, "utf-8")).to_uri(
                label=self.user_name,
                issuer=current_app.config["CANAILLE"]["NAME"],
                counter=self.hotp_counter,
            )
        else:  # pragma: no cover
            raise RuntimeError("Invalid one-time password method")

    def is_otp_valid(self, user_otp, method):
        if method == "TOTP":
            return self.is_totp_valid(user_otp)
        elif method == "HOTP":
            return self.is_hotp_valid(user_otp)
        elif method == "EMAIL_OTP" or method == "SMS_OTP":
            return self.is_email_or_sms_otp_valid(user_otp)
        else:  # pragma: no cover
            raise RuntimeError("Invalid one-time password method")

    def is_totp_valid(self, user_otp):
        import otpauth

        return otpauth.TOTP(bytes(self.secret_token, "utf-8")).verify(user_otp)

    def is_hotp_valid(self, user_otp):
        import otpauth

        counter = self.hotp_counter
        is_valid = False
        # if user token's counter is ahead of canaille's, try to catch up to it
        while counter - self.hotp_counter <= HOTP_LOOK_AHEAD_WINDOW:
            is_valid = otpauth.HOTP(bytes(self.secret_token, "utf-8")).verify(
                user_otp, counter
            )
            counter += 1
            if is_valid:
                self.hotp_counter = counter
                return True
        return False

    def is_email_or_sms_otp_valid(self, user_otp):
        return user_otp == self.one_time_password and self.is_otp_still_valid()

    def is_otp_still_valid(self):
        return datetime.datetime.now(
            datetime.timezone.utc
        ) - self.one_time_password_emission_date < datetime.timedelta(
            seconds=OTP_VALIDITY
        )

    def can_send_new_otp(self):
        return self.one_time_password_emission_date is None or (
            datetime.datetime.now(datetime.timezone.utc)
            - self.one_time_password_emission_date
            >= datetime.timedelta(seconds=SEND_NEW_OTP_DELAY)
        )

    def get_intruder_lockout_delay(self):
        if self.password_failure_timestamps:
            # discard old attempts
            self.password_failure_timestamps = [
                attempt
                for attempt in self.password_failure_timestamps
                if attempt
                > datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(seconds=PASSWORD_FAILURE_COUNT_INTERVAL)
            ]
        if not self.password_failure_timestamps:
            return 0
        failed_login_count = len(self.password_failure_timestamps)
        # delay is multiplied by 2 each failed attempt, starting at min delay, limited to max delay
        calculated_delay = min(
            PASSWORD_MIN_DELAY * 2 ** (failed_login_count - 1), PASSWORD_MAX_DELAY
        )
        time_since_last_failed_bind = (
            datetime.datetime.now(datetime.timezone.utc)
            - self.password_failure_timestamps[-1]
        ).total_seconds()
        return max(calculated_delay - time_since_last_failed_bind, 0)

    def has_expired_password(self):
        last_update = self.password_last_update or datetime.datetime.now(
            datetime.timezone.utc
        )
        if current_app.config["CANAILLE"]["PASSWORD_LIFETIME"] is None:
            password_expiration = None
        else:
            password_expiration = TypeAdapter(datetime.timedelta).validate_python(
                current_app.config["CANAILLE"]["PASSWORD_LIFETIME"]
            )

        return (
            password_expiration is not None
            and last_update + password_expiration
            < datetime.datetime.now(datetime.timezone.utc)
        )


class Group(Model):
    """User model, based on the `SCIM Group schema
    <https://datatracker.ietf.org/doc/html/rfc7643#section-4.2>`_.
    """

    identifier_attribute: ClassVar[str] = "display_name"

    display_name: str
    """A human-readable name for the Group.

    REQUIRED.
    """

    members: list[Annotated["User", {"backref": "groups"}]] = []
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

    description: str | None = None


def string_code(code: int, digit: int) -> str:
    """Add leading 0 if the code length does not match the defined length.

    For instance, parameter ``digit=6``, but ``code=123``, this method would
    return ``000123``::

        >>> otp.string_code(123)
        '000123'
    """
    return f"{code:0{digit}}"
