import datetime

import wtforms
from babel.dates import LOCALTZ
from canaille.app import models
from canaille.app.forms import DateTimeUTCField
from flask import current_app
from werkzeug.datastructures import ImmutableMultiDict


def test_datetime_utc_field_no_timezone_is_local_timezone(testclient):
    del current_app.config["TIMEZONE"]

    offset = LOCALTZ.utcoffset(datetime.datetime.utcnow())

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    locale_date = datetime.datetime(2023, 6, 1, 12) + offset
    rendered_locale_date = locale_date.strftime("%Y-%m-%d %H:%M:%S")
    rendered_locale_date_form = locale_date.strftime("%Y-%m-%d %H:%M:%S")

    request_form = ImmutableMultiDict({"dt": rendered_locale_date_form})
    form = TestForm(request_form)
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date_form}">'
    )

    form = TestForm(data={"dt": utc_date})
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )

    class Foobar:
        dt = utc_date

    form = TestForm(obj=Foobar())
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )


def test_datetime_utc_field_utc(testclient):
    current_app.config["TIMEZONE"] = "UTC"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    rendered_date = date.strftime("%Y-%m-%d %H:%M:%S")
    rendered_date_form = date.strftime("%Y-%m-%d %H:%M:%S")

    request_form = ImmutableMultiDict({"dt": rendered_date_form})
    form = TestForm(request_form)
    assert form.validate()
    assert form.dt.data == date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_date_form}">'
    )

    form = TestForm(data={"dt": date})
    assert form.validate()
    assert form.dt.data == date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_date}">'
    )

    class Foobar:
        dt = date

    form = TestForm(obj=Foobar())
    assert form.validate()
    assert form.dt.data == date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_date}">'
    )


def test_datetime_utc_field_japan_timezone(testclient):
    current_app.config["TIMEZONE"] = "Japan"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    locale_date = datetime.datetime(2023, 6, 1, 21)
    rendered_locale_date = locale_date.strftime("%Y-%m-%d %H:%M:%S")
    rendered_locale_date_form = locale_date.strftime("%Y-%m-%d %H:%M:%S")

    request_form = ImmutableMultiDict({"dt": rendered_locale_date_form})
    form = TestForm(request_form)
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date_form}">'
    )

    form = TestForm(data={"dt": utc_date})
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )

    class Foobar:
        dt = utc_date

    form = TestForm(obj=Foobar())
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )


def test_datetime_utc_field_invalid_timezone(testclient):
    current_app.config["TIMEZONE"] = "invalid"

    offset = LOCALTZ.utcoffset(datetime.datetime.utcnow())

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    locale_date = datetime.datetime(2023, 6, 1, 12) + offset
    rendered_locale_date = locale_date.strftime("%Y-%m-%d %H:%M:%S")
    rendered_locale_date_form = locale_date.strftime("%Y-%m-%d %H:%M:%S")

    request_form = ImmutableMultiDict({"dt": rendered_locale_date_form})
    form = TestForm(request_form)
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date_form}">'
    )

    form = TestForm(data={"dt": utc_date})
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )

    class Foobar:
        dt = utc_date

    form = TestForm(obj=Foobar())
    assert form.validate()
    assert form.dt.data == utc_date
    assert (
        form.dt()
        == f'<input id="dt" name="dt" type="datetime-local" value="{rendered_locale_date}">'
    )


