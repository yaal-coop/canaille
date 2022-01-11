from canaille.oidc.models import Client


def test_no_logged_no_access(testclient):
    testclient.get("/admin/client", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/client", status=403)


def test_invalid_client_edition(testclient, logged_admin):
    testclient.get("/admin/client/edit/invalid", status=404)


def test_client_list(testclient, client, logged_admin):
    res = testclient.get("/admin/client")
    assert client.oauthClientName in res.text


def test_client_add(testclient, logged_admin, slapd_connection):
    res = testclient.get("/admin/client/add")
    data = {
        "oauthClientName": "foobar",
        "oauthClientContact": "foo@bar.com",
        "oauthClientURI": "https://foo.bar",
        "oauthRedirectURIs": ["https:/foo.bar/callback"],
        "oauthGrantType": ["password", "authorization_code"],
        "oauthScope": "openid profile",
        "oauthResponseType": ["code", "token"],
        "oauthTokenEndpointAuthMethod": "none",
        "oauthLogoURI": "https://foo.bar/logo.png",
        "oauthTermsOfServiceURI": "https://foo.bar/tos",
        "oauthPolicyURI": "https://foo.bar/policy",
        "oauthSoftwareID": "software",
        "oauthSoftwareVersion": "1",
        "oauthJWK": "jwk",
        "oauthJWKURI": "https://foo.bar/jwks.json",
        "oauthAudience": [],
        "oauthPreconsent": False,
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["oauthClientID"].value
    client = Client.get(client_id, conn=slapd_connection)
    data["oauthAudience"] = [client.dn]
    for k, v in data.items():
        client_value = getattr(client, k)
        if k == "oauthScope":
            assert v == " ".join(client_value)
        elif k == "oauthPreconsent":
            assert v is False
        else:
            assert v == client_value


def test_client_edit(testclient, client, logged_admin, slapd_connection, other_client):
    res = testclient.get("/admin/client/edit/" + client.oauthClientID)
    data = {
        "oauthClientName": "foobar",
        "oauthClientContact": "foo@bar.com",
        "oauthClientURI": "https://foo.bar",
        "oauthRedirectURIs": ["https:/foo.bar/callback"],
        "oauthGrantType": ["password", "authorization_code"],
        "oauthScope": "openid profile",
        "oauthResponseType": ["code", "token"],
        "oauthTokenEndpointAuthMethod": "none",
        "oauthLogoURI": "https://foo.bar/logo.png",
        "oauthTermsOfServiceURI": "https://foo.bar/tos",
        "oauthPolicyURI": "https://foo.bar/policy",
        "oauthSoftwareID": "software",
        "oauthSoftwareVersion": "1",
        "oauthJWK": "jwk",
        "oauthJWKURI": "https://foo.bar/jwks.json",
        "oauthAudience": [client.dn, other_client.dn],
        "oauthPreconsent": True,
    }
    for k, v in data.items():
        res.forms["clientadd"][k].force_value(v)
    res = res.forms["clientadd"].submit(status=200, name="action", value="edit")

    assert (
        "The client has not been edited. Please check your information." not in res.text
    )

    client = Client.get(client.dn, conn=slapd_connection)
    for k, v in data.items():
        client_value = getattr(client, k)
        if k == "oauthScope":
            assert v == " ".join(client_value)
        elif k == "oauthPreconsent":
            assert v is True
        else:
            assert v == client_value

    res.forms["clientadd"].submit(status=302, name="action", value="delete").follow(
        status=200
    )
    assert Client.get(client.oauthClientID, conn=slapd_connection) is None
