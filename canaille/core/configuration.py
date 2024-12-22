from enum import Enum

from pydantic import BaseModel
from pydantic import ValidationInfo
from pydantic import field_validator


class SMTPSettings(BaseModel):
    """The SMTP configuration. Belong in the ``CANAILLE.SMTP`` namespace. If
    unset, mail related features will be disabled, such as mail verification or
    password recovery emails.

    By default, Canaille will try to send mails from localhost without
    authentication.
    """

    HOST: str | None = "localhost"
    """The SMTP host."""

    PORT: int | None = 25
    """The SMTP port."""

    TLS: bool | None = False
    """Whether to use TLS to connect to the SMTP server."""

    SSL: bool | None = False
    """Whether to use SSL to connect to the SMTP server."""

    LOGIN: str | None = None
    """The SMTP login."""

    PASSWORD: str | None = None
    """The SMTP password."""

    FROM_ADDR: str | None = None
    """The sender for Canaille mails.

    Some mail provider might require a valid sender address.
    """


class SMPPSettings(BaseModel):
    """The SMPP configuration. Belong in the ``CANAILLE.SMPP`` namespace. If
    not set, sms related features such as sms one-time passwords will be disabled.
    """

    HOST: str | None = "localhost"
    """The SMPP host."""

    PORT: int | None = 2775
    """The SMPP port. Use 8775 for SMPP over TLS (recommended)."""

    LOGIN: str | None = None
    """The SMPP login."""

    PASSWORD: str | None = None
    """The SMPP password."""


class Permission(str, Enum):
    """The permissions that can be assigned to users.

    The permissions are intended to be used in :attr:`ACLSettings <canaille.core.configuration.ACLSettings.PERMISSIONS>`.
    """

    EDIT_SELF = "edit_self"
    """Allows users to edit their own profile."""

    USE_OIDC = "use_oidc"
    """Allows OpenID Connect authentication."""

    MANAGE_OIDC = "manage_oidc"
    """Allows OpenID Connect client managements."""

    MANAGE_USERS = "manage_users"
    """Allows other users management."""

    MANAGE_GROUPS = "manage_groups"
    """Allows group edition and creation."""

    DELETE_ACCOUNT = "delete_account"
    """Allows users to delete their account.

    If used with :attr:`~canaille.core.configuration.Permission.MANAGE_USERS`, users can delete any account.
    """

    IMPERSONATE_USERS = "impersonate_users"
    """Allows users to take the identity of another user."""


class ACLSettings(BaseModel):
    """Access Control List settings. Belong in the ``CANAILLE.ACL`` namespace.

    You can define access controls that define what users can do on canaille.
    An access control consists in a :attr:`FILTER` to match users, a list of :attr:`PERMISSIONS`
    matched users will be able to perform, and fields users will be able
    to :attr:`READ` and :attr:`WRITE`. Users matching several filters will cumulate permissions.
    """

    PERMISSIONS: list[Permission] = [Permission.EDIT_SELF, Permission.USE_OIDC]
    """A list of :class:`Permission` users in the access control will be able
    to manage.

    For example:

    ..code-block:: toml

        PERMISSIONS = ["manage_users", "manage_groups", "manage_oidc", "delete_account", "impersonate_users"]
    """

    READ: list[str] = [
        "user_name",
        "groups",
        "lock_date",
    ]
    """A list of :class:`~canaille.core.models.User` attributes that users in
    the ACL will be able to read."""

    WRITE: list[str] = [
        "photo",
        "given_name",
        "family_name",
        "display_name",
        "password",
        "phone_numbers",
        "emails",
        "profile_url",
        "formatted_address",
        "street",
        "postal_code",
        "locality",
        "region",
        "preferred_language",
        "employee_number",
        "department",
        "title",
        "organization",
    ]
    """A list of :class:`~canaille.core.models.User` attributes that users in
    the ACL will be able to edit."""

    @field_validator("READ")
    def validate_read_values(
        cls,
        read: list[str],
        info: ValidationInfo,
    ) -> list[str]:
        from canaille.core.models import User

        assert all(field in User.attributes for field in read)
        return read

    @field_validator("WRITE")
    def validate_write_values(
        cls,
        write: list[str],
        info: ValidationInfo,
    ) -> list[str]:
        from canaille.core.models import User

        assert all(field in User.attributes for field in write)
        return write

    FILTER: dict[str, str] | list[dict[str, str]] | None = None
    """:attr:`FILTER` can be:

    - :py:data:`None`, in which case all the users will match this access control
    - a mapping where keys are user attributes name and the values those user
      attribute values. All the values must be matched for the user to be part
      of the access control.
    - a list of those mappings. If a user values match at least one mapping,
      then the user will be part of the access control

    Here are some examples::

        FILTER = {user_name = 'admin'}
        FILTER = [
            {groups = 'admins},
            {groups = 'moderators'},
        ]
    """


