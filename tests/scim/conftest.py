import datetime
import threading
import uuid

import pytest
from httpx import Client as httpx_client
from scim2_client.engines.httpx import SyncSCIMClient
from scim2_client.engines.werkzeug import TestSCIMClient
from scim2_server.backend import InMemoryBackend
from scim2_server.provider import SCIMProvider
from scim2_server.utils import load_default_resource_types
from scim2_server.utils import load_default_schemas
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.scim.endpoints import bp


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_SCIM"] = {
        "ENABLE_SERVER": True,
    }
    configuration["CANAILLE"]["LOGGING"]["loggers"]["httpx"] = {
        "level": "INFO",
    }
    configuration["CANAILLE"]["LOGGING"]["loggers"]["httpcore"] = {
        "level": "INFO",
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


@pytest.fixture(scope="session")
def scim_server():
    from werkzeug.serving import run_simple

    backend = InMemoryBackend()
    app = SCIMProvider(backend)

    for schema in load_default_schemas().values():
        app.register_schema(schema)
    for resource_type in load_default_resource_types().values():
        app.register_resource_type(resource_type)

    t = threading.Thread(
        target=run_simple,
        daemon=True,
        kwargs=dict(
            hostname="localhost",
            port=8080,
            application=app,
            use_debugger=True,
        ),
    )
    t.start()

    yield app


@pytest.fixture
def scim_preconsented_client(testclient, backend):
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Some client",
        contacts=["contact@mydomain.test"],
        client_uri="http://localhost:8080",
        redirect_uris=[
            "http://localhost:8080/redirect1",
        ],
        client_id_issued_at=datetime.datetime.now(datetime.timezone.utc),
        client_secret=gen_salt(48),
        grant_types=[
            "client_credentials",
        ],
        response_types=["code", "token", "id_token"],
        scope=["openid", "email", "profile", "groups", "address", "phone"],
        token_endpoint_auth_method="client_secret_basic",
        preconsent=True,
    )
    backend.save(c)
    yield c
    backend.delete(c)


@pytest.fixture
def scim_token(testclient, scim_preconsented_client, backend):
    t = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        audience=[scim_preconsented_client],
        client=scim_preconsented_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    backend.save(t)
    yield t
    backend.delete(t)


@pytest.fixture
def scim_client_for_preconsented_client(app, scim_preconsented_client, scim_token):
    client_httpx = httpx_client(
        base_url=scim_preconsented_client.client_uri,
        headers={"Authorization": f"Bearer {scim_token.access_token}"},
    )
    scim = SyncSCIMClient(client_httpx)
    scim.discover()

    return scim


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
        preconsent=True,
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
