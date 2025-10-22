from flask import g

from canaille.app.session import UserSession


def test_index(testclient, user, backend):
    """Test that the index page redirects to the appropriate page based on user authentication and permissions."""
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    g.session = UserSession(user=user)
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    backend.reload(g.session.user)
    res = testclient.get("/", status=302)
    assert res.location == "/consent/"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(g.session.user)
    res = testclient.get("/", status=302)
    assert res.location == "/about"
