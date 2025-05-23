import datetime
import typing
import uuid

from sqlalchemy import Boolean
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
from sqlalchemy_json import MutableJson
from sqlalchemy_utils import PasswordType
from sqlalchemy_utils import force_auto_coercion

import canaille.core.models
import canaille.oidc.models
from canaille.backends import Backend
from canaille.backends.models import BackendModel

from .backend import Base
from .utils import TZDateTime

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
            return getattr(cls, name).contains(value)

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


client_audience_association_table = Table(
    "client_audience_association_table",
    Base.metadata,
    Column("index", Integer, autoincrement=True),
    Column("audience_id", ForeignKey("client.id"), primary_key=True, nullable=True),
    Column("client_id", ForeignKey("client.id"), primary_key=True, nullable=True),
)


class Client(canaille.oidc.models.Client, Base, SqlAlchemyModel):
    __tablename__ = "client"

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
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=True)
    post_logout_redirect_uris: Mapped[list[str]] = mapped_column(
        MutableJson, nullable=True
    )
    audience: Mapped[list["Client"]] = relationship(
        "Client",
        secondary=client_audience_association_table,
        primaryjoin=id == client_audience_association_table.c.client_id,
        secondaryjoin=id == client_audience_association_table.c.audience_id,
        order_by=client_audience_association_table.c.index,
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
    contacts: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    client_uri: Mapped[str] = mapped_column(String, nullable=True)
    redirect_uris: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    logo_uri: Mapped[str] = mapped_column(String, nullable=True)
    grant_types: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    response_types: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    scope: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    tos_uri: Mapped[str] = mapped_column(String, nullable=True)
    policy_uri: Mapped[str] = mapped_column(String, nullable=True)
    jwks_uri: Mapped[str] = mapped_column(String, nullable=True)
    jwks: Mapped[str] = mapped_column(String, nullable=True)
    token_endpoint_auth_method: Mapped[str] = mapped_column(String, nullable=True)
    token_endpoint_auth_signing_alg: Mapped[str] = mapped_column(String, nullable=True)
    sector_identifier_uri: Mapped[str] = mapped_column(String, nullable=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=True)
    software_id: Mapped[str] = mapped_column(String, nullable=True)
    software_version: Mapped[str] = mapped_column(String, nullable=True)
    application_type: Mapped[str] = mapped_column(String, nullable=True)
    id_token_signed_response_alg: Mapped[str] = mapped_column(String, nullable=True)
    id_token_encrypted_response_alg: Mapped[str] = mapped_column(String, nullable=True)
    id_token_encrypted_response_enc: Mapped[str] = mapped_column(String, nullable=True)
    userinfo_signed_response_alg: Mapped[str] = mapped_column(String, nullable=True)
    userinfo_encrypted_response_alg: Mapped[str] = mapped_column(String, nullable=True)
    userinfo_encrypted_response_enc: Mapped[str] = mapped_column(String, nullable=True)
    default_max_age: Mapped[int] = mapped_column(Integer, nullable=True)
    require_auth_time: Mapped[bool] = mapped_column(Boolean, nullable=True)
    default_acr_values: Mapped[list[str]] = mapped_column(
        MutableJson, nullable=True, default=[]
    )
    initiate_login_uri: Mapped[str] = mapped_column(String, nullable=True)
    request_object_signing_alg: Mapped[str] = mapped_column(String, nullable=True)
    request_object_encryption_alg: Mapped[str] = mapped_column(String, nullable=True)
    request_object_encryption_enc: Mapped[str] = mapped_column(String, nullable=True)
    request_uris: Mapped[list[str]] = mapped_column(
        MutableJson, nullable=True, default=[]
    )
    require_signed_request_object: Mapped[bool] = mapped_column(Boolean, nullable=True)


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, Base, SqlAlchemyModel):
    __tablename__ = "authorization_code"

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
    scope: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
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
    auth_time: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    acr: Mapped[str] = mapped_column(String, nullable=True)
    amr: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)


token_audience_association_table = Table(
    "token_audience_association_table",
    Base.metadata,
    Column("index", Integer, autoincrement=True),
    Column("token_id", ForeignKey("token.id"), primary_key=True, nullable=True),
    Column("client_id", ForeignKey("client.id"), primary_key=True, nullable=True),
)


class Token(canaille.oidc.models.Token, Base, SqlAlchemyModel):
    __tablename__ = "token"

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
    subject_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=True)
    subject: Mapped["User"] = relationship()
    type: Mapped[str] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str] = mapped_column(String, nullable=True)
    scope: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    issue_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    lifetime: Mapped[int] = mapped_column(Integer, nullable=True)
    revokation_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    audience: Mapped[list["Client"]] = relationship(
        "Client",
        secondary=token_audience_association_table,
        primaryjoin=id == token_audience_association_table.c.token_id,
        secondaryjoin=Client.id == token_audience_association_table.c.client_id,
        order_by=token_audience_association_table.c.index,
    )


class Consent(canaille.oidc.models.Consent, Base, SqlAlchemyModel):
    __tablename__ = "consent"

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
    scope: Mapped[list[str]] = mapped_column(MutableJson, nullable=True)
    issue_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
    revokation_date: Mapped[datetime.datetime] = mapped_column(
        TZDateTime(timezone=True), nullable=True
    )
