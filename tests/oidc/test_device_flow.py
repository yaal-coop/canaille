import datetime
import re

from authlib.oauth2.rfc8628 import endpoint

from canaille.app import models
from tests.htmx import htmx_headers

from . import client_credentials

DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


def enable_device_grant(client, backend):
    client.grant_types = client.grant_types + [DEVICE_GRANT]
    backend.save(client)


def request_device_code(testclient, client, status=200, scope="openid profile"):
    """Request a device code at the device authorization endpoint."""
    return testclient.post(
        "/oauth/device_authorization",
        params={"scope": scope},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=status,
    )


def test_device_authorization_endpoint(testclient, client, backend):
    """The device authorization endpoint issues a device and user code."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    assert "device_code" in res.json
    assert "user_code" in res.json
    assert res.json["verification_uri"].endswith("/oauth/device")
    assert res.json["verification_uri_complete"].endswith(
        "user_code=" + res.json["user_code"]
    )
    assert res.json["expires_in"] == 1800
    assert res.json["interval"] == 5

    device_code = backend.get(models.DeviceCode, device_code=res.json["device_code"])
    assert device_code.status == "pending"
    assert device_code.client == client
    assert set(device_code.scope) == {"openid", "profile"}
    backend.delete(device_code)


def test_device_flow_nominal(testclient, logged_user, client, backend):
    """The full device flow: request, poll, authorize, get a token."""
    enable_device_grant(client, backend)

    res = request_device_code(testclient, client)
    device_code = res.json["device_code"]
    user_code = res.json["user_code"]

    # Polling before authorization is pending.
    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "authorization_pending"

    # Polling again too fast asks the client to slow down.
    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "slow_down"

    # The user visits the verification endpoint and approves.
    res = testclient.get("/oauth/device", params={"user_code": user_code}, status=200)
    res = res.form.submit(name="answer", value="accept", status=200)

    device_code_obj = backend.get(models.DeviceCode, device_code=device_code)
    assert device_code_obj.status == "authorized"
    assert device_code_obj.subject == logged_user
    assert backend.query(models.Consent, client=client, subject=logged_user)

    # Polling now returns a token.
    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    # The device code is single use.
    assert backend.get(models.DeviceCode, device_code=device_code) is None


def test_device_flow_denied(testclient, logged_user, client, backend):
    """A denied authorization request results in access_denied."""
    enable_device_grant(client, backend)

    res = request_device_code(testclient, client)
    device_code = res.json["device_code"]
    user_code = res.json["user_code"]

    res = testclient.get("/oauth/device", params={"user_code": user_code}, status=200)
    res.form.submit(name="answer", value="deny", status=200)

    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "access_denied"
    assert not backend.get(models.DeviceCode, device_code=device_code)


def test_device_verification_requires_login(testclient, client, backend):
    """An anonymous user is redirected to the login page."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    user_code = res.json["user_code"]
    testclient.get("/oauth/device", params={"user_code": user_code}, status=302)


def test_device_verification_invalid_code(testclient, logged_user):
    """An invalid user code displays an error and the entry form."""
    res = testclient.get("/oauth/device", params={"user_code": "XXXX-XXXX"}, status=200)
    res.mustcontain("invalid")


def test_device_verification_entry_form(testclient, logged_user):
    """Without a user code, the entry form is displayed."""
    res = testclient.get("/oauth/device", status=200)
    res.mustcontain("Authorize a device")


def test_device_verification_inline_validation(testclient, logged_user):
    """Inline field validation returns only the field, not the whole page."""
    res = testclient.get("/oauth/device", status=200)
    res = testclient.post(
        "/oauth/device",
        {"csrf_token": res.form["csrf_token"].value, "user_code": "WD"},
        headers=htmx_headers("user_code"),
        status=200,
    )
    res.mustcontain("user_code")
    assert "Authorize a device" not in res.text


