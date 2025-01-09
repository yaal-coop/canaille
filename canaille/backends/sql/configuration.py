from pydantic import BaseModel


class SQLSettings(BaseModel):
    """Settings related to the SQL backend.

    Belong in the ``CANAILLE_SQL`` namespace.
    """

    DATABASE_URI: str
    """The SQL server URI.
    For example:

    ..code-block:: toml

        DATABASE_URI = "postgresql://user:password@localhost/database_name"
    """

    PASSWORD_SCHEMES: str = "pbkdf2_sha512"
    """Password hashing scheme.

    Defines password hashing scheme in SQL database.
    examples : "mssql2000", "ldap_salted_sha1", "pbkdf2_sha512"
    """

    AUTO_MIGRATE: bool = True
    """Whether to automatically apply database migrations.

    If :data:`True`, database migrations will be automatically applied when Canaille web application is launched.
    If :data:`False`, migrations must be applied manually with ``canaille db upgrade``.

    .. note::

        When running the CLI, migrations will never be applied.
    """
