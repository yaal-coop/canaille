import datetime

from werkzeug.security import gen_salt

from canaille.app import models


def test_no_logged_no_access(testclient):
    testclient.get("/admin/client", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/client", status=403)


def test_invalid_client_edition(testclient, logged_admin):
    testclient.get("/admin/client/edit/invalid", status=404)


def test_client_list(testclient, client, logged_admin):
    res = testclient.get("/admin/client")
    res.mustcontain(client.client_name)


def test_client_list_pagination(
    testclient, logged_admin, client, trusted_client, backend
):
    res = testclient.get("/admin/client")
    res.mustcontain("2 items")
    clients = []
    for _ in range(25):
        client = models.Client(client_id=gen_salt(48), client_name=gen_salt(48))
        backend.save(client)
        clients.append(client)

    res = testclient.get("/admin/client")
    res.mustcontain("27 items")
    client_name = res.pyquery(
        ".clients tbody tr:nth-of-type(1) td:nth-of-type(2) a"
    ).text()
    assert client_name

    form = res.forms["tableform"]
    res = form.submit(name="form", value="2")
    assert client_name not in res.pyquery(
        ".clients tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for client in clients:
        backend.delete(client)

    res = testclient.get("/admin/client")
    res.mustcontain("2 items")


def test_client_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/client")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/client",
        {"csrf_token": form["csrf_token"].value, "page": "2"},
        status=404,
    )

    res = testclient.get("/admin/client")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/client",
        {"csrf_token": form["csrf_token"].value, "page": "-1"},
        status=404,
    )


def test_client_list_search(testclient, logged_admin, client, trusted_client):
    res = testclient.get("/admin/client")
    res.mustcontain("2 items")
    res.mustcontain(client.client_name)
    res.mustcontain(trusted_client.client_name)

    form = res.forms["search"]
    form["query"] = "other"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(trusted_client.client_name)
    res.mustcontain(no=client.client_name)


def test_client_add(testclient, logged_admin, backend):
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "foobar",
        "contacts-0": "foo@bar.test",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback",
        "grant_types": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foobar.test/logo.webp",
        "tos_uri": "https://foobar.test/tos",
        "policy_uri": "https://foobar.test/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwks_uri": "https://foobar.test/jwks.json",
        "audience": [],
        "preconsent": False,
        "post_logout_redirect_uris-0": "https://foobar.test/disconnected",
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="add")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.client_name == "foobar"
    assert client.contacts == ["foo@bar.test"]
    assert client.client_uri == "https://foobar.test"
    assert client.redirect_uris == ["https://foobar.test/callback"]
    assert client.grant_types == ["password", "authorization_code"]
    assert client.scope == ["openid", "profile"]
    assert client.response_types == ["code", "token"]
    assert client.token_endpoint_auth_method == "none"
    assert client.logo_uri == "https://foobar.test/logo.webp"
    assert client.tos_uri == "https://foobar.test/tos"
    assert client.policy_uri == "https://foobar.test/policy"
    assert client.software_id == "software"
    assert client.software_version == "1"
    assert client.jwk == "jwk"
    assert client.jwks_uri == "https://foobar.test/jwks.json"
    assert client.audience == [client]
    assert not client.preconsent
    assert client.post_logout_redirect_uris == ["https://foobar.test/disconnected"]

    backend.delete(client)


