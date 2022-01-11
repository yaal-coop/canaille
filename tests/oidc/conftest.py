import datetime

import pytest
from canaille.models import AuthorizationCode
from canaille.models import Client
from canaille.models import Consent
from canaille.models import Token
from werkzeug.security import gen_salt


@pytest.fixture
def client(app, slapd_connection, other_client):
    c = Client(
        oauthClientID=gen_salt(24),
        oauthClientName="Some client",
        oauthClientContact="contact@mydomain.tld",
        oauthClientURI="https://mydomain.tld",
        oauthRedirectURIs=[
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        oauthLogoURI="https://mydomain.tld/logo.png",
        oauthIssueDate=datetime.datetime.now(),
        oauthClientSecret=gen_salt(48),
        oauthGrantType=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        oauthResponseType=["code", "token", "id_token"],
        oauthScope=["openid", "profile", "groups"],
        oauthTermsOfServiceURI="https://mydomain.tld/tos",
        oauthPolicyURI="https://mydomain.tld/policy",
        oauthJWKURI="https://mydomain.tld/jwk",
        oauthTokenEndpointAuthMethod="client_secret_basic",
    )
    c.oauthAudience = [c.dn, other_client.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def other_client(app, slapd_connection):
    c = Client(
        oauthClientID=gen_salt(24),
        oauthClientName="Some other client",
        oauthClientContact="contact@myotherdomain.tld",
        oauthClientURI="https://myotherdomain.tld",
        oauthRedirectURIs=[
            "https://myotherdomain.tld/redirect1",
            "https://myotherdomain.tld/redirect2",
        ],
        oauthLogoURI="https://myotherdomain.tld/logo.png",
        oauthIssueDate=datetime.datetime.now(),
        oauthClientSecret=gen_salt(48),
        oauthGrantType=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        oauthResponseType=["code", "token", "id_token"],
        oauthScope=["openid", "profile", "groups"],
        oauthTermsOfServiceURI="https://myotherdomain.tld/tos",
        oauthPolicyURI="https://myotherdomain.tld/policy",
        oauthJWKURI="https://myotherdomain.tld/jwk",
        oauthTokenEndpointAuthMethod="client_secret_basic",
    )
    c.oauthAudience = [c.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def authorization(app, slapd_connection, user, client):
    a = AuthorizationCode(
        oauthCode="my-code",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthRedirectURI="https://foo.bar/callback",
        oauthResponseType="code",
        oauthScope="openid profile",
        oauthNonce="nonce",
        oauthAuthorizationDate=datetime.datetime(2020, 1, 1),
        oauthAuthorizationLifetime="3600",
        oauthCodeChallenge="challenge",
        oauthCodeChallengeMethod="method",
        oauthRevokation="",
    )
    a.save(slapd_connection)
    return a


@pytest.fixture
def token(slapd_connection, client, user):
    t = Token(
        oauthAccessToken=gen_salt(48),
        oauthAudience=[client.dn],
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthTokenType=None,
        oauthRefreshToken=gen_salt(48),
        oauthScope="openid profile",
        oauthIssueDate=datetime.datetime.now(),
        oauthTokenLifetime=str(3600),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture
def consent(slapd_connection, client, user):
    t = Consent(
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthScope=["openid", "profile"],
        oauthIssueDate=datetime.datetime.now(),
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