def test_device_verification_user_code_normalization(
    testclient, logged_user, client, backend
):
    """A user code is matched regardless of case and punctuation."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    user_code = res.json["user_code"]
    messy = user_code.replace("-", " ").lower()
    testclient.get(
        "/oauth/device", params={"user_code": messy}, status=200
    ).mustcontain("Accept")


def test_device_user_code_type_digital(testclient, client, backend):
    """The digital user code type produces a numeric code."""
    enable_device_grant(client, backend)
    testclient.app.config["CANAILLE_OIDC"]["DEVICE_USER_CODE_TYPE"] = "digital"
    res = request_device_code(testclient, client)
    assert re.fullmatch(r"\d{3}-\d{3}-\d{3}", res.json["user_code"])
    backend.delete(backend.get(models.DeviceCode, device_code=res.json["device_code"]))


def test_device_entry_placeholder_adapts_to_config(testclient, logged_user):
    """The user code field placeholder reflects the configured code type."""
    res = testclient.get("/oauth/device", status=200)
    res.mustcontain("WDJB-MJHT")

    testclient.app.config["CANAILLE_OIDC"]["DEVICE_USER_CODE_TYPE"] = "digital"
    res = testclient.get("/oauth/device", status=200)
    res.mustcontain("019-450-730")


def test_device_verification_no_permission(testclient, logged_user, client, backend):
    """A user without the use_oidc permission cannot authorize a device."""
    enable_device_grant(client, backend)
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    res = request_device_code(testclient, client)
    testclient.get(
        "/oauth/device", params={"user_code": res.json["user_code"]}, status=403
    )


def test_device_decision_code_gone(testclient, logged_user, client, backend):
    """If the code is gone when the decision is submitted, an error is shown."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    res = testclient.get(
        "/oauth/device", params={"user_code": res.json["user_code"]}, status=200
    )
    # The code is consumed or expires before the user submits the form.
    for device_code in backend.query(models.DeviceCode):
        backend.delete(device_code)
    res = res.form.submit(name="answer", value="accept", status=200)
    res.mustcontain("invalid")


def test_device_flow_expired(testclient, logged_user, client, backend):
    """An expired device code results in expired_token."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    device_code = res.json["device_code"]
    device_code_obj = backend.get(models.DeviceCode, device_code=device_code)
    device_code_obj.issue_date = datetime.datetime.now(
        datetime.UTC
    ) - datetime.timedelta(hours=2)
    device_code_obj.lifetime = 1
    backend.save(device_code_obj)

    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "expired_token"
    backend.delete(backend.get(models.DeviceCode, device_code=device_code))


def test_device_flow_unauthorized_client(testclient, logged_user, client, backend):
    """A client that lost the device grant cannot exchange its device code."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    device_code = res.json["device_code"]

    client.grant_types = [g for g in client.grant_types if g != DEVICE_GRANT]
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "unauthorized_client"
    backend.delete(backend.get(models.DeviceCode, device_code=device_code))


def test_device_authorization_without_device_grant(testclient, client, backend):
    """A client without the device grant cannot get a device code."""
    res = request_device_code(testclient, client, status=400)
    assert res.json["error"] == "unauthorized_client"
    assert not backend.query(models.DeviceCode)


def test_device_authorization_requires_client_authentication(
    testclient, client, backend
):
    """A confidential client must authenticate to get a device code."""
    enable_device_grant(client, backend)
    res = testclient.post(
        "/oauth/device_authorization",
        params={"client_id": client.client_id, "scope": "openid profile"},
        status=401,
    )
    assert res.json["error"] == "invalid_client"
    assert not backend.query(models.DeviceCode)


def test_device_authorization_public_client(testclient, client, backend):
    """A public client only sends its client_id to get a device code."""
    enable_device_grant(client, backend)
    client.token_endpoint_auth_method = "none"
    backend.save(client)
    res = testclient.post(
        "/oauth/device_authorization",
        params={"client_id": client.client_id, "scope": "openid profile"},
        status=200,
    )
    backend.delete(backend.get(models.DeviceCode, device_code=res.json["device_code"]))