def test_add_missing_fields(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    res = res.form.submit(status=200, name="action", value="edit")
    assert (
        "error",
        "The client has not been added. Please check your information.",
    ) in res.flashes


def test_client_edit(testclient, client, logged_admin, trusted_client, backend):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    data = {
        "client_name": "foobar",
        "contacts-0": "foo@bar.test",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback",
        "grant_types": ["password", "authorization_code"],
        "scope": "openid profile",
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "logo_uri": "https://foobar.test/logo.webp",
        "tos_uri": "https://foobar.test/tos",
        "policy_uri": "https://foobar.test/policy",
        "software_id": "software",
        "software_version": "1",
        "jwk": "jwk",
        "jwks_uri": "https://foobar.test/jwks.json",
        "audience": [client.id, trusted_client.id],
        "preconsent": True,
        "post_logout_redirect_uris-0": "https://foobar.test/disconnected",
    }
    for k, v in data.items():
        res.forms["clientaddform"][k].force_value(v)
    res = res.forms["clientaddform"].submit(status=302, name="action", value="edit")

    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) not in res.flashes
    assert ("success", "The client has been edited.") in res.flashes

    backend.reload(client)

    assert client.client_name == "foobar"
    assert client.contacts == ["foo@bar.test"]
    assert client.client_uri == "https://foobar.test"
    assert client.redirect_uris == [
        "https://foobar.test/callback",
        "https://mydomain.test/redirect2",
    ]
    assert client.grant_types == ["password", "authorization_code"]
    assert client.scope == ["openid", "profile"]
    assert client.response_types == ["code", "token"]
    assert client.token_endpoint_auth_method == "none"
    assert client.logo_uri == "https://foobar.test/logo.webp"
    assert client.tos_uri == "https://foobar.test/tos"
    assert client.policy_uri == "https://foobar.test/policy"
    assert client.software_id == "software"
    assert client.software_version == "1"
    assert client.jwk == "jwk"
    assert client.jwks_uri == "https://foobar.test/jwks.json"
    assert client.audience == [client, trusted_client]
    assert not client.preconsent
    assert client.post_logout_redirect_uris == ["https://foobar.test/disconnected"]


def test_client_edit_missing_fields(
    testclient, client, logged_admin, trusted_client, backend
):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientaddform"]["client_name"] = ""
    res = res.forms["clientaddform"].submit(name="action", value="edit")
    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) in res.flashes
    backend.reload(client)
    assert client.client_name


def test_client_delete(testclient, logged_admin, backend):
    client = models.Client(client_id="client_id")
    backend.save(client)
    token = models.Token(
        token_id="id",
        client=client,
        subject=logged_admin,
        issue_date=datetime.datetime.now(datetime.timezone.utc),
    )
    backend.save(token)
    consent = models.Consent(
        consent_id="consent_id", subject=logged_admin, client=client, scope=["openid"]
    )
    backend.save(consent)
    authorization_code = models.AuthorizationCode(
        authorization_code_id="id", client=client, subject=logged_admin
    )
    backend.save(authorization_code)

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientaddform"].submit(name="action", value="confirm-delete")
    res = res.form.submit(name="action", value="delete")
    res = res.follow()

    assert not backend.get(models.Client)
    assert not backend.get(models.Token)
    assert not backend.get(models.AuthorizationCode)
    assert not backend.get(models.Consent)


def test_client_delete_invalid_client(testclient, logged_admin, client):
    res = testclient.get(f"/admin/client/edit/{client.client_id}")
    testclient.post(
        "/admin/client/edit/invalid",
        {
            "action": "delete",
            "csrf_token": res.forms["clientaddform"]["csrf_token"].value,
        },
        status=404,
    )


def test_client_edit_preauth(testclient, client, logged_admin, trusted_client, backend):
    assert not client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientaddform"]["preconsent"] = True
    res = res.forms["clientaddform"].submit(name="action", value="edit")

    assert ("success", "The client has been edited.") in res.flashes
    backend.reload(client)
    assert client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientaddform"]["preconsent"] = False
    res = res.forms["clientaddform"].submit(name="action", value="edit")

    assert ("success", "The client has been edited.") in res.flashes
    backend.reload(client)
    assert not client.preconsent


def test_client_edit_invalid_uri(testclient, client, logged_admin, trusted_client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientaddform"]["client_uri"] = "invalid"
    res = res.forms["clientaddform"].submit(status=200, name="action", value="edit")
    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) in res.flashes
    res.mustcontain("This is not a valid URL")


def test_client_new_token(testclient, logged_admin, backend, client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientaddform"].submit(name="action", value="new-token")
    assert (
        "success",
        "A token have been created for the client Some client",
    ) in res.flashes

    token = backend.get(models.Token)
    assert token.client == client
    assert not token.subject
    assert token.type == "access_token"
    assert token.scope == client.scope
    assert client in token.audience

    res = res.follow()
    assert res.template == "oidc/token_view.html"