class CoreSettings(BaseModel):
    """The settings from the ``CANAILLE`` namespace.

    Those are all the configuration parameters that controls the
    behavior of Canaille.
    """

    NAME: str = "Canaille"
    """Your organization name.

    Used for display purpose.
    """

    LOGO: str | None = None
    """The logo of your organization, this is useful to make your organization
    recognizable on login screens."""

    FAVICON: str | None = None
    """You favicon.

    If unset and :attr:`LOGO` is set, then the logo will be used.
    """

    THEME: str = "default"
    """The name of a theme in the 'theme' directory, or a path to a theme.

    Defaults to ``default``. Theming is done with `flask-themer <https://github.com/tktech/flask-themer>`_.
    """

    LANGUAGE: str | None = None
    """If a language code is set, it will be used for every user.

    If unset, the language is guessed according to the users browser.
    """

    TIMEZONE: str | None = None
    """The timezone in which datetimes will be displayed to the users (e.g.
    ``CEST``).

    If unset, the server timezone will be used.
    """

    SENTRY_DSN: str | None = None
    """A `Sentry <https://sentry.io>`_ DSN to collect the exceptions.

    This is useful for tracking errors in test and production environments.
    """

    JAVASCRIPT: bool = True
    """Enables Javascript to smooth the user experience."""

    HTMX: bool = True
    """Accelerates webpages loading with asynchronous requests."""

    EMAIL_CONFIRMATION: bool = True
    """If :py:data:`True`, users will need to click on a confirmation link sent
    by email when they want to add a new email.

    By default, this is true
    if ``SMTP`` is configured, else this is false. If explicitly set to true
    and ``SMTP`` is disabled, the email field will be read-only.
    """

    ENABLE_REGISTRATION: bool = False
    """If :py:data:`True`, then users can freely create an account at this
    instance.

    If email verification is available, users must confirm their email
    before the account is created.
    """

    HIDE_INVALID_LOGINS: bool = True
    """If :py:data:`True`, when users try to sign in with an invalid login, a
    message is shown indicating that the password is wrong, but does not give a
    clue whether the login exists or not.

    If :py:data:`False`,
    when a user tries to sign in with an invalid login, a message is shown
    indicating that the login does not exist.
    """

    ENABLE_PASSWORD_RECOVERY: bool = True
    """If :py:data:`False`, then users cannot ask for a password recovery link
    by email."""

    ENABLE_INTRUDER_LOCKOUT: bool = False
    """If :py:data:`True`, then users will have to wait for an increasingly
    long time between each failed login attempt."""

    OTP_METHOD: str = None
    """If OTP_METHOD is defined, then users will need to authenticate themselves
    using a one-time password (OTP) via an authenticator app.
    If set to ``TOTP``, the application will use time one-time passwords,
    If set to ``HOTP``, the application will use HMAC-based one-time passwords."""

    EMAIL_OTP: bool = False
    """If :py:data:`True`, then users will need to authenticate themselves
    via a one-time password sent to their primary email address."""

    SMS_OTP: bool = False
    """If :py:data:`True`, then users will need to authenticate themselves
    via a one-time password sent to their primary phone number."""

    INVITATION_EXPIRATION: int = 172800
    """The validity duration of registration invitations, in seconds.

    Defaults to 2 days.
    """

    LOGGING: str | dict | None = None
    """Configures the logging output using the python logging configuration format:

    - If :data:`None`, everything is logged in the standard error output.
      The log level is :data:`~logging.DEBUG` if the :attr:`~canaille.app.configuration.RootSettings.DEBUG`
      setting is :py:data:`True`, else this is :py:data:`~logging.INFO`.
    - If this is a :class:`dict`, it is passed to :func:`logging.config.dictConfig`:
    - If this is a :class:`str`, it is expected to be a file path that will be passed
      to :func:`logging.config.fileConfig`.

    For example:

    ..code-block:: toml

        [CANAILLE.LOGGING]
        version = 1
        formatters.default.format = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        root = {level = "INFO", handlers = ["canaille"]}

        [CANAILLE.LOGGING.handlers.canaille]
        class = "logging.handlers.WatchedFileHandler"
        filename = "/var/log/canaille.log"
        formatter = "default"
    """

    SMTP: SMTPSettings | None = None
    """The settings related to SMTP and mail configuration.

    If unset, mail-related features like password recovery won't be
    enabled.
    """

    SMPP: SMPPSettings | None = None
    """The settings related to SMPP configuration.

    If unset, sms-related features like sms one-time passwords won't be
    enabled.
    """

    ACL: dict[str, ACLSettings] | None = {"DEFAULT": ACLSettings()}
    """Mapping of permission groups. See :class:`ACLSettings` for more details.

    The ACL name can be freely chosen. For example:

    ..code-block:: toml

        [CANAILLE.ACL.DEFAULT]
        PERMISSIONS = ["edit_self", "use_oidc"]
        READ = ["user_name", "groups"]
        WRITE = ["given_name", "family_name"]

        [CANAILLE.ACL.ADMIN]
        WRITE = ["user_name", "groups"]
    """

    MIN_PASSWORD_LENGTH: int = 8
    """User password minimum length.

    If 0 or :data:`None`, password won't have a minimum length.
    """

    MAX_PASSWORD_LENGTH: int = 1000
    """User password maximum length.

    There is a technical of 4096 characters with the SQL backend.
    If the value is 0, :data:`None`, or greater than 4096,
    then 4096 will be retained.
    """

    ADMIN_EMAIL: str | None = None
    """Administration email contact.

    In certain special cases (example : questioning about password
    corruption), it is necessary to provide an administration contact
    email.
    """

    ENABLE_PASSWORD_COMPROMISSION_CHECK: bool = False
    """If :py:data:`True`, Canaille will check if passwords appears in
    compromission databases such as `HIBP <https://haveibeenpwned.com>`_
    when users choose a new one."""

    PASSWORD_COMPROMISSION_CHECK_API_URL: str = "https://api.pwnedpasswords.com/range/"
    """Have i been pwned api url for compromission checks."""

    PASSWORD_LIFETIME: str | None = None
    """Password validity duration.

    If set, user passwords expire after this delay.
    Users are forced to change their password when the lifetime of the password is over.
    The duration value is expressed in `ISO8601 format <https://en.wikipedia.org/wiki/ISO_8601#Durations>`_.
    For example, delay of 60 days is written "P60D".
    """
