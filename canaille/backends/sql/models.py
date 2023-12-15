import datetime
import uuid
from typing import List

import canaille.core.models
import canaille.oidc.models
from canaille.app import models
from canaille.backends.models import Model
from flask import current_app
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import relationship
from sqlalchemy_json import MutableJson
from sqlalchemy_utils import force_auto_coercion
from sqlalchemy_utils import PasswordType

from .backend import Backend
from .backend import Base
from .utils import TZDateTime

force_auto_coercion()


class SqlAlchemyModel(Model):
    def __html__(self):
        return self.id

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {self.identifier_attribute}={self.identifier}>"
        )

    @classmethod
    def query(cls, **kwargs):
        filter = [
            cls.attribute_filter(attribute_name, expected_value)
            for attribute_name, expected_value in kwargs.items()
        ]
        return (
            Backend.get()
            .db_session.execute(select(cls).filter(*filter))
            .scalars()
            .all()
        )

    @classmethod
    def fuzzy(cls, query, attributes=None, **kwargs):
        attributes = attributes or cls.attributes
        filter = or_(
            getattr(cls, attribute_name).ilike(f"%{query}%")
            for attribute_name in attributes
            if "str" in str(cls.__annotations__[attribute_name])
        )

        return (
            Backend.get().db_session.execute(select(cls).filter(filter)).scalars().all()
        )

    @classmethod
    def attribute_filter(cls, name, value):
        if isinstance(value, list):
            return or_(cls.attribute_filter(name, v) for v in value)

        multiple = "List" in str(cls.__annotations__[name])
        if multiple:
            return getattr(cls, name).contains(value)

        return getattr(cls, name) == value

    @classmethod
    def get(cls, identifier=None, **kwargs):
        if identifier:
            kwargs[cls.identifier_attribute] = identifier

        filter = [
            cls.attribute_filter(attribute_name, expected_value)
            for attribute_name, expected_value in kwargs.items()
        ]
        return (
            Backend.get()
            .db_session.execute(select(cls).filter(*filter))
            .scalar_one_or_none()
        )

    @property
    def identifier(self):
        return getattr(self, self.identifier_attribute)

    def save(self):
        Backend.get().db_session.add(self)
        Backend.get().db_session.commit()

    def delete(self):
        Backend.get().db_session.delete(self)
        Backend.get().db_session.commit()

    def reload(self):
        Backend.get().db_session.refresh(self)


membership_association_table = Table(
    "membership_association_table",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)


class User(canaille.core.models.User, Base, SqlAlchemyModel):
    __tablename__ = "user"
    identifier_attribute = "user_name"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(
        PasswordType(schemes=["pbkdf2_sha512"]), nullable=True
    )
    preferred_language: Mapped[str] = mapped_column(String, nullable=True)
    family_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    formatted_name: Mapped[str] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    emails: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    phone_numbers: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
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
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    groups: Mapped[List["Group"]] = relationship(
        secondary=membership_association_table, back_populates="members"
    )
    lock_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_permissions()

    def reload(self):
        super().reload()
        self.load_permissions()

    @reconstructor
    def load_permissions(self):
        self.permissions = set()
        self.read = set()
        self.write = set()
        for access_group_name, details in current_app.config.get("ACL", {}).items():
            if self.match_filter(details.get("FILTER")):
                self.permissions |= set(details.get("PERMISSIONS", []))
                self.read |= set(details.get("READ", []))
                self.write |= set(details.get("WRITE", []))

    def normalize_filter_value(self, attribute, value):
        # not super generic, but we can improve this when we have
        # type checking and/or pydantic for the models
        if attribute == "groups":
            if models.Group.get(id=value):
                return models.Group.get(id=value)
            elif models.Group.get(display_name=value):
                return models.Group.get(display_name=value)
        return value

    def match_filter(self, filter):
        if filter is None:
            return True

        if isinstance(filter, dict):
            return all(
                self.normalize_filter_value(attribute, value)
                in getattr(self, attribute, [])
                if "List" in str(self.__annotations__[attribute])
                else self.normalize_filter_value(attribute, value)
                == getattr(self, attribute, None)
                for attribute, value in filter.items()
            )

        return any(self.match_filter(subfilter) for subfilter in filter)

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        return User.get(user_name=login)

    def has_password(self):
        return self.password is not None

    def check_password(self, password):
        if password != self.password:
            return (False, None)

        if self.locked:
            return (False, "Your account has been locked.")

        return (True, None)

    def set_password(self, password):
        self.password = password
        self.save()

    def save(self):
        self.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        super().save()


