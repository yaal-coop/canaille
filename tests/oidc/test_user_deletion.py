import datetime
import uuid
from unittest import mock

import pytest
from werkzeug.security import gen_salt

from canaille.app import models

from . import client_credentials


@pytest.fixture
def grants(backend, client):
    """Create a user with a consent, an authorization code, a device code and a token."""
    user = models.User(
        user_name="temp-user",
        formatted_name="Temp User",
        family_name="User",
        emails=["temp@user.test"],
    )
    backend.save(user)

    now = datetime.datetime.now(datetime.UTC)
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=["openid"],
        issue_date=now,
    )
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=gen_salt(48),
        client=client,
        subject=user,
        redirect_uri="https://client.test/redirect1",
        response_type="code",
        scope=["openid"],
        issue_date=now,
        lifetime=3600,
    )
    device_code = models.DeviceCode(
        device_code_id=gen_salt(48),
        device_code=gen_salt(48),
        user_code="USER-CODE",
        client=client,
        subject=user,
        scope=["openid"],
        status="authorized",
        issue_date=now,
        lifetime=600,
    )
    token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        refresh_token=gen_salt(48),
        audience=[client],
        client=client,
        subject=user,
        scope=["openid"],
        issue_date=now,
        lifetime=3600,
    )
    for instance in (consent, code, device_code, token):
        backend.save(instance)

    return user, consent, code, device_code, token


def test_user_deletion_deletes_their_grants(testclient, backend, client, grants):
    """Deleting a user deletes their consents, codes and tokens."""
    user, consent, code, device_code, token = grants
    consent_id = consent.consent_id
    authorization_code_id = code.authorization_code_id
    device_code_id = device_code.device_code_id
    token_id = token.token_id
    access_token = token.access_token

    backend.delete(user)

    assert not backend.get(models.Consent, consent_id=consent_id)
    assert not backend.get(
        models.AuthorizationCode, authorization_code_id=authorization_code_id
    )
    assert not backend.get(models.DeviceCode, device_code_id=device_code_id)
    assert not backend.get(models.Token, token_id=token_id)

    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=access_token),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert res.json == {"active": False}


def test_user_deletion_without_oidc(testclient, backend, monkeypatch):
    """Without OIDC, deleting a user does not query the OIDC objects."""
    user = models.User(
        user_name="temp-user",
        formatted_name="Temp User",
        family_name="User",
        emails=["temp@user.test"],
    )
    backend.save(user)

    monkeypatch.setitem(testclient.app.config["CANAILLE_OIDC"], "ENABLE_OIDC", False)
    with mock.patch.object(backend, "query", wraps=backend.query) as query:
        backend.delete(user)

    queried_models = {call.args[0] for call in query.call_args_list}
    assert not queried_models & {
        models.Consent,
        models.AuthorizationCode,
        models.DeviceCode,
        models.Token,
    }
    assert not backend.get(models.User, user_name="temp-user")
