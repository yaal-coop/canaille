import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy_json import MutableJson

import canaille.oidc.models

from ..backend import Base
from ..utils import TZDateTime
from .core import SqlAlchemyModel

if TYPE_CHECKING:
    from .core import User

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
    access_token: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("client.id"))
    client: Mapped["Client"] = relationship()
    subject_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=True)
    subject: Mapped["User"] = relationship()
    type: Mapped[str] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str] = mapped_column(String, nullable=True, unique=True)
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
