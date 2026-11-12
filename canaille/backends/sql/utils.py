import datetime

from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import TypeDecorator
from sqlalchemy.dialects import mysql

from canaille.app.encryption import decrypt
from canaille.app.encryption import encrypt


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


class EncryptedString(TypeDecorator):
    """A string encrypted with the ``SECRET_KEY`` in the database."""

    impl = String
    cache_ok = True

    def __init__(self, length, context):
        super().__init__(length)
        self.context = context

    def process_bind_param(self, value, dialect):
        return encrypt(value, self.context)

    def process_result_value(self, value, dialect):
        return decrypt(value, self.context)

    def compare_values(self, x, y):
        # Assigning a value always writes it, even when it is unchanged,
        # so that ``canaille secrets reencrypt`` encrypts it with the current key.
        return False
