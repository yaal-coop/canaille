import datetime
import json
import typing
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import or_
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list
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

            # Handle association_proxy attributes
            if hasattr(column, "local_attr") and hasattr(column, "remote_attr"):
                # Get the underlying relationship (e.g., _groups_association for groups)
                underlying_attr = column.local_attr
                target_attr = column.remote_attr

                # Build a query like: User._groups_association.any(Membership.group == value)
                association_model = underlying_attr.entity.class_
                target_column = getattr(association_model, target_attr.key)
                return underlying_attr.any(target_column == value)

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


class Membership(Base):
    """Association object for Group.members with ordering support."""

    __tablename__ = "membership_association_table"

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("group.id"), primary_key=True)
    index: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")
    group: Mapped["Group"] = relationship(
        "Group", foreign_keys=[group_id], lazy="joined"
    )


class User(canaille.core.models.User, Base, SqlAlchemyModel):
    __tablename__ = "user"

    @staticmethod
    def default_password_arguments(**kwargs):
        return dict(
            schemes=Backend.instance.config["CANAILLE_SQL"]["PASSWORD_SCHEMES"],
            **Backend.instance.config["CANAILLE_SQL"].get("PASSWORD_HASH_PARAMS", {}),
            **kwargs,
        )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    user_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
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
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=True)
    family_name: Mapped[str] = mapped_column(String(100), nullable=True)
    given_name: Mapped[str] = mapped_column(String(100), nullable=True)
    formatted_name: Mapped[str] = mapped_column(String(200), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=True)
    emails: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    phone_numbers: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    formatted_address: Mapped[str] = mapped_column(Text, nullable=True)
    street: Mapped[str] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=True)
    locality: Mapped[str] = mapped_column(String(100), nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    photo: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    profile_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    employee_number: Mapped[str] = mapped_column(String(50), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(100), nullable=True)
    organization: Mapped[str] = mapped_column(String(200), nullable=True)
    _groups_association: Mapped[list["Membership"]] = relationship(
        "Membership",
        foreign_keys="Membership.user_id",
        order_by="Membership.index",
        collection_class=ordering_list("index"),
        cascade="all, delete-orphan",
        overlaps="user",
    )
    groups = association_proxy(
        "_groups_association",
        "group",
        creator=lambda grp: Membership(group=grp),
    )
    lock_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_otp_login: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    secret_token: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    hotp_counter: Mapped[int] = mapped_column(Integer, nullable=True)
    one_time_password: Mapped[str] = mapped_column(String(255), nullable=True)
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
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )

    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    _members_association: Mapped[list["Membership"]] = relationship(
        "Membership",
        foreign_keys="Membership.group_id",
        order_by="Membership.index",
        collection_class=ordering_list("index"),
        cascade="all, delete-orphan",
        overlaps="group",
    )
    members = association_proxy(
        "_members_association",
        "user",
        creator=lambda usr: Membership(user=usr),
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=True)
    owner: Mapped["User"] = relationship()
