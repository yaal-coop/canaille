from canaille.oidc.models import Client


def test_no_logged_no_access(testclient):
    testclient.get("/admin/client", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/client", status=403)


def test_invalid_client_edition(testclient, logged_admin):
    testclient.get("/admin/client/edit/invalid", status=404)


def test_client_list(testclient, client, logged_admin):
    res = testclient.get("/admin/client")
    assert client.name in res.text


def test_client_add(testclient, logged_admin, slapd_connection):
    res = testclient.get("/admin/client/add")
    data = {
        "name": "foobar",
        "contact": "foo@bar.com",
        "uri": "https://foo.bar",
        "redirect_uris": ["https:/foo.bar/callback"],
        "grant_type": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_type": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foo.bar/logo.png",
        "tos_uri": "https://foo.bar/tos",
        "policy_uri": "https://foo.bar/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwk_uri": "https://foo.bar/jwks.json",
        "audience": [],
        "preconsent": False,
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = Client.get(client_id, conn=slapd_connection)
    data["audience"] = [client.dn]
    for k, v in data.items():
        client_value = getattr(client, k)
        if k == "scope":
            assert v == " ".join(client_value)
        elif k == "preconsent":
            assert v is False
        else:
            assert v == client_value


def test_client_edit(testclient, client, logged_admin, slapd_connection, other_client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    data = {
        "name": "foobar",
        "contact": "foo@bar.com",
        "uri": "https://foo.bar",
        "redirect_uris": ["https:/foo.bar/callback"],
        "grant_type": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_type": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foo.bar/logo.png",
        "tos_uri": "https://foo.bar/tos",
        "policy_uri": "https://foo.bar/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwk_uri": "https://foo.bar/jwks.json",
        "audience": [client.dn, other_client.dn],
        "preconsent": True,
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
        if k == "scope":
            assert v == " ".join(client_value)
        elif k == "preconsent":
            assert v is True
        else:
            assert v == client_value

    res.forms["clientadd"].submit(status=302, name="action", value="delete").follow(
        status=200
    )
    assert Client.get(client.client_id, conn=slapd_connection) is None
