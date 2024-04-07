import datetime
import typing
import uuid
from typing import List

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy_json import MutableJson
from sqlalchemy_utils import PasswordType
from sqlalchemy_utils import force_auto_coercion

import canaille.core.models
import canaille.oidc.models
from canaille.backends.models import BackendModel

from .backend import Backend
from .backend import Base
from .utils import TZDateTime

force_auto_coercion()


class SqlAlchemyModel(BackendModel):
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
            if "str" in str(cls.attributes[attribute_name])
            # erk, photo is an URL string according to SCIM, but bytes here
            and attribute_name != "photo"
        )

        return (
            Backend.get().db_session.execute(select(cls).filter(filter)).scalars().all()
        )

    @classmethod
    def attribute_filter(cls, name, value):
        if isinstance(value, list):
            return or_(cls.attribute_filter(name, v) for v in value)

        multiple = typing.get_origin(cls.attributes[name]) is list

        if multiple:
            return getattr(cls, name).contains(value)

        return getattr(cls, name) == value

    @classmethod
    def get(cls, identifier=None, /, **kwargs):
        if identifier:
            return (
                cls.get(**{cls.identifier_attribute: identifier})
                or cls.get(id=identifier)
                or None
            )

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
        self.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not self.created:
            self.created = self.last_modified

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
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
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
    groups: Mapped[List["Group"]] = relationship(
        secondary=membership_association_table, back_populates="members"
    )
    lock_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )


class Group(canaille.core.models.Group, Base, SqlAlchemyModel):
    __tablename__ = "group"
    identifier_attribute = "display_name"

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
    identifier_attribute = "client_id"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )

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
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
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
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
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
    created: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    last_modified: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
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
