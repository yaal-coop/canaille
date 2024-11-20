"""Tests the behavior of Canaille depending on the OIDC 'prompt' parameter.

https://openid.net/specs/openid-connect-core-1_0.html#AuthorizationEndpoint
"""

import datetime
import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from flask import url_for

from canaille.app import models
from canaille.core.endpoints.account import RegistrationPayload


def test_prompt_none(testclient, logged_user, client, backend):
    """Nominal case with prompt=none."""
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    backend.delete(consent)


def test_prompt_not_logged(testclient, user, client, backend):
    """Prompt=none should return a login_required error when no user is logged
    in.

    login_required     The Authorization Server requires End-User
    authentication.     This error MAY be returned when the prompt
    parameter value in the     Authentication Request is none, but the
    Authentication Request     cannot be completed without displaying a
    user interface for End-User     authentication.
    """
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "login_required" == res.json.get("error")

    backend.delete(consent)


def test_prompt_no_consent(testclient, logged_user, client):
    """Prompt=none should return a consent_required error when user are logged
    in but have not granted their consent.

    consent_required The Authorization Server requires End-User consent.
    This error MAY be returned when the prompt parameter value in the
    Authentication Request is none, but the Authentication Request
    cannot be completed without displaying a user interface for End-User
    consent.
    """
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "consent_required" == res.json.get("error")


def test_prompt_create_logged(testclient, logged_user, client, backend):
    """If prompt=create and user is already logged in, then go straight to the
    consent page."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])

    backend.delete(consent)


def test_prompt_create_registration_disabled(testclient, trusted_client, smtpd):
    """If prompt=create but Canaille registration is disabled, an error
    response should be returned.

    If the OpenID Provider receives a prompt value that it does not
    support (not declared in the prompt_values_supported metadata field)
    the OP SHOULD respond with an HTTP 400 (Bad Request) status code and
    an error value of invalid_request. It is RECOMMENDED that the OP
    return an error_description value identifying the invalid parameter
    value.
    """
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=trusted_client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
        ),
        status=400,
    )
    assert res.json == {
        "error": "invalid_request",
        "error_description": "prompt 'create' value is not supported",
    }


def test_prompt_create_not_logged(testclient, trusted_client, smtpd):
    """If prompt=create and user is not logged in, then display the
    registration form.

    Check that the user is correctly redirected to the client page after
    the registration process.
    """
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=trusted_client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="create",
        ),
    )

    # Display the registration form
    res = res.follow()
    res.form["email"] = "foo@bar.test"
    res = res.form.submit()

    # Checks the registration mail is sent
    assert len(smtpd.messages) == 1

    # Simulate a click on the validation link in the mail
    payload = RegistrationPayload(
        creation_date_isoformat=datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        user_name="",
        user_name_editable=True,
        email="foo@bar.test",
        groups=[],
    )
    registration_url = url_for(
        "core.account.registration",
        data=payload.b64(),
        hash=payload.build_hash(),
        _external=True,
    )

    # Fill the user creation form
    res = testclient.get(registration_url)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res = res.form.submit()

    assert res.flashes == [
        ("success", "Your account has been created successfully."),
    ]

    # Return to the client
    res = res.follow()
    assert res.location.startswith(trusted_client.redirect_uris[0])
