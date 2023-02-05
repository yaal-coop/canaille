import datetime

from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from werkzeug.security import gen_salt


def test_no_logged_no_access(testclient):
    testclient.get("/admin/client", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/client", status=403)


def test_invalid_client_edition(testclient, logged_admin):
    testclient.get("/admin/client/edit/invalid", status=404)


def test_client_list(testclient, client, logged_admin):
    res = testclient.get("/admin/client")
    assert client.client_name in res.text


def test_client_list_pagination(testclient, logged_admin, client, other_client):
    res = testclient.get("/admin/client")
    assert "2 items" in res
    clients = []
    for _ in range(25):
        client = Client(client_id=gen_salt(48), client_name=gen_salt(48))
        client.save()
        clients.append(client)

    res = testclient.get("/admin/client")
    assert "27 items" in res, res.text
    client_name = res.pyquery(
        ".clients tbody tr:nth-of-type(1) td:nth-of-type(2) a"
    ).text()
    assert client_name

    form = res.forms["next"]
    form["page"] = 2
    res = form.submit()
    assert client_name not in res.pyquery(
        ".clients tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for client in clients:
        client.delete()

    res = testclient.get("/admin/client")
    assert "2 items" in res


def test_client_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/client")
    form = res.forms["next"]
    testclient.post(
        "/admin/client", {"csrf_token": form["csrf_token"], "page": "2"}, status=404
    )

    res = testclient.get("/admin/client")
    form = res.forms["next"]
    testclient.post(
        "/admin/client", {"csrf_token": form["csrf_token"], "page": "-1"}, status=404
    )


def test_client_list_search(testclient, logged_admin, client, other_client):
    res = testclient.get("/admin/client")
    assert "2 items" in res
    assert client.client_name in res
    assert other_client.client_name in res

    form = res.forms["search"]
    form["query"] = "other"
    res = form.submit()

    assert "1 items" in res
    assert other_client.client_name in res
    assert client.client_name not in res


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
    data["audience"] = [client]
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
        "audience": [client.id, other_client.id],
        "preconsent": True,
        "post_logout_redirect_uris": ["https://foo.bar/disconnected"],
    }
    for k, v in data.items():
        res.forms["clientadd"][k].force_value(v)
    res = res.forms["clientadd"].submit(status=302, name="action", value="edit")

    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) not in res.flashes
    assert ("success", "The client has been edited.") in res.flashes

    client = Client.get(client.id)
    data["audience"] = [client, other_client]
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
    token = Token(
        token_id="id", client=client, issue_datetime=datetime.datetime.utcnow()
    )
    token.save()
    consent = Consent(
        consent_id="consent_id", subject=logged_admin, client=client, scope="openid"
    )
    consent.save()
    code = AuthorizationCode(authorization_code_id="id", client=client, subject=client)

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientadd"].submit(name="action", value="delete").follow()

    assert not Client.get()
    assert not Token.get()
    assert not AuthorizationCode.get()
    assert not Consent.get()


def test_client_delete_invalid_client(testclient, logged_admin):
    testclient.post("/admin/client/edit/invalid", {"action": "delete"}, status=404)


def test_invalid_request(testclient, logged_admin, client):
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res = res.forms["clientadd"].submit(name="action", value="invalid", status=400)


def test_client_edit_preauth(testclient, client, logged_admin, other_client):
    assert not client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientadd"]["preconsent"] = True
    res = res.forms["clientadd"].submit(name="action", value="edit")

    assert ("success", "The client has been edited.") in res.flashes
    client = Client.get(client.id)
    assert client.preconsent

    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clientadd"]["preconsent"] = False
    res = res.forms["clientadd"].submit(name="action", value="edit")

    assert ("success", "The client has been edited.") in res.flashes
    client = Client.get(client.id)
    assert not client.preconsent
