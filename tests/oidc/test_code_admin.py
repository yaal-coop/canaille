from canaille.oidc.models import AuthorizationCode
from werkzeug.security import gen_salt


def test_no_logged_no_access(testclient):
    testclient.get("/admin/authorization", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/authorization", status=403)


def test_authorizaton_list(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization")
    assert authorization.authorization_code_id in res.text


def test_authorization_list_pagination(testclient, logged_admin, client):
    res = testclient.get("/admin/authorization")
    assert "0 items" in res
    authorizations = []
    for _ in range(26):
        code = AuthorizationCode(
            authorization_code_id=gen_salt(48), client=client, subject=client
        )
        code.save()
        authorizations.append(code)

    res = testclient.get("/admin/authorization")
    assert "26 items" in res, res.text
    authorization_code_id = res.pyquery(
        ".codes tbody tr:nth-of-type(1) td:nth-of-type(1) a"
    ).text()
    assert authorization_code_id

    form = res.forms["next"]
    form["page"] = 2
    res = form.submit()
    assert authorization_code_id not in res.pyquery(
        ".codes tbody tr td:nth-of-type(1) a"
    ).text().split(" ")
    for authorization in authorizations:
        authorization.delete()

    res = testclient.get("/admin/authorization")
    assert "0 items" in res


def test_authorization_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/authorization")
    form = res.forms["next"]
    testclient.post(
        "/admin/authorization",
        {"csrf_token": form["csrf_token"], "page": "2"},
        status=404,
    )

    res = testclient.get("/admin/authorization")
    form = res.forms["next"]
    testclient.post(
        "/admin/authorization",
        {"csrf_token": form["csrf_token"], "page": "-1"},
        status=404,
    )


def test_authorization_list_search(testclient, logged_admin, client):
    id1 = gen_salt(48)
    auth1 = AuthorizationCode(authorization_code_id=id1, client=client, subject=client)
    auth1.save()

    id2 = gen_salt(48)
    auth2 = AuthorizationCode(authorization_code_id=id2, client=client, subject=client)
    auth2.save()

    res = testclient.get("/admin/authorization")
    assert "2 items" in res
    assert id1 in res
    assert id2 in res

    form = res.forms["search"]
    form["query"] = id1
    res = form.submit()

    assert "1 items" in res
    assert id1 in res
    assert id2 not in res


def test_authorizaton_view(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization/" + authorization.authorization_code_id)
    for attr in authorization.may() + authorization.must():
        assert attr in res.text
