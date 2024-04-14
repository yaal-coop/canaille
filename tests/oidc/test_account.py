from flask import g


def test_index(testclient, user, backend):
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    g.user = user
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    backend.reload(g.user)
    res = testclient.get("/", status=302)
    assert res.location == "/consent/"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(g.user)
    res = testclient.get("/", status=302)
    assert res.location == "/about"
