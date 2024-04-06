from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

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

    HOST: Optional[str] = "localhost"
    """The SMTP host."""

    PORT: Optional[int] = 25
    """The SMTP port."""

    TLS: Optional[bool] = False
    """Wether to use TLS to connect to the SMTP server."""

    SSL: Optional[bool] = False
    """Wether to use SSL to connect to the SMTP server."""

    LOGIN: Optional[str] = None
    """The SMTP login."""

    PASSWORD: Optional[str] = None
    """The SMTP password."""

    FROM_ADDR: Optional[str] = None
    """The sender for Canaille mails.

    Some mail provider might require a valid sender address.
    """


class Permission(str, Enum):
    """The permissions that can be assigned to users."""

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

    If used with :enum:member:`~canaille.core.configuration.Permission.MANAGE_USERS`, users can delete any account.
    """

    IMPERSONATE_USERS = "impersonate_users"
    """Allows users to take the identity of another user."""


class ACLSettings(BaseModel):
    """Access Control List settings. Belong in the ``CANAILLE.ACL`` namespace.

    You can define access controls that define what users can do on canaille
    An access control consists in a :attr:`FILTER` to match users, a list of :attr:`PERMISSIONS`
    matched users will be able to perform, and fields users will be able
    to :attr:`READ` and :attr:`WRITE`. Users matching several filters will cumulate permissions.
    """

    PERMISSIONS: List[Permission] = [Permission.EDIT_SELF, Permission.USE_OIDC]
    """A list of :class:`Permission` users in the access control will be able
    to manage. For example::

        PERMISSIONS = [
            "manage_users",
            "manage_groups",
            "manage_oidc",
            "delete_account",
            "impersonate_users",
        ]"""

    READ: List[str] = [
        "user_name",
        "groups",
        "lock_date",
    ]
    """A list of :class:`~canaille.core.models.User` attributes that users in
    the ACL will be able to read."""

    WRITE: List[str] = [
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
        read: List[str],
        info: ValidationInfo,
    ) -> List[str]:
        from canaille.core.models import User

        assert all(field in User.attributes for field in read)
        return read

    @field_validator("WRITE")
    def validate_write_values(
        cls,
        write: List[str],
        info: ValidationInfo,
    ) -> List[str]:
        from canaille.core.models import User

        assert all(field in User.attributes for field in write)
        return write

    FILTER: Optional[Union[Dict[str, str], List[Dict[str, str]]]] = None
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

    LOGO: Optional[str] = None
    """The logo of your organization, this is useful to make your organization
    recognizable on login screens."""

    FAVICON: Optional[str] = None
    """You favicon.

    If unset and :attr:`LOGO` is set, then the logo will be used.
    """

    THEME: str = "default"
    """The name of a theme in the 'theme' directory, or a path to a theme.

    Defaults to ``default``. Theming is done with `flask-themer <https://github.com/tktech/flask-themer>`_.
    """

    LANGUAGE: Optional[str] = None
    """If a language code is set, it will be used for every user.

    If unset, the language is guessed according to the users browser.
    """

    TIMEZONE: Optional[str] = None
    """The timezone in which datetimes will be displayed to the users (e.g.
    ``CEST``).

    If unset, the server timezone will be used.
    """

    SENTRY_DSN: Optional[str] = None
    """A `Sentry <https://sentry.io>`_ DSN to collect the exceptions.

    This is useful for tracking errors in test and production environments.
    """

    JAVASCRIPT: bool = True
    """Enables Javascript to smooth the user experience."""

    HTMX: bool = True
    """Accelerates webpages loading with asynchroneous requests."""

    EMAIL_CONFIRMATION: bool = True
    """If :py:data:`True`, users will need to click on a confirmation link sent
    by email when they want to add a new email.

    By default, this is true
    if ``SMTP`` is configured, else this is false. If explicitely set to true
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
    clue wether the login exists or not.

    If :py:data:`False`,
    when a user tries to sign in with an invalid login, a message is shown
    indicating that the login does not exist.
    """

    ENABLE_PASSWORD_RECOVERY: bool = True
    """If :py:data:`False`, then users cannot ask for a password recovery link
    by email."""

    INVITATION_EXPIRATION: int = 172800
    """The validity duration of registration invitations, in seconds.

    Defaults to 2 days.
    """

    LOGGING: Optional[Union[str, Dict]] = None
    """Configures the logging output using the python logging configuration format:

    - if :py:data:`None`, everything is logged in the standard output
      the log level is :py:data:`~logging.DEBUG` if the :attr:`~canaille.app.configuration.RootSettings.DEBUG` setting is :py:data:`True`, else this is :py:data:`~logging.INFO`
    - if this is a :class:`dict`, it is passed to :func:`logging.config.dictConfig`:
    - if this is a :class:`str`, it is expected to be a file path that will be passed
      to :func:`logging.config.fileConfig`

    For example::

        [CANAILLE.LOGGING]
        version = 1
        formatters.default.format = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        root = {level = "INFO", handlers = ["canaille"]}

        [CANAILLE.LOGGING.handlers.canaille]
        class = "logging.handlers.WatchedFileHandler"
        filename = "/var/log/canaille.log"
        formatter = "default"
    """

    SMTP: Optional[SMTPSettings] = None
    """The settings related to SMTP and mail configuration.

    If unset, mail-related features like password recovery won't be
    enabled.
    """

    ACL: Optional[Dict[str, ACLSettings]] = {"DEFAULT": ACLSettings()}
    """Mapping of permission groups. See :class:`ACLSettings` for more details.

    The ACL name can be freely choosed. For example::

        [CANAILLE.ACL.DEFAULT]
        PERMISSIONS = ["edit_self", "use_oidc"]
        READ = ["user_name", "groups"]
        WRITE = ["given_name", "family_name"]

        [CANAILLE.ACL.ADMIN]
        WRITE = ["user_name", "groups"]
    """
