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

    POOL_SIZE: int = 5
    """The number of connections to keep persistently in the pool.

    Set to ``0`` to indicate no size limit (not recommended in production).
    See the ``pool_size`` parameter of :func:`sqlalchemy.create_engine`.
    """

    POOL_MAX_OVERFLOW: int = 10
    """The number of connections to allow in overflow beyond :attr:`POOL_SIZE`.

    When all persistent connections are in use, additional connections will be created
    up to this limit. Set to ``-1`` to indicate no overflow limit.
    See the ``max_overflow`` parameter of :func:`sqlalchemy.create_engine`.
    """

    POOL_RECYCLE: int = -1
    """Number of seconds after which a connection is automatically recycled.

    Useful to prevent the database server from closing idle connections.
    For example, MySQL/MariaDB closes idle connections after ``wait_timeout`` (default 8 hours).
    Set this to a value below the server's timeout (e.g. ``3600`` for one hour).
    ``-1`` disables recycling.
    See the ``pool_recycle`` parameter of :func:`sqlalchemy.create_engine`.
    """

    POOL_PRE_PING: bool = False
    """Whether to test connections for liveness upon each checkout.

    When enabled, a ``SELECT 1`` is emitted before each connection use
    to detect stale connections (e.g. after a database restart).
    The overhead is negligible compared to the cost of failed requests.
    See the ``pool_pre_ping`` parameter of :func:`sqlalchemy.create_engine`.
    """

    AUTO_MIGRATE: bool = True
    """Whether to automatically apply database migrations.

    If :data:`True`, database migrations will be automatically applied when Canaille web application is launched.
    If :data:`False`, migrations must be applied manually with ``canaille db upgrade``.

    .. note::

        When running the CLI, migrations will never be applied.
    """
