import datetime

import pytest
from scim2_client import SCIMResponseErrorObject
from scim2_client.engines.werkzeug import TestSCIMClient
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.scim.endpoints import bp


def test_authentication_failure(app):
    """Test authentication with an invalid token."""
    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={"headers": {"Authorization": "Bearer invalid"}},
    )
    with pytest.raises(SCIMResponseErrorObject):
        scim_client.discover()


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

    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={"headers": {"Authorization": f"Bearer {scim_token.access_token}"}},
    )
    with pytest.raises(SCIMResponseErrorObject):
        scim_client.discover()
