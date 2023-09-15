from flask import g


def test_index(testclient, user):
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    g.user = user
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    g.user.reload()
    res = testclient.get("/", status=302)
    assert res.location == "/consent/"

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    g.user.reload()
    res = testclient.get("/", status=302)
    assert res.location == "/about"
