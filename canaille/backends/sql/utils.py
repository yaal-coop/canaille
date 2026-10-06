import datetime

from sqlalchemy import DateTime
from sqlalchemy import TypeDecorator
from sqlalchemy.dialects import mysql


def is_mysql(dialect):
    """Tell whether a dialect is MySQL or MariaDB."""
    return dialect.name in ("mysql", "mariadb")


class TZDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        # MySQL drops the fractional seconds unless asked to keep them.
        if is_mysql(dialect):
            return mysql.DATETIME(fsp=6)
        return self.impl_instance

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = value.astimezone(datetime.UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=datetime.UTC)
        return value
