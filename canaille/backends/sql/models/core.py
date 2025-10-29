import datetime
import json
import typing
import uuid

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import or_
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm.properties import ColumnProperty
from sqlalchemy_json import MutableJson
from sqlalchemy_utils import PasswordType
from sqlalchemy_utils import force_auto_coercion

import canaille.core.models
from canaille.backends import Backend
from canaille.backends.models import BackendModel

from ..backend import Base
from ..utils import TZDateTime

force_auto_coercion()


class SqlAlchemyModel(BackendModel):
    __mapper_args__ = {
        # avoids warnings on double deletions
        "confirm_deleted_rows": False,
    }

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {self.identifier_attribute}={self.identifier}>"
        )

    @classmethod
    def attribute_filter(cls, name, value):
        if isinstance(value, list):
            return or_(cls.attribute_filter(name, v) for v in value)

        multiple = typing.get_origin(cls.attributes[name]) is list

        if multiple:
            column = getattr(cls, name)
            column_property = getattr(cls, name).property
            if not isinstance(column_property, ColumnProperty):
                return column.contains(value)

            # This is a JSON column with primitive values - use exact matching
            # to prevent MultipleResultsFound when searching partial strings
            quoted_value = json.dumps(value)  # Properly escape the value
            return column.cast(String).like(f"%{quoted_value}%")

        return getattr(cls, name) == value

    @classmethod
    def is_attr_required(cls, attr_name: str) -> bool:
        if attr_name in class_mapper(cls).relationships and hasattr(
            cls, f"{attr_name}_id"
        ):
            return cls.is_attr_required(f"{attr_name}_id")

        attr = getattr(cls, attr_name)
        return not getattr(attr, "nullable", True)

    @classmethod
    def is_attr_readonly(cls, attr_name: str) -> bool:
        return False


membership_association_table = Table(
    "membership_association_table",
    Base.metadata,
    Column("index", Integer, autoincrement=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)


class User(canaille.core.models.User, Base, SqlAlchemyModel):
    __tablename__ = "user"

    @staticmethod
    def default_password_arguments(**kwargs):
        return dict(
            schemes=Backend.instance.config["CANAILLE_SQL"]["PASSWORD_SCHEMES"],
            **kwargs,
        )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    user_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(
        PasswordType(
            onload=default_password_arguments,
        ),
        nullable=True,
    )

    def get_password_hash(self):
        if self.password is None:
            return None
        return self.password.hash.decode("utf-8")

    password_last_update: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    _password_failure_timestamps: Mapped[list[str]] = mapped_column(
        MutableJson, nullable=True
    )
    preferred_language: Mapped[str] = mapped_column(String, nullable=True)
    family_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    formatted_name: Mapped[str] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    emails: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    phone_numbers: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    formatted_address: Mapped[str] = mapped_column(String, nullable=True)
    street: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True)
    locality: Mapped[str] = mapped_column(String, nullable=True)
    region: Mapped[str] = mapped_column(String, nullable=True)
    photo: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    profile_url: Mapped[str] = mapped_column(String, nullable=True)
    employee_number: Mapped[str] = mapped_column(String, nullable=True)
    department: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    organization: Mapped[str] = mapped_column(String, nullable=True)
    groups: Mapped[list["Group"]] = relationship(
        secondary=membership_association_table,
        back_populates="members",
        order_by=membership_association_table.c.index,
    )
    lock_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_otp_login: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    secret_token: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    hotp_counter: Mapped[int] = mapped_column(Integer, nullable=True)
    one_time_password: Mapped[str] = mapped_column(String, nullable=True)
    one_time_password_emission_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )

    @property
    def password_failure_timestamps(self):
        if self._password_failure_timestamps:
            return [
                datetime.datetime.fromisoformat(d)
                for d in self._password_failure_timestamps
            ]
        return self._password_failure_timestamps

    @password_failure_timestamps.setter
    def password_failure_timestamps(self, dates_list):
        if dates_list:
            self._password_failure_timestamps = [str(d) for d in dates_list]
        else:
            self._password_failure_timestamps = dates_list


class Group(canaille.core.models.Group, Base, SqlAlchemyModel):
    __tablename__ = "group"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )

    display_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    members: Mapped[list["User"]] = relationship(
        secondary=membership_association_table,
        back_populates="groups",
        order_by=membership_association_table.c.index,
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=True)
    owner: Mapped["User"] = relationship()
