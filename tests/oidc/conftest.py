import datetime

import pytest
from authlib.oidc.core.grants.util import generate_id_token
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from canaille.oidc.oauth2utils import generate_user_info
from canaille.oidc.oauth2utils import get_jwt_config
from werkzeug.security import gen_salt


@pytest.fixture
def client(testclient, other_client, slapd_connection):
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
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        tos_uri="https://mydomain.tld/tos",
        policy_uri="https://mydomain.tld/policy",
        jwk_uri="https://mydomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://mydomain.tld/disconnected"],
    )
    c.audience = [c.dn, other_client.dn]
    c.save()

    yield c
    try:
        c.delete()
    except:
        pass


@pytest.fixture
def other_client(testclient, slapd_connection):
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
        post_logout_redirect_uris=["https://myotherdomain.tld/disconnected"],
    )
    c.audience = [c.dn]
    c.save()

    yield c
    try:
        c.delete()
    except:
        pass


@pytest.fixture
def authorization(testclient, user, client, slapd_connection):
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
    a.save()
    yield a
    try:
        a.delete()
    except:
        pass


@pytest.fixture
def token(testclient, client, user, slapd_connection):
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
    t.save()
    yield t
    try:
        t.delete()
    except:
        pass


@pytest.fixture
def id_token(testclient, client, user, slapd_connection):
    return generate_id_token(
        {},
        generate_user_info(user.dn, client.scope),
        aud=client.client_id,
        **get_jwt_config(None)
    )


@pytest.fixture
def consent(testclient, client, user, slapd_connection):
    t = Consent(
        client=client.dn,
        subject=user.dn,
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(),
    )
    t.save()
    yield t
    try:
        t.delete()
    except:
        pass
