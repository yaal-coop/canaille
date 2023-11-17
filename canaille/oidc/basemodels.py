import datetime
from typing import List
from typing import Optional

from canaille.backends.models import Model
from canaille.core.models import User


class Client(Model):
    """
    OpenID Connect client definition.
    """

    id: str
    description: Optional[str]
    preconsent: Optional[bool]
    post_logout_redirect_uris: List[str]
    audience: List["Client"]
    client_id: Optional[str]
    client_secret: Optional[str]
    client_id_issued_at: Optional[datetime.datetime]
    client_secret_expires_at: Optional[datetime.datetime]
    client_name: Optional[str]
    contacts: List[str]
    client_uri: Optional[str]
    redirect_uris: List[str]
    logo_uri: Optional[str]
    grant_types: List[str]
    response_types: List[str]
    scope: List[str]
    tos_uri: Optional[str]
    policy_uri: Optional[str]
    jwks_uri: Optional[str]
    jwk: Optional[str]
    token_endpoint_auth_method: Optional[str]
    software_id: Optional[str]
    software_version: Optional[str]


class AuthorizationCode(Model):
    """
    OpenID Connect temporary authorization code definition.
    """

    id: str
    authorization_code_id: str
    code: str
    client: "Client"
    subject: User
    redirect_uri: Optional[str]
    response_type: Optional[str]
    scope: List[str]
    nonce: Optional[str]
    issue_date: datetime.datetime
    lifetime: int
    challenge: Optional[str]
    challenge_method: Optional[str]
    revokation_date: datetime.datetime


class Token(Model):
    """
    OpenID Connect token definition.
    """

    id: str
    token_id: str
    access_token: str
    client: "Client"
    subject: User
    type: str
    refresh_token: str
    scope: List[str]
    issue_date: datetime.datetime
    lifetime: int
    revokation_date: datetime.datetime
    audience: List["Client"]


class Consent(Model):
    """
    Long-term user consent to an application.
    """

    id: str
    consent_id: str
    subject: User
    client: "Client"
    scope: List[str]
    issue_date: datetime.datetime
    revokation_date: datetime.datetime

    def revoke(self):
        raise NotImplementedError()

    def restore(self):
        raise NotImplementedError()