def test_device_owned_client_non_owner(testclient, logged_user, admin, client, backend):
    """A user who cannot use an owned client cannot authorize a device for it."""
    enable_device_grant(client, backend)
    client.owners = [admin]
    backend.save(client)
    res = request_device_code(testclient, client)
    user_code = res.json["user_code"]

    testclient.get("/oauth/device", params={"user_code": user_code}, status=403)

    res = testclient.get("/oauth/device", status=200)
    testclient.post(
        "/oauth/device",
        {
            "csrf_token": res.form["csrf_token"].value,
            "user_code": user_code,
            "answer": "accept",
        },
        status=403,
    )
    device_code = backend.get(models.DeviceCode, user_code=user_code)
    assert device_code.status == "pending"
    assert not backend.query(models.Consent, client=client, subject=logged_user)
    backend.delete(device_code)


def test_device_owned_client_owner(testclient, logged_user, client, backend):
    """The owner of a client can authorize a device for it."""
    enable_device_grant(client, backend)
    client.owners = [logged_user]
    backend.save(client)
    res = request_device_code(testclient, client)

    res = testclient.get(
        "/oauth/device", params={"user_code": res.json["user_code"]}, status=200
    )
    res.form.submit(name="answer", value="accept", status=200)


def test_device_decision_of_another_code_with_same_user_code(
    testclient, logged_user, admin, client, backend
):
    """The decision on an old code does not apply to a new code with the same user code."""
    enable_device_grant(client, backend)
    now = datetime.datetime.now(datetime.UTC)
    old_device_code = models.DeviceCode(
        device_code_id="old-device-code",
        device_code="old-device-code",
        user_code="SAME-CODE",
        client=client,
        subject=admin,
        scope=["openid", "profile"],
        status="authorized",
        issue_date=now - datetime.timedelta(hours=2),
        lifetime=1,
    )
    backend.save(old_device_code)
    device_code = models.DeviceCode(
        device_code_id="new-device-code",
        device_code="new-device-code",
        user_code="SAME-CODE",
        client=client,
        scope=["openid", "profile"],
        status="pending",
        issue_date=now,
        lifetime=1800,
    )
    backend.save(device_code)

    res = testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": "new-device-code"},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "authorization_pending"
    backend.delete(old_device_code)
    backend.delete(device_code)


def approve_device(testclient, client):
    """Request a device code and approve it as the logged user."""
    res = request_device_code(testclient, client)
    device_code = res.json["device_code"]
    res = testclient.get(
        "/oauth/device", params={"user_code": res.json["user_code"]}, status=200
    )
    res.form.submit(name="answer", value="accept", status=200)
    return device_code


def poll(testclient, client, device_code, status):
    """Poll the token endpoint with a device code."""
    return testclient.post(
        "/oauth/token",
        params={"grant_type": DEVICE_GRANT, "device_code": device_code},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=status,
    )


def test_device_flow_user_locked_after_approval(
    testclient, logged_user, client, backend
):
    """A user locked after the approval gets no token."""
    enable_device_grant(client, backend)
    device_code = approve_device(testclient, client)

    logged_user.lock_date = datetime.datetime.now(datetime.UTC)
    backend.save(logged_user)

    res = poll(testclient, client, device_code, status=400)
    assert res.json["error"] == "invalid_grant"
    assert not backend.query(models.Token, client=client)
    assert not backend.get(models.DeviceCode, device_code=device_code)


def test_device_flow_user_cannot_use_client_after_approval(
    testclient, logged_user, admin, client, backend
):
    """A user who cannot use the client anymore gets no token."""
    enable_device_grant(client, backend)
    device_code = approve_device(testclient, client)

    client.owners = [admin]
    backend.save(client)

    res = poll(testclient, client, device_code, status=400)
    assert res.json["error"] == "invalid_grant"
    assert not backend.query(models.Token, client=client)
    assert not backend.get(models.DeviceCode, device_code=device_code)


