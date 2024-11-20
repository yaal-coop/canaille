from canaille.app import models

# TODO: this test files tests generic features about forms,
# we should rewrite the tests without using specific OIDC
# forms.


def test_fieldlist_add(testclient, logged_admin, backend):
    assert not backend.query(models.Client)

    res = testclient.get("/admin/client/add")
    assert "redirect_uris-1" not in res.form.fields

    data = {
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")
    assert not backend.query(models.Client)

    data["redirect_uris-1"] = "https://foobar.test/callback2"
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.redirect_uris == [
        "https://foobar.test/callback",
        "https://foobar.test/callback2",
    ]

    backend.delete(client)


def test_fieldlist_delete(testclient, logged_admin, backend):
    assert not backend.query(models.Client)
    res = testclient.get("/admin/client/add")

    data = {
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback1",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)
    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")

    res.form["redirect_uris-1"] = "https://foobar.test/callback2"
    res = res.form.submit(status=200, name="fieldlist_remove", value="redirect_uris-1")
    assert not backend.query(models.Client)
    assert "redirect_uris-1" not in res.form.fields

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.redirect_uris == [
        "https://foobar.test/callback1",
    ]

    backend.delete(client)


def test_fieldlist_add_invalid_field(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_add": "invalid",
    }
    testclient.post("/admin/client/add", data, status=400)


def test_fieldlist_delete_invalid_field(testclient, logged_admin, backend):
    assert not backend.query(models.Client)
    res = testclient.get("/admin/client/add")

    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback1",
        "redirect_uris-1": "https://foobar.test/callback2",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_remove": "invalid",
    }
    testclient.post("/admin/client/add", data, status=400)


def test_fieldlist_duplicate_value(testclient, logged_admin, client):
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/samecallback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)
    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")
    res.form["redirect_uris-1"] = "https://foobar.test/samecallback"
    res = res.form.submit(status=200, name="action", value="edit")
    res.mustcontain("This value is a duplicate")


def test_fieldlist_empty_value(testclient, logged_admin, backend):
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/samecallback",
        "post_logout_redirect_uris-0": "https://foobar.test/callback1",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)
    res = res.form.submit(
        status=200, name="fieldlist_add", value="post_logout_redirect_uris-0"
    )
    res.form.submit(status=302, name="action", value="edit")
    client = backend.get(models.Client)
    backend.delete(client)


def test_fieldlist_add_field_htmx(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_add": "redirect_uris-0",
    }
    response = testclient.post(
        "/admin/client/add",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "listfield_add",
        },
    )
    assert 'name="redirect_uris-0' in response.text
    assert 'name="redirect_uris-1' in response.text


def test_fieldlist_add_field_htmx_validation(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "not-a-valid-uri",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_add": "redirect_uris-0",
    }
    response = testclient.post(
        "/admin/client/add",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "listfield_add",
        },
    )
    assert 'name="redirect_uris-0' in response.text
    assert 'name="redirect_uris-1' in response.text
    assert "This is not a valid URL" in response.text


def test_fieldlist_remove_field_htmx(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "https://foobar.test/callback1",
        "redirect_uris-1": "https://foobar.test/callback2",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_remove": "redirect_uris-1",
    }
    response = testclient.post(
        "/admin/client/add",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "listfield_remove",
        },
    )
    assert 'name="redirect_uris-0' in response.text
    assert 'name="redirect_uris-1' not in response.text


def test_fieldlist_inline_validation(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foobar.test",
        "redirect_uris-0": "invalid-url",
        "redirect_uris-1": "https://foobar.test/callback2",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    response = testclient.post(
        "/admin/client/add",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "redirect_uris-0",
        },
    )
    assert 'name="redirect_uris-0' in response.text
    assert 'name="redirect_uris-1' not in response.text
    assert "This is not a valid URL" in response.text
