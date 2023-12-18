import datetime

import pytest
import wtforms
from babel.dates import LOCALTZ
from flask import current_app
from werkzeug.datastructures import ImmutableMultiDict

from canaille.app.forms import DateTimeUTCField
from canaille.app.forms import phone_number


def test_datetime_utc_field_no_timezone_is_local_timezone(testclient):
    del current_app.config["CANAILLE"]["TIMEZONE"]

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    offset = LOCALTZ.utcoffset(utc_date.replace(tzinfo=None))
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
    current_app.config["CANAILLE"]["TIMEZONE"] = "UTC"

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
    current_app.config["CANAILLE"]["TIMEZONE"] = "Japan"

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
    current_app.config["CANAILLE"]["TIMEZONE"] = "invalid"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.timezone.utc)
    offset = LOCALTZ.utcoffset(utc_date.replace(tzinfo=None))
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


def test_fieldlist_add_readonly(testclient, logged_user):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].append("phone_numbers")
    logged_user.reload()

    res = testclient.get("/profile/user")
    form = res.forms["baseform"]
    assert "readonly" in form["phone_numbers-0"].attrs
    assert "phone_numbers-1" not in form.fields

    data = {
        "csrf_token": form["csrf_token"].value,
        "family_name": form["family_name"].value,
        "phone_numbers-0": form["phone_numbers-0"].value,
        "fieldlist_add": "phone_numbers-0",
    }
    testclient.post("/profile/user", data, status=403)


def test_fieldlist_remove_readonly(testclient, logged_user):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].append("phone_numbers")
    logged_user.reload()

    logged_user.phone_numbers = ["555-555-000", "555-555-111"]
    logged_user.save()

    res = testclient.get("/profile/user")
    form = res.forms["baseform"]
    assert "readonly" in form["phone_numbers-0"].attrs
    assert "readonly" in form["phone_numbers-1"].attrs

    data = {
        "csrf_token": form["csrf_token"].value,
        "family_name": form["family_name"].value,
        "phone_numbers-0": form["phone_numbers-0"].value,
        "fieldlist_remove": "phone_numbers-1",
    }
    testclient.post("/profile/user", data, status=403)


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


def test_phone_number_validator():
    class Field:
        def __init__(self, data):
            self.data = data

    phone_number(None, Field("0601060106"))
    phone_number(None, Field("06 01 06 01 06"))
    phone_number(None, Field(" 06 01 06 01 06 "))
    phone_number(None, Field("06-01-06-01-06"))
    phone_number(None, Field("06.01.06.01.06"))
    phone_number(None, Field("+336 01 06 01 06 "))
    phone_number(None, Field("555-000-555"))

    with pytest.raises(wtforms.ValidationError):
        phone_number(None, Field("invalid"))
