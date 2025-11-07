from pydantic import Field

from canaille.app.configuration import BaseModel


class SQLSettings(BaseModel):
    """Settings related to the SQL backend.

    Belong in the ``CANAILLE_SQL`` namespace.
    """

    DATABASE_URI: str = Field(
        "sqlite:///canaille.sqlite",
        examples=[
            "sqlite:///canaille.sqlite",
            "postgresql://user:password@localhost/database_name",
        ],
    )
    """The SQL server URI.
    For example:

    .. code-block:: toml

        DATABASE_URI = "postgresql://user:password@localhost/database_name"
    """

    PASSWORD_SCHEMES: str = "pbkdf2_sha512"
    """Password hashing scheme.

    Defines password hashing scheme in SQL database.
    See the :mod:`passlib.hash` documentation for a complete list of available schemes.

    Examples: ``"mssql2000"``, ``"ldap_salted_sha1"``, ``"pbkdf2_sha512"``, ``"argon2"``, ``"scrypt"``
    """

    PASSWORD_HASH_PARAMS: dict = Field(default_factory=dict)
    """Additional parameters for password hashing.

    These parameters are passed directly to passlib's :class:`~passlib.context.CryptContext`.
    Useful for customizing hash parameters like rounds/iterations.

    Example to tune PBKDF2:

    .. code-block:: toml

        [CANAILLE_SQL]
        PASSWORD_HASH_PARAMS = { "pbkdf2_sha512__rounds" = 100000 }
    """

    AUTO_MIGRATE: bool = True
    """Whether to automatically apply database migrations.

    If :data:`True`, database migrations will be automatically applied when Canaille web application is launched.
    If :data:`False`, migrations must be applied manually with ``canaille db upgrade``.

    .. note::

        When running the CLI, migrations will never be applied.
    """
