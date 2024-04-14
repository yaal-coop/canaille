from werkzeug.security import gen_salt

from canaille.app import models


def test_no_logged_no_access(testclient):
    testclient.get("/admin/authorization", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/authorization", status=403)


def test_authorizaton_list(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization")
    res.mustcontain(authorization.authorization_code_id)


def test_authorization_list_pagination(testclient, logged_admin, client, backend):
    res = testclient.get("/admin/authorization")
    res.mustcontain("0 items")
    authorizations = []
    for _ in range(26):
        code = models.AuthorizationCode(
            authorization_code_id=gen_salt(48), client=client, subject=logged_admin
        )
        backend.save(code)
        authorizations.append(code)

    res = testclient.get("/admin/authorization")
    res.mustcontain("26 items")
    authorization_code_id = res.pyquery(
        ".codes tbody tr:nth-of-type(1) td:nth-of-type(1) a"
    ).text()
    assert authorization_code_id

    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    assert authorization_code_id not in res.pyquery(
        ".codes tbody tr td:nth-of-type(1) a"
    ).text().split(" ")
    for authorization in authorizations:
        backend.delete(authorization)

    res = testclient.get("/admin/authorization")
    res.mustcontain("0 items")


def test_authorization_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/authorization")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/authorization",
        {"csrf_token": form["csrf_token"].value, "page": "2"},
        status=404,
    )

    res = testclient.get("/admin/authorization")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/authorization",
        {"csrf_token": form["csrf_token"].value, "page": "-1"},
        status=404,
    )


def test_authorization_list_search(testclient, logged_admin, client, backend):
    id1 = gen_salt(48)
    auth1 = models.AuthorizationCode(
        authorization_code_id=id1, client=client, subject=logged_admin
    )
    backend.save(auth1)

    id2 = gen_salt(48)
    auth2 = models.AuthorizationCode(
        authorization_code_id=id2, client=client, subject=logged_admin
    )
    backend.save(auth2)

    res = testclient.get("/admin/authorization")
    res.mustcontain("2 items")
    res.mustcontain(id1)
    res.mustcontain(id2)

    form = res.forms["search"]
    form["query"] = id1
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(id1)
    res.mustcontain(no=id2)


def test_authorizaton_view(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization/" + authorization.authorization_code_id)
    for attr in authorization.attributes:
        res.mustcontain(attr)
