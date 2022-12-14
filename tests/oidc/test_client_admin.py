from canaille.oidc.models import Client


def test_no_logged_no_access(testclient):
    testclient.get("/admin/client", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/client", status=403)


def test_invalid_client_edition(testclient, logged_admin):
    testclient.get("/admin/client/edit/invalid", status=404)


def test_client_list(testclient, client, logged_admin):
    res = testclient.get("/admin/client")
    assert client.client_name in res.text


def test_client_add(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "foobar",
        "contacts": "foo@bar.com",
        "client_uri": "https://foo.bar",
        "redirect_uris": ["https:/foo.bar/callback"],
        "grant_types": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foo.bar/logo.png",
        "tos_uri": "https://foo.bar/tos",
        "policy_uri": "https://foo.bar/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwks_uri": "https://foo.bar/jwks.json",
        "audience": [],
        "preconsent": False,
        "post_logout_redirect_uris": ["https://foo.bar/disconnected"],
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = Client.get(client_id)
    data["audience"] = [client.dn]
    for k, v in data.items():
        client_value = getattr(client, k)
        if k == "scope":
            assert v == " ".join(client_value)
        elif k == "preconsent":
            assert v is False
        elif k == "contacts":
            assert [v] == client_value
        else:
            assert v == client_value
    client.delete()


def test_add_missing_fields(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    res = res.form.submit(status=200, name="action", value="edit")
    assert "The client has not been added. Please check your information." in res


def test_client_edit(testclient, client, logged_admin, other_client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    data = {
        "client_name": "foobar",
        "contacts": "foo@bar.com",
        "client_uri": "https://foo.bar",
        "redirect_uris": ["https:/foo.bar/callback"],
        "grant_types": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foo.bar/logo.png",
        "tos_uri": "https://foo.bar/tos",
        "policy_uri": "https://foo.bar/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwks_uri": "https://foo.bar/jwks.json",
        "audience": [client.dn, other_client.dn],
        "preconsent": True,
        "post_logout_redirect_uris": ["https://foo.bar/disconnected"],
    }
    for k, v in data.items():
        res.forms["clientadd"][k].force_value(v)
    res = (
        res.forms["clientadd"].submit(status=302, name="action", value="edit").follow()
    )

    assert (
        "The client has not been edited. Please check your information." not in res.text
    )
    assert "The client has been edited." in res.text

    client = Client.get(client.dn)
    for k, v in data.items():
        client_value = getattr(client, k)
        if k == "scope":
            assert v == " ".join(client_value)
        elif k == "preconsent":
            assert v is True
        elif k == "contacts":
            assert [v] == client_value
        else:
            assert v == client_value


def test_client_edit_missing_fields(testclient, client, logged_admin, other_client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientadd"]["client_name"] = ""
    res = res.forms["clientadd"].submit(name="action", value="edit")
    assert "The client has not been edited. Please check your information." in res
    client.reload()
    assert client.client_name


def test_client_delete(testclient, logged_admin):
    client = Client(client_id="client_id")
    client.save()

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientadd"].submit(name="action", value="delete").follow()

    assert not Client.get(client.client_id)


def test_invalid_request(testclient, logged_admin, client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientadd"].submit(name="action", value="invalid", status=400)


def test_client_edit_preauth(testclient, client, logged_admin, other_client):
    assert not client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientadd"]["preconsent"] = True
    res = res.forms["clientadd"].submit(name="action", value="edit").follow()

    assert "The client has been edited." in res.text
    client = Client.get(client.dn)
    assert client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientadd"]["preconsent"] = False
    res = res.forms["clientadd"].submit(name="action", value="edit").follow()

    assert "The client has been edited." in res.text
    client = Client.get(client.dn)
    assert not client.preconsent
