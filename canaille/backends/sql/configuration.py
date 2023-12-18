from pydantic import BaseModel


class SQLSettings(BaseModel):
    """Settings related to the SQL backend.

    Belong in the ``CANAILLE_SQL`` namespace.
    """

    DATABASE_URI: str
    """The SQL server URI.
    For example::

        DATABASE_URI = "postgresql://user:password@localhost/database_name"
    """