def test_device_flow_user_deleted_after_approval(testclient, user, client, backend):
    """A user deleted after the approval gets no token."""
    enable_device_grant(client, backend)
    device_code = models.DeviceCode(
        device_code_id="deleted-user-device-code",
        device_code="deleted-user-device-code",
        user_code="DELE-TEDU",
        client=client,
        subject=user,
        scope=["openid", "profile"],
        status="authorized",
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=1800,
    )
    backend.save(device_code)
    backend.delete(user)

    res = poll(testclient, client, "deleted-user-device-code", status=400)
    assert res.json["error"] in ("invalid_grant", "invalid_request")
    assert not backend.query(models.Token, client=client)
    assert not backend.get(models.DeviceCode, device_code="deleted-user-device-code")


def test_device_unknown_answer(testclient, logged_user, client, backend):
    """An unknown answer is rejected and leaves the code pending."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    user_code = res.json["user_code"]
    res = testclient.get("/oauth/device", params={"user_code": user_code}, status=200)
    testclient.post(
        "/oauth/device",
        {
            "csrf_token": res.form["csrf_token"].value,
            "user_code": user_code,
            "answer": "foobar",
        },
        status=400,
    )

    device_code = backend.get(models.DeviceCode, user_code=user_code)
    assert device_code.status == "pending"
    backend.delete(device_code)


def test_device_client_lost_device_grant(testclient, logged_user, client, backend):
    """A code is invalid once its client cannot use the device grant anymore."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client)
    user_code = res.json["user_code"]
    res = testclient.get("/oauth/device", params={"user_code": user_code}, status=200)

    client.grant_types = [g for g in client.grant_types if g != DEVICE_GRANT]
    backend.save(client)

    testclient.get(
        "/oauth/device", params={"user_code": user_code}, status=200
    ).mustcontain("invalid")
    res.form.submit(name="answer", value="accept", status=200).mustcontain("invalid")

    device_code = backend.get(models.DeviceCode, user_code=user_code)
    assert device_code.status == "pending"
    assert not backend.query(models.Consent, client=client, subject=logged_user)
    backend.delete(device_code)


def test_device_authorization_filters_scope(testclient, client, backend):
    """Only the scopes allowed for the client are stored."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client, scope="openid profile admin")

    device_code = backend.get(models.DeviceCode, device_code=res.json["device_code"])
    assert set(device_code.scope) == {"openid", "profile"}
    backend.delete(device_code)


def test_device_authorization_unknown_scope(testclient, client, backend):
    """A request with no scope allowed for the client is refused."""
    enable_device_grant(client, backend)
    res = request_device_code(testclient, client, status=400, scope="admin")
    assert res.json["error"] == "invalid_scope"
    assert not backend.query(models.DeviceCode)


def test_device_consent_revocation(testclient, logged_user, client, backend):
    """Revoking the consent invalidates the approved device codes."""
    enable_device_grant(client, backend)
    device_code = approve_device(testclient, client)

    consent = backend.get(models.Consent, client=client, subject=logged_user)
    consent.revoke()

    assert not backend.get(models.DeviceCode, device_code=device_code)
    res = poll(testclient, client, device_code, status=400)
    assert res.json["error"] == "invalid_request"
    backend.delete(consent)


def test_device_user_code_collision(testclient, client, backend, monkeypatch):
    """A new user code is generated when an active device code already uses it."""
    enable_device_grant(client, backend)
    existing = models.DeviceCode(
        device_code_id="existing-device-code",
        device_code="existing-device-code",
        user_code="SAME-CODE",
        client=client,
        scope=["openid"],
        status="pending",
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=1800,
    )
    backend.save(existing)
    user_codes = iter(["SAME-CODE", "OTHE-RCOD"])
    monkeypatch.setattr(endpoint, "create_string_user_code", lambda: next(user_codes))

    res = request_device_code(testclient, client)
    assert res.json["user_code"] == "OTHE-RCOD"

    backend.delete(existing)
    backend.delete(backend.get(models.DeviceCode, device_code=res.json["device_code"]))
