import datetime
import logging

from werkzeug.security import gen_salt

from canaille.app import models


def test_no_logged_no_access(testclient):
    testclient.get("/admin/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/admin/token")
    res.mustcontain(token.token_id)


def test_token_list_pagination(testclient, logged_admin, client, backend):
    res = testclient.get("/admin/token")
    res.mustcontain("0 items")
    tokens = []
    for _ in range(26):
        token = models.Token(
            token_id=gen_salt(48),
            access_token="my-valid-token",
            client=client,
            subject=logged_admin,
            type=None,
            refresh_token=gen_salt(48),
            scope=["openid", "profile"],
            issue_date=(
                datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
            ),
            lifetime=3600,
        )
        backend.save(token)
        tokens.append(token)

    res = testclient.get("/admin/token")
    res.mustcontain("26 items")
    token_id = res.pyquery(".tokens tbody tr td:nth-of-type(1) a").text()
    assert token_id

    form = res.forms["tableform"]
    res = form.submit(name="form", value="2")
    assert token_id not in res.pyquery(
        ".tokens tbody tr:nth-of-type(1) td:nth-of-type(1) a"
    ).text().split(" ")
    for token in tokens:
        backend.delete(token)

    res = testclient.get("/admin/token")
    res.mustcontain("0 items")


def test_token_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/admin/token")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/token",
        {"csrf_token": form["csrf_token"].value, "page": "2"},
        status=404,
    )

    res = testclient.get("/admin/token")
    form = res.forms["tableform"]
    testclient.post(
        "/admin/token",
        {"csrf_token": form["csrf_token"].value, "page": "-1"},
        status=404,
    )


def test_token_list_search(testclient, logged_admin, client, backend):
    token1 = models.Token(
        token_id=gen_salt(48),
        access_token="this-token-is-ok",
        client=client,
        subject=logged_admin,
        type=None,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ),
        lifetime=3600,
    )
    backend.save(token1)
    token2 = models.Token(
        token_id=gen_salt(48),
        access_token="this-token-is-valid",
        client=client,
        subject=logged_admin,
        type=None,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ),
        lifetime=3600,
    )
    backend.save(token2)

    res = testclient.get("/admin/token")
    res.mustcontain("2 items")
    res.mustcontain(token1.token_id)
    res.mustcontain(token2.token_id)

    form = res.forms["search"]
    form["query"] = "valid"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(token2.token_id)
    res.mustcontain(no=token1.token_id)


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/admin/token/" + token.token_id)
    res.mustcontain(token.access_token)


def test_token_not_found(testclient, logged_admin):
    testclient.get("/admin/token/" + "yolo", status=404)


def test_revoke_bad_request(testclient, token, logged_admin):
    assert not token.revoked

    res = testclient.get(f"/admin/token/{token.token_id}")
    res = res.form.submit(name="action", value="invalid", status=400)


def test_revoke_token(testclient, token, logged_admin, backend, caplog):
    assert not token.revoked

    res = testclient.get(f"/admin/token/{token.token_id}")
    res = res.form.submit(name="action", value="confirm-revoke")
    res = res.form.submit(name="action", value="revoke")
    assert ("success", "The token has successfully been revoked.") in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Revoked token for user in client Some client by admin from unknown IP",
    ) in caplog.record_tuples

    backend.reload(token)
    assert token.revoked


def test_revoke_invalid_token(testclient, logged_admin):
    testclient.get("/admin/token/invalid/revoke", status=404)
