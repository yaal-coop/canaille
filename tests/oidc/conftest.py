import datetime
import os
import uuid

import pytest
from authlib.oidc.core.grants.util import generate_id_token
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.oidc.installation import generate_keypair
from canaille.oidc.oauth import generate_user_info
from canaille.oidc.oauth import get_jwt_config


@pytest.fixture
# For some reason all the params from the overriden fixture must be present here
# https://github.com/pytest-dev/pytest/issues/11075
def app(app, configuration, backend):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"
    yield app


@pytest.fixture(scope="session")
def keypair():
    return generate_keypair()


@pytest.fixture
def configuration(configuration, keypair):
    private_key, public_key = keypair
    conf = {
        **configuration,
        "OIDC": {
            "JWT": {
                "PUBLIC_KEY": public_key,
                "PRIVATE_KEY": private_key,
                "ISS": "https://auth.mydomain.tld",
            }
        },
    }
    return conf


@pytest.fixture
def client(testclient, trusted_client, backend):
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Some client",
        contacts=["contact@mydomain.tld"],
        client_uri="https://mydomain.tld",
        redirect_uris=[
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        logo_uri="https://mydomain.tld/logo.webp",
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        tos_uri="https://mydomain.tld/tos",
        policy_uri="https://mydomain.tld/policy",
        jwks_uri="https://mydomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://mydomain.tld/disconnected"],
    )
    c.audience = [c, trusted_client]
    c.save()

    yield c
    c.delete()


@pytest.fixture
def trusted_client(testclient, backend):
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Some other client",
        contacts=["contact@myotherdomain.tld"],
        client_uri="https://myotherdomain.tld",
        redirect_uris=[
            "https://myotherdomain.tld/redirect1",
            "https://myotherdomain.tld/redirect2",
        ],
        logo_uri="https://myotherdomain.tld/logo.webp",
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "profile", "groups"],
        tos_uri="https://myotherdomain.tld/tos",
        policy_uri="https://myotherdomain.tld/policy",
        jwks_uri="https://myotherdomain.tld/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://myotherdomain.tld/disconnected"],
        preconsent=True,
    )
    c.audience = [c]
    c.save()

    yield c
    c.delete()


@pytest.fixture
def authorization(testclient, user, client, backend):
    a = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-code",
        client=client,
        subject=user,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
        lifetime=3600,
        challenge="challenge",
        challenge_method="method",
    )
    a.save()
    yield a
    a.delete()


@pytest.fixture
def token(testclient, client, user, backend):
    t = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[client],
        client=client,
        subject=user,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    t.save()
    yield t
    t.delete()


@pytest.fixture
def id_token(testclient, client, user, backend):
    return generate_id_token(
        {},
        generate_user_info(user, client.scope),
        aud=client.client_id,
        **get_jwt_config(None),
    )


@pytest.fixture
def consent(testclient, client, user, backend):
    t = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
    )
    t.save()
    yield t
    t.delete()
