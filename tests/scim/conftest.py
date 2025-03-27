import datetime
import uuid

import pytest
from httpx import Client as httpx_client
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_client.engines.werkzeug import TestSCIMClient
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.scim.endpoints import bp


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_SCIM"] = {
        "ENABLE_SERVER": True,
        "ENABLE_CLIENT": True,
    }
    return configuration


@pytest.fixture
def oidc_client(testclient, backend):
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Some client",
        contacts=["contact@mydomain.test"],
        client_uri="https://mydomain.test",
        redirect_uris=[
            "https://mydomain.test/redirect1",
        ],
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "client_credentials",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        token_endpoint_auth_method="client_secret_basic",
    )
    backend.save(c)

    yield c
    backend.delete(c)


@pytest.fixture
def oidc_token(testclient, oidc_client, backend):
    t = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[oidc_client],
        client=oidc_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    backend.save(t)
    yield t
    backend.delete(t)


@pytest.fixture
def scim_client(app, oidc_client, oidc_token):
    return TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={"headers": {"Authorization": f"Bearer {oidc_token.access_token}"}},
        check_response_status_codes=False,
    )


@pytest.fixture
def scim_trusted_client(testclient, scim2_server, backend):
    client_uri = f"http://localhost:{scim2_server.port}"
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Some client",
        contacts=["contact@mydomain.test"],
        client_uri=client_uri,
        redirect_uris=[
            client_uri + "/redirect1",
        ],
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "client_credentials",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        token_endpoint_auth_method="client_secret_basic",
        trusted=True,
    )
    backend.save(c)
    yield c
    backend.delete(c)


@pytest.fixture
def scim_token(testclient, scim_trusted_client, backend):
    t = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[scim_trusted_client],
        client=scim_trusted_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    backend.save(t)
    yield t
    backend.delete(t)


@pytest.fixture
def scim_client_for_trusted_client(scim2_server, scim_token):
    client_httpx = httpx_client(
        base_url=f"http://localhost:{scim2_server.port}",
        headers={"Authorization": f"Bearer {scim_token.access_token}"},
    )
    scim_client = SyncSCIMClient(client_httpx)
    scim_client.discover()
    return scim_client


@pytest.fixture
def client_without_scim(testclient, backend):
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Client",
        contacts=["contact@myotherdomain.test"],
        client_uri="https://myotherdomain.test",
        redirect_uris=[
            "https://myotherdomain.test/redirect1",
            "https://myotherdomain.test/redirect2",
        ],
        logo_uri="https://myotherdomain.test/logo.webp",
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
            "client_credentials",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "profile", "groups"],
        tos_uri="https://myotherdomain.test/tos",
        policy_uri="https://myotherdomain.test/policy",
        jwks_uri="https://myotherdomain.test/jwk",
        token_endpoint_auth_method="client_secret_basic",
        post_logout_redirect_uris=["https://myotherdomain.test/disconnected"],
        trusted=True,
    )
    backend.save(c)
    c.audience = [c]
    backend.save(c)

    yield c
    backend.delete(c)


@pytest.fixture
def consent(testclient, client_without_scim, user, backend):
    t = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client_without_scim,
        subject=user,
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
    )
    backend.save(t)
    yield t
    backend.delete(t)
