import json

from canaille.app import models
from canaille.commands import cli


def test_restore_stdin(testclient, backend):
    """Test the full database dump command."""
    payload = {
        "client": [
            {
                "id": "45fb7f55-816a-41bf-a9f0-16bb1d60f448",
                "created": "2025-03-15T12:55:32+00:00",
                "last_modified": "2025-03-15T12:55:32+00:00",
                "trusted": True,
                "audience": ["45fb7f55-816a-41bf-a9f0-16bb1d60f448"],
                "client_id": "dx8HWLJOM2GRQtkR92fjwHZ7",
                "client_secret": "1pwUfTGWJCsvPVJdoNyMZIJiQuUEO6KBX5HA49G8OTsAtdXY",
                "client_id_issued_at": "2025-03-15T12:55:32.745494+00:00",
                "redirect_uris": [
                    "https://myotherdomain.test/redirect1",
                    "https://myotherdomain.test/redirect2",
                ],
                "token_endpoint_auth_method": "client_secret_basic",
                "grant_types": [
                    "password",
                    "authorization_code",
                    "implicit",
                    "hybrid",
                    "refresh_token",
                    "client_credentials",
                    "urn:ietf:params:oauth:grant-type:jwt-bearer",
                ],
                "response_types": ["code", "token", "id_token"],
                "client_name": "Some other client",
                "client_uri": "https://myotherdomain.test",
                "logo_uri": "https://myotherdomain.test/logo.webp",
                "scope": ["openid", "profile", "groups"],
                "contacts": ["contact@myotherdomain.test"],
                "tos_uri": "https://myotherdomain.test/tos",
                "policy_uri": "https://myotherdomain.test/policy",
                "jwks": '{"keys": [{"n": "02uEn7s1vpHLEwNRV-5mQn0W-N--KhPoFuJ28NoRuGGBVoFmCLxnd70qdqu_8tQRuu6R65566PGiDLavkbNqe0cFZB7VSk2vnhpfJGLzUo_FYQeSK-XafnfIiuhd1IdCG6-ck7YfKJMnfqpQW_hFnq-k1SXkZVhcEsYtZ-wtXfa3hiTPrT4oFzEf0gAAvluaTTKOXaGELo-8NDv4HycQPzWLSvpAqtAEyVo_pjfAUrdDTaNPtiQG1-ISrx3UKxji0Wmt8oaJyOABQ0y3dpvT5EyvWfkooOjlebK4dI-a8ZmSU6ev_x3-HWy-9W3wkWiBCscBgiR_vmd1dCz2RF9QVQ", "e": "AQAB", "kty": "RSA", "kid": "xrELM5bzoeSWozMrhtcrLKnmx3ZGGjycukSee3_zyks"}]}',
                "post_logout_redirect_uris": [
                    "https://myotherdomain.test/disconnected"
                ],
            },
            {
                "id": "83eff494-ea5d-490e-b044-c5bcef518979",
                "created": "2025-03-15T12:55:32+00:00",
                "last_modified": "2025-03-15T12:55:32+00:00",
                "audience": [
                    "83eff494-ea5d-490e-b044-c5bcef518979",
                    "45fb7f55-816a-41bf-a9f0-16bb1d60f448",
                ],
                "client_id": "M2yzGYiZgilOvQdc8vCLyzrb",
                "client_secret": "tx22iqvdPpUBA4o8fFdGUc5jxR4596bKcs8ZvSAcLuU3LxvP",
                "client_id_issued_at": "2025-03-15T12:55:32.747508+00:00",
                "redirect_uris": [
                    "https://client.test/redirect1",
                    "https://client.test/redirect2",
                ],
                "token_endpoint_auth_method": "client_secret_basic",
                "grant_types": [
                    "password",
                    "authorization_code",
                    "implicit",
                    "hybrid",
                    "refresh_token",
                    "client_credentials",
                    "urn:ietf:params:oauth:grant-type:jwt-bearer",
                ],
                "response_types": ["code", "token", "id_token"],
                "client_name": "Some client",
                "client_uri": "https://client.test",
                "logo_uri": "https://client.test/logo.webp",
                "scope": ["openid", "email", "profile", "groups", "address", "phone"],
                "contacts": ["contact@mydomain.test"],
                "tos_uri": "https://client.test/tos",
                "policy_uri": "https://client.test/policy",
                "jwks": '{"keys": [{"n": "02uEn7s1vpHLEwNRV-5mQn0W-N--KhPoFuJ28NoRuGGBVoFmCLxnd70qdqu_8tQRuu6R65566PGiDLavkbNqe0cFZB7VSk2vnhpfJGLzUo_FYQeSK-XafnfIiuhd1IdCG6-ck7YfKJMnfqpQW_hFnq-k1SXkZVhcEsYtZ-wtXfa3hiTPrT4oFzEf0gAAvluaTTKOXaGELo-8NDv4HycQPzWLSvpAqtAEyVo_pjfAUrdDTaNPtiQG1-ISrx3UKxji0Wmt8oaJyOABQ0y3dpvT5EyvWfkooOjlebK4dI-a8ZmSU6ev_x3-HWy-9W3wkWiBCscBgiR_vmd1dCz2RF9QVQ", "e": "AQAB", "kty": "RSA", "kid": "xrELM5bzoeSWozMrhtcrLKnmx3ZGGjycukSee3_zyks"}]}',
                "post_logout_redirect_uris": ["https://client.test/disconnected"],
            },
        ],
        "consent": [
            {
                "id": "352d714d-b563-4934-8f74-ef5bba5f4cbd",
                "created": "2025-03-15T12:55:32+00:00",
                "last_modified": "2025-03-15T12:55:32+00:00",
                "consent_id": "9b97bf4c-7689-4ea2-b155-92006d192aa5",
                "subject": "17d7c987-fce0-41c3-ab48-d4de697d28e6",
                "client": "83eff494-ea5d-490e-b044-c5bcef518979",
                "scope": ["openid", "profile"],
                "issue_date": "2025-03-15T12:55:32.749027+00:00",
            }
        ],
        "token": [
            {
                "id": "57834001-55c8-4177-b22b-cbe5e62b7eb8",
                "created": "2025-03-15T12:55:32+00:00",
                "last_modified": "2025-03-15T12:55:32+00:00",
                "token_id": "iS5JFG7Yk7d4kFRUpsMNf85I0N6aCKqvs5fVwjBSKjvqafLZ",
                "access_token": "zOG6d15hkCRSzLfYlDlBvAmZ2HUeOC4FwGZLUCjVsLXE811v",
                "client": "83eff494-ea5d-490e-b044-c5bcef518979",
                "subject": "17d7c987-fce0-41c3-ab48-d4de697d28e6",
                "refresh_token": "2ilgM6qhsyWWWExKXShS9R0Chjjf2ouI72NZYIoswaXWc7iF",
                "scope": ["openid", "profile"],
                "issue_date": "2025-03-15T12:55:32.749713+00:00",
                "lifetime": 3600,
                "audience": ["83eff494-ea5d-490e-b044-c5bcef518979"],
            }
        ],
        "user": [
            {
                "id": "17d7c987-fce0-41c3-ab48-d4de697d28e6",
                "created": "2025-03-15T12:55:32+00:00",
                "last_modified": "2025-03-15T12:55:32+00:00",
                "user_name": "user",
                "password": "correct horse battery staple",
                "preferred_language": "en",
                "family_name": "Doe",
                "given_name": "John",
                "formatted_name": "John (johnny) Doe",
                "display_name": "Johnny",
                "emails": ["john@doe.test"],
                "phone_numbers": ["555-000-000"],
                "formatted_address": "1235, somewhere",
                "profile_url": "https://john.test",
            }
        ],
    }
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["restore"], catch_exceptions=False, input=json.dumps(payload)
    )
    assert res.exit_code == 0, res.stdout

    client1 = backend.get(models.Client, client_id="M2yzGYiZgilOvQdc8vCLyzrb")
    client2 = backend.get(models.Client, client_id="dx8HWLJOM2GRQtkR92fjwHZ7")
    token = backend.get(models.Token)
    consent = backend.get(models.Consent)
    user = backend.get(models.User)
    assert token.client == client1
    assert consent.subject == user

    backend.delete(token)
    backend.delete(consent)
    backend.delete(client1)
    backend.delete(client2)
    backend.delete(user)
