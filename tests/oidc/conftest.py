import datetime

import pytest
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from werkzeug.security import gen_salt


@pytest.fixture
def client(app, slapd_connection, other_client):
    c = Client(
        client_id=gen_salt(24),
        name="Some client",
        contact="contact@mydomain.tld",
        uri="https://mydomain.tld",
        redirect_uris=[
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        logo_uri="https://mydomain.tld/logo.png",
        issue_date=datetime.datetime.now(),
        secret=gen_salt(48),
        grant_type=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_type=["code", "token", "id_token"],
        scope=["openid", "profile", "groups"],
        tos_uri="https://mydomain.tld/tos",
        policy_uri="https://mydomain.tld/policy",
        jwk_uri="https://mydomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
    )
    c.audience = [c.dn, other_client.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def other_client(app, slapd_connection):
    c = Client(
        client_id=gen_salt(24),
        name="Some other client",
        contact="contact@myotherdomain.tld",
        uri="https://myotherdomain.tld",
        redirect_uris=[
            "https://myotherdomain.tld/redirect1",
            "https://myotherdomain.tld/redirect2",
        ],
        logo_uri="https://myotherdomain.tld/logo.png",
        issue_date=datetime.datetime.now(),
        secret=gen_salt(48),
        grant_type=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_type=["code", "token", "id_token"],
        scope=["openid", "profile", "groups"],
        tos_uri="https://myotherdomain.tld/tos",
        policy_uri="https://myotherdomain.tld/policy",
        jwk_uri="https://myotherdomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
    )
    c.audience = [c.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def authorization(app, slapd_connection, user, client):
    a = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-code",
        client=client.dn,
        subject=user.dn,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope="openid profile",
        nonce="nonce",
        issue_date=datetime.datetime(2020, 1, 1),
        lifetime="3600",
        challenge="challenge",
        challenge_method="method",
        revokation="",
    )
    a.save(slapd_connection)
    return a


@pytest.fixture
def token(slapd_connection, client, user):
    t = Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[client.dn],
        client=client.dn,
        subject=user.dn,
        token_type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=datetime.datetime.now(),
        lifetime=str(3600),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture
def consent(slapd_connection, client, user):
    t = Consent(
        client=client.dn,
        subject=user.dn,
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture(autouse=True)
def cleanups(slapd_connection):
    yield
    try:
        for consent in Consent.filter(conn=slapd_connection):
            consent.delete(conn=slapd_connection)
    except Exception:
        pass
