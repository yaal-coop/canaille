import warnings
from datetime import datetime

from canaille.app import models


def test_get(testclient, backend, client, user):
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

    headers = {"Authorization": "Bearer static-token"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=200
    )
    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": int(datetime.timestamp(client.client_id_issued_at)),
        "client_secret_expires_at": 0,
        "redirect_uris": [
            "https://mydomain.test/redirect1",
            "https://mydomain.test/redirect2",
        ],
        "registration_access_token": "static-token",
        "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": [
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
            "client_credentials",
        ],
        "response_types": ["code", "token", "id_token"],
        "client_name": "Some client",
        "client_uri": "https://mydomain.test",
        "logo_uri": "https://mydomain.test/logo.webp",
        "scope": "openid email profile groups address phone",
        "contacts": ["contact@mydomain.test"],
        "tos_uri": "https://mydomain.test/tos",
        "policy_uri": "https://mydomain.test/policy",
        "jwk": None,
        "jwks_uri": "https://mydomain.test/jwk",
        "software_id": None,
        "software_version": None,
    }


def test_update(testclient, backend, client, user):
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

    assert client.redirect_uris != ["https://newname.example.test/callback"]
    assert client.token_endpoint_auth_method != "none"
    assert client.grant_types != ["refresh_token"]
    assert client.response_types != ["code", "token"]
    assert client.client_name != "new name"
    assert client.client_uri != "https://newname.example.test"
    assert client.logo_uri != "https://newname.example.test/logo.webp"
    assert client.scope != ["openid", "profile", "email"]
    assert client.contacts != ["newcontact@example.test"]
    assert client.tos_uri != "https://newname.example.test/tos"
    assert client.policy_uri != "https://newname.example.test/policy"
    assert client.jwks_uri != "https://newname.example.test/my_public_keys.jwks"
    assert client.software_id != "new_software_id"
    assert client.software_version != "3.14"

    payload = {
        "client_id": client.client_id,
        "redirect_uris": ["https://newname.example.test/callback"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["refresh_token"],
        "response_types": ["code", "token"],
        "client_name": "new name",
        "client_uri": "https://newname.example.test",
        "logo_uri": "https://newname.example.test/logo.webp",
        "scope": "openid profile email",
        "contacts": ["newcontact@example.test"],
        "tos_uri": "https://newname.example.test/tos",
        "policy_uri": "https://newname.example.test/policy",
        "jwks_uri": "https://newname.example.test/my_public_keys.jwks",
        "software_id": "new_software_id",
        "software_version": "3.14",
    }

    headers = {"Authorization": "Bearer static-token"}
    res = testclient.put_json(
        f"/oauth/register/{client.client_id}", payload, headers=headers, status=200
    )
    client = backend.get(models.Client, client_id=res.json["client_id"])

    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": int(datetime.timestamp(client.client_id_issued_at)),
        "client_secret_expires_at": 0,
        "redirect_uris": ["https://newname.example.test/callback"],
        "registration_access_token": "static-token",
        "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
        "token_endpoint_auth_method": "none",
        "grant_types": ["refresh_token"],
        "response_types": ["code", "token"],
        "client_name": "new name",
        "client_uri": "https://newname.example.test",
        "logo_uri": "https://newname.example.test/logo.webp",
        "scope": "openid profile email",
        "contacts": ["newcontact@example.test"],
        "tos_uri": "https://newname.example.test/tos",
        "policy_uri": "https://newname.example.test/policy",
        "jwk": None,
        "jwks_uri": "https://newname.example.test/my_public_keys.jwks",
        "software_id": "new_software_id",
        "software_version": "3.14",
    }

    assert client.redirect_uris == ["https://newname.example.test/callback"]
    assert client.token_endpoint_auth_method == "none"
    assert client.grant_types == ["refresh_token"]
    assert client.response_types == ["code", "token"]
    assert client.client_name == "new name"
    assert client.client_uri == "https://newname.example.test"
    assert client.logo_uri == "https://newname.example.test/logo.webp"
    assert client.scope == ["openid", "profile", "email"]
    assert client.contacts == ["newcontact@example.test"]
    assert client.tos_uri == "https://newname.example.test/tos"
    assert client.policy_uri == "https://newname.example.test/policy"
    assert client.jwks_uri == "https://newname.example.test/my_public_keys.jwks"
    assert client.software_id == "new_software_id"
    assert client.software_version == "3.14"


def test_delete(testclient, backend, user):
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

    client = models.Client(client_id="foobar", client_name="Some client")
    backend.save(client)

    headers = {"Authorization": "Bearer static-token"}
    with warnings.catch_warnings(record=True):
        testclient.delete(
            f"/oauth/register/{client.client_id}", headers=headers, status=204
        )
    assert not backend.get(models.Client, client_id=client.client_id)


def test_invalid_client(testclient, backend, user):
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

    payload = {
        "client_id": "invalid-client-id",
        "redirect_uris": ["https://newname.example.test/callback"],
    }

    headers = {"Authorization": "Bearer static-token"}
    res = testclient.put_json(
        "/oauth/register/invalid-client-id", payload, headers=headers, status=401
    )
    assert res.json == {"error": "invalid_client"}
