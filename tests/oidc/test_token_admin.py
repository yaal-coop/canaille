import datetime

from canaille.oidc.models import Token
from werkzeug.security import gen_salt


def test_no_logged_no_access(testclient):
    testclient.get("/admin/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/admin/token")
    assert token.token_id in res.text


def test_token_list_pagination(testclient, logged_admin, client):
    res = testclient.get("/admin/token")
    assert "0 items" in res
    tokens = []
    for _ in range(26):
        token = Token(
            token_id=gen_salt(48),
            access_token="my-valid-token",
            client=client,
            subject=logged_admin,
            type=None,
            refresh_token=gen_salt(48),
            scope="openid profile",
            issue_date=(datetime.datetime.now().replace(microsecond=0)),
            lifetime=3600,
        )
        token.save()
        tokens.append(token)

    res = testclient.get("/admin/token")
    assert "26 items" in res, res.text
    token_id = res.pyquery(".tokens tbody tr td:nth-of-type(1) a").text()
    assert token_id

    form = res.forms["pagination"]
    res = form.submit(name="page", value="2")
    assert (
        token_id
        not in res.pyquery(".tokens tbody tr:nth-of-type(1) td:nth-of-type(1) a").text()
    )
    for token in tokens:
        token.delete()

    res = testclient.get("/admin/token")
    assert "0 items" in res


def test_token_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/token")
    form = res.forms["pagination"]
    testclient.post(
        "/admin/token", {"csrf_token": form["csrf_token"], "page": "2"}, status=404
    )

    res = testclient.get("/admin/token")
    form = res.forms["pagination"]
    testclient.post(
        "/admin/token", {"csrf_token": form["csrf_token"], "page": "-1"}, status=404
    )


def test_token_list_search(testclient, logged_admin, client):
    token1 = Token(
        token_id=gen_salt(48),
        access_token="this-token-is-ok",
        client=client,
        subject=logged_admin,
        type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=(datetime.datetime.now().replace(microsecond=0)),
        lifetime=3600,
    )
    token1.save()
    token2 = Token(
        token_id=gen_salt(48),
        access_token="this-token-is-valid",
        client=client,
        subject=logged_admin,
        type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=(datetime.datetime.now().replace(microsecond=0)),
        lifetime=3600,
    )
    token2.save()

    res = testclient.get("/admin/token")
    assert "2 items" in res
    assert token1.token_id in res
    assert token2.token_id in res

    form = res.forms["search"]
    form["query"] = "valid"
    res = form.submit()

    assert "1 items" in res
    assert token2.token_id in res
    assert token1.token_id not in res


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/admin/token/" + token.token_id)
    assert token.access_token in res.text


def test_token_not_found(testclient, logged_admin):
    res = testclient.get("/admin/token/" + "yolo", status=404)


def test_revoke_token(testclient, token, logged_admin):
    assert not token.revoked

    res = testclient.get(f"/admin/token/{token.token_id}/revoke")
    assert ("success", "The token has successfully been revoked.") in res.flashes

    token.reload()
    assert token.revoked


def test_revoke_invalid_token(testclient, logged_admin):
    testclient.get(f"/admin/token/invalid/revoke", status=404)
