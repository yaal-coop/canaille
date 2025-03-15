import json
from unittest import mock

from canaille.commands import cli


def test_dump_stdout(testclient, backend, user, client, trusted_client, consent, token):
    """Test the full database dump command."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["dump"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert {
        "audience": [
            trusted_client.id,
        ],
        "client_id": mock.ANY,
        "client_id_issued_at": mock.ANY,
        "client_name": "Some other client",
        "client_secret": mock.ANY,
        "client_uri": "https://myotherdomain.test",
        "contacts": [
            "contact@myotherdomain.test",
        ],
        "created": mock.ANY,
        "grant_types": [
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        ],
        "id": trusted_client.id,
        "jwks": mock.ANY,
        "last_modified": mock.ANY,
        "logo_uri": "https://myotherdomain.test/logo.webp",
        "policy_uri": "https://myotherdomain.test/policy",
        "post_logout_redirect_uris": [
            "https://myotherdomain.test/disconnected",
        ],
        "redirect_uris": [
            "https://myotherdomain.test/redirect1",
            "https://myotherdomain.test/redirect2",
        ],
        "response_types": [
            "code",
            "token",
            "id_token",
        ],
        "scope": [
            "openid",
            "profile",
            "groups",
        ],
        "token_endpoint_auth_method": "client_secret_basic",
        "tos_uri": "https://myotherdomain.test/tos",
        "trusted": True,
    } in payload["client"]
    assert {
        "audience": [
            client.id,
            trusted_client.id,
        ],
        "client_id": mock.ANY,
        "client_id_issued_at": mock.ANY,
        "client_name": "Some client",
        "client_secret": mock.ANY,
        "client_uri": "https://client.test",
        "contacts": [
            "contact@mydomain.test",
        ],
        "created": mock.ANY,
        "grant_types": [
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        ],
        "id": client.id,
        "jwks": mock.ANY,
        "last_modified": mock.ANY,
        "logo_uri": "https://client.test/logo.webp",
        "policy_uri": "https://client.test/policy",
        "post_logout_redirect_uris": [
            "https://client.test/disconnected",
        ],
        "redirect_uris": [
            "https://client.test/redirect1",
            "https://client.test/redirect2",
        ],
        "response_types": [
            "code",
            "token",
            "id_token",
        ],
        "scope": [
            "openid",
            "email",
            "profile",
            "groups",
            "address",
            "phone",
        ],
        "token_endpoint_auth_method": "client_secret_basic",
        "tos_uri": "https://client.test/tos",
    } in payload["client"]
    assert payload["consent"] == [
        {
            "client": client.id,
            "consent_id": mock.ANY,
            "created": mock.ANY,
            "id": consent.id,
            "issue_date": mock.ANY,
            "last_modified": mock.ANY,
            "scope": [
                "openid",
                "profile",
            ],
            "subject": user.id,
        },
    ]
    assert payload["token"] == [
        {
            "access_token": mock.ANY,
            "audience": [
                client.id,
            ],
            "client": mock.ANY,
            "created": mock.ANY,
            "id": token.id,
            "issue_date": mock.ANY,
            "last_modified": mock.ANY,
            "lifetime": 3600,
            "refresh_token": mock.ANY,
            "scope": [
                "openid",
                "profile",
            ],
            "subject": user.id,
            "token_id": mock.ANY,
        },
    ]
