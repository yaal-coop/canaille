from flask import g


def test_oauth_authorization_server(testclient):
    res = testclient.get("/.well-known/oauth-authorization-server", status=200).json
    assert "https://auth.mydomain.tld" == res["issuer"]
    assert res["ui_locales_supported"] == g.available_language_codes


def test_openid_configuration(testclient):
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "https://auth.mydomain.tld" == res["issuer"]
    assert res["ui_locales_supported"] == g.available_language_codes
