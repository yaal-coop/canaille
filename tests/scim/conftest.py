import datetime

import pytest
from scim2_client.engines.werkzeug import TestSCIMClient
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