def test_fieldlist_add(testclient, logged_admin):
    assert not models.Client.query()

    res = testclient.get("/admin/client/add")
    assert "redirect_uris-1" not in res.form.fields

    data = {
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")
    assert not models.Client.query()

    data["redirect_uris-1"] = "https://foo.bar/callback2"
    for k, v in data.items():
        res.form[k].force_value(v)

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = models.Client.get(client_id=client_id)

    assert client.redirect_uris == [
        "https://foo.bar/callback",
        "https://foo.bar/callback2",
    ]

    client.delete()


def test_fieldlist_delete(testclient, logged_admin):
    assert not models.Client.query()
    res = testclient.get("/admin/client/add")

    data = {
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback1",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)
    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")

    res.form["redirect_uris-1"] = "https://foo.bar/callback2"
    res = res.form.submit(status=200, name="fieldlist_remove", value="redirect_uris-1")
    assert not models.Client.query()
    assert "redirect_uris-1" not in res.form.fields

    res = res.form.submit(status=302, name="action", value="edit")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = models.Client.get(client_id=client_id)

    assert client.redirect_uris == [
        "https://foo.bar/callback1",
    ]

    client.delete()


def test_fieldlist_add_invalid_field(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
        "fieldlist_add": "invalid",
    }
    testclient.post("/admin/client/add", data, status=400)


def test_fieldlist_delete_invalid_field(testclient, logged_admin):
    assert not models.Client.query()
    res = testclient.get("/admin/client/add")

    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback1",
        "redirect_uris-1": "https://foo.bar/callback2",
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
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/samecallback",
        "grant_types": ["password", "authorization_code"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "none",
    }
    for k, v in data.items():
        res.form[k].force_value(v)
    res = res.form.submit(status=200, name="fieldlist_add", value="redirect_uris-0")
    res.form["redirect_uris-1"] = "https://foo.bar/samecallback"
    res = res.form.submit(status=200, name="action", value="edit")
    res.mustcontain("This value is a duplicate")


def test_fieldlist_empty_value(testclient, logged_admin, client):
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/samecallback",
        "post_logout_redirect_uris-0": "https://foo.bar/callback1",
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
    client = models.Client.get()
    client.delete()


def test_fieldlist_add_field_htmx(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback",
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
        "client_uri": "https://foo.bar",
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
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "https://foo.bar/callback1",
        "redirect_uris-1": "https://foo.bar/callback2",
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


def test_fieldlist_add_readonly(testclient, logged_user, configuration):
    configuration["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    configuration["ACL"]["DEFAULT"]["READ"].append("phone_numbers")

    res = testclient.get("/profile/user")
    assert res.form["phone_numbers-0"].attrs["readonly"]
    assert "phone_numbers-1" not in res.form.fields

    data = {
        "csrf_token": res.form["csrf_token"].value,
        "family_name": res.form["family_name"].value,
        "phone_numbers-0": res.form["phone_numbers-0"].value,
        "fieldlist_add": "phone_numbers-0",
    }
    testclient.post("/profile/user", data, status=403)


def test_fieldlist_remove_readonly(testclient, logged_user, configuration):
    configuration["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    configuration["ACL"]["DEFAULT"]["READ"].append("phone_numbers")
    logged_user.phone_numbers = ["555-555-000", "555-555-111"]
    logged_user.save()

    res = testclient.get("/profile/user")
    assert res.form["phone_numbers-0"].attrs["readonly"]
    assert res.form["phone_numbers-1"].attrs["readonly"]

    data = {
        "csrf_token": res.form["csrf_token"].value,
        "family_name": res.form["family_name"].value,
        "phone_numbers-0": res.form["phone_numbers-0"].value,
        "fieldlist_remove": "phone_numbers-1",
    }
    testclient.post("/profile/user", data, status=403)


def test_fieldlist_inline_validation(testclient, logged_admin):
    res = testclient.get("/admin/client/add")
    data = {
        "csrf_token": res.form["csrf_token"].value,
        "client_name": "foobar",
        "client_uri": "https://foo.bar",
        "redirect_uris-0": "invalid-url",
        "redirect_uris-1": "https://foo.bar/callback2",
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


def test_inline_validation_invalid_field(testclient, logged_admin, user):
    res = testclient.get("/profile")
    testclient.post(
        "/profile",
        {
            "csrf_token": res.form["csrf_token"].value,
            "email": "john@doe.com",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "invalid-field",
        },
        status=400,
    )
