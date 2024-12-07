import datetime

from scim2_client.engines.werkzeug import TestSCIMClient
from scim2_models import Error
from scim2_models import Resource
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.scim.endpoints import bp
from canaille.scim.endpoints import get_resource_types
from canaille.scim.endpoints import get_schemas
from canaille.scim.endpoints import get_service_provider_config


def test_authentication_failure(app):
    """Test authentication with an invalid token."""
    resource_models = [
        Resource.from_schema(schema) for schema in get_schemas().values()
    ]
    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={"headers": {"Authorization": "Bearer invalid"}},
        service_provider_config=get_service_provider_config(),
        resource_types=get_resource_types().values(),
        resource_models=resource_models,
    )
    User = scim_client.get_resource_model("User")
    error = scim_client.query(User, raise_scim_errors=False)
    assert isinstance(error, Error)
    assert not error.scim_type
    assert error.status == 401


def test_authentication_with_an_user_token(app, backend, oidc_client, user):
    """Test authentication with an user token."""
    scim_token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        subject=user,
        audience=[oidc_client],
        client=oidc_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    backend.save(scim_token)

    resource_models = [
        Resource.from_schema(schema) for schema in get_schemas().values()
    ]
    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={"headers": {"Authorization": f"Bearer {scim_token.access_token}"}},
        service_provider_config=get_service_provider_config(),
        resource_types=get_resource_types().values(),
        resource_models=resource_models,
    )
    User = scim_client.get_resource_model("User")
    error = scim_client.query(User, raise_scim_errors=False)
    assert isinstance(error, Error)
    assert not error.scim_type
    assert error.status == 401


def test_invalid_payload(app, backend, scim_client):
    # TODO: push this test in scim2-tester
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    error = scim_client.create(User(), raise_scim_errors=False)
    assert isinstance(error, Error)
    assert error.scim_type == "invalidValue"
    assert error.status == 400