class Group(canaille.core.models.Group, Base, SqlAlchemyModel):
    __tablename__ = "group"
    identifier_attribute = "display_name"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    display_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, nullable=True)
    members: Mapped[List["User"]] = relationship(
        secondary=membership_association_table, back_populates="groups"
    )


client_audience_association_table = Table(
    "client_audience_association_table",
    Base.metadata,
    Column("audience_id", ForeignKey("client.id"), primary_key=True, nullable=True),
    Column("client_id", ForeignKey("client.id"), primary_key=True, nullable=True),
)


class Client(canaille.oidc.models.Client, Base, SqlAlchemyModel):
    __tablename__ = "client"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    identifier_attribute = "client_id"

    description: Mapped[str] = mapped_column(String, nullable=True)
    preconsent: Mapped[bool] = mapped_column(Boolean, nullable=True)
    post_logout_redirect_uris: Mapped[List[str]] = mapped_column(
        MutableJson, nullable=True
    )
    audience: Mapped[List["Client"]] = relationship(
        "Client",
        secondary=client_audience_association_table,
        primaryjoin=id == client_audience_association_table.c.client_id,
        secondaryjoin=id == client_audience_association_table.c.audience_id,
    )
    client_id: Mapped[str] = mapped_column(String, nullable=True)
    client_secret: Mapped[str] = mapped_column(String, nullable=True)
    client_id_issued_at: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    client_secret_expires_at: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    client_name: Mapped[str] = mapped_column(String, nullable=True)
    contacts: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    client_uri: Mapped[str] = mapped_column(String, nullable=True)
    redirect_uris: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    logo_uri: Mapped[str] = mapped_column(String, nullable=True)
    grant_types: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    response_types: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    scope: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    tos_uri: Mapped[str] = mapped_column(String, nullable=True)
    policy_uri: Mapped[str] = mapped_column(String, nullable=True)
    jwks_uri: Mapped[str] = mapped_column(String, nullable=True)
    jwk: Mapped[str] = mapped_column(String, nullable=True)
    token_endpoint_auth_method: Mapped[str] = mapped_column(String, nullable=True)
    software_id: Mapped[str] = mapped_column(String, nullable=True)
    software_version: Mapped[str] = mapped_column(String, nullable=True)


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, Base, SqlAlchemyModel):
    __tablename__ = "authorization_code"
    identifier_attribute = "authorization_code_id"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    authorization_code_id: Mapped[str] = mapped_column(String, nullable=True)
    code: Mapped[str] = mapped_column(String, nullable=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("client.id"))
    client: Mapped["Client"] = relationship()
    subject_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    subject: Mapped["User"] = relationship()
    redirect_uri: Mapped[str] = mapped_column(String, nullable=True)
    response_type: Mapped[str] = mapped_column(String, nullable=True)
    scope: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    nonce: Mapped[str] = mapped_column(String, nullable=True)
    issue_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    lifetime: Mapped[int] = mapped_column(Integer, nullable=True)
    challenge: Mapped[str] = mapped_column(String, nullable=True)
    challenge_method: Mapped[str] = mapped_column(String, nullable=True)
    revokation_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )


token_audience_association_table = Table(
    "token_audience_association_table",
    Base.metadata,
    Column("token_id", ForeignKey("token.id"), primary_key=True, nullable=True),
    Column("client_id", ForeignKey("client.id"), primary_key=True, nullable=True),
)


class Token(canaille.oidc.models.Token, Base, SqlAlchemyModel):
    __tablename__ = "token"
    identifier_attribute = "token_id"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    token_id: Mapped[str] = mapped_column(String, nullable=True)
    access_token: Mapped[str] = mapped_column(String, nullable=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("client.id"))
    client: Mapped["Client"] = relationship()
    subject_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    subject: Mapped["User"] = relationship()
    type: Mapped[str] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str] = mapped_column(String, nullable=True)
    scope: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    issue_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    lifetime: Mapped[int] = mapped_column(Integer, nullable=True)
    revokation_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    audience: Mapped[List["Client"]] = relationship(
        "Client",
        secondary=token_audience_association_table,
        primaryjoin=id == token_audience_association_table.c.token_id,
        secondaryjoin=Client.id == token_audience_association_table.c.client_id,
    )


class Consent(canaille.oidc.models.Consent, Base, SqlAlchemyModel):
    __tablename__ = "consent"
    identifier_attribute = "consent_id"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    consent_id: Mapped[str] = mapped_column(String, nullable=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    subject: Mapped["User"] = relationship()
    client_id: Mapped[str] = mapped_column(ForeignKey("client.id"))
    client: Mapped["Client"] = relationship()
    scope: Mapped[List[str]] = mapped_column(MutableJson, nullable=True)
    issue_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    revokation_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
