import datetime
import logging
from unittest import mock

import pytest
import wtforms
from babel.dates import LOCALTZ
from flask import current_app
from flask_wtf import FlaskForm
from werkzeug.datastructures import ImmutableMultiDict

from canaille.app.forms import BoundCSRF
from canaille.app.forms import DateTimeUTCField
from canaille.app.forms import IDToModel
from canaille.app.forms import compromised_password_validator
from canaille.app.forms import password_length_validator
from canaille.app.forms import password_too_long_validator
from canaille.app.forms import phone_number
from canaille.core.endpoints.forms import build_profile_form
from tests.htmx import fieldlist_add
from tests.htmx import fieldlist_remove
from tests.htmx import htmx_headers


def test_datetime_utc_field_no_timezone_is_local_timezone(testclient):
    """Test that DateTimeUTCField uses local timezone when no timezone is configured."""
    current_app.config["CANAILLE"]["TIMEZONE"] = None

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.UTC)
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
    """Test that DateTimeUTCField correctly handles UTC timezone configuration."""
    current_app.config["CANAILLE"]["TIMEZONE"] = "UTC"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.UTC)
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
    """Test that DateTimeUTCField correctly handles Japan timezone with UTC conversion."""
    current_app.config["CANAILLE"]["TIMEZONE"] = "Japan"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.UTC)
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
    """Test that DateTimeUTCField falls back to local timezone when configured with invalid timezone."""
    current_app.config["CANAILLE"]["TIMEZONE"] = "invalid"

    class TestForm(wtforms.Form):
        dt = DateTimeUTCField()

    form = TestForm()
    form.validate()
    assert form.dt.data is None

    utc_date = datetime.datetime(2023, 6, 1, 12, tzinfo=datetime.UTC)
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


def test_fieldlist_add_readonly(testclient, logged_user, backend):
    """A readonly fieldlist has no add button, and a forged click adds nothing."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].append("phone_numbers")
    backend.reload(logged_user)

    res = testclient.get("/profile/user")
    form = res.forms["profileform"]
    assert "readonly" in form["phone_numbers-0"].attrs
    assert "phone_numbers-1" not in form.fields
    assert "add_phone_numbers" not in form.fields

    data = {
        "csrf_token": form["csrf_token"].value,
        "family_name": form["family_name"].value,
        "phone_numbers-0": form["phone_numbers-0"].value,
        **fieldlist_add("phone_numbers"),
    }
    res = testclient.post("/profile/user", data, status=400)
    res.mustcontain(no="phone_numbers-1")


def test_fieldlist_remove_readonly(testclient, logged_user, backend):
    """A readonly fieldlist has no remove button, and a forged click removes nothing."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("phone_numbers")
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].append("phone_numbers")
    backend.reload(logged_user)

    logged_user.phone_numbers = ["555-555-000", "555-555-111"]
    backend.save(logged_user)

    res = testclient.get("/profile/user")
    form = res.forms["profileform"]
    assert "readonly" in form["phone_numbers-0"].attrs
    assert "readonly" in form["phone_numbers-1"].attrs
    assert "del_phone_numbers" not in form.fields

    data = {
        "csrf_token": form["csrf_token"].value,
        "family_name": form["family_name"].value,
        "phone_numbers-0": form["phone_numbers-0"].value,
        **fieldlist_remove("phone_numbers"),
    }
    testclient.post("/profile/user", data, status=400)
    backend.reload(logged_user)
    assert logged_user.phone_numbers == ["555-555-000", "555-555-111"]


def test_phone_number_validator():
    """Test that phone number validator accepts various valid formats and rejects invalid ones."""

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


def test_minimum_password_length_config(testclient):
    """Test that password length validator respects MIN_PASSWORD_LENGTH configuration."""

    class Field:
        def __init__(self, data):
            self.data = data

    current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"] = 20
    password_length_validator(None, Field("12345678901234567890"))

    with pytest.raises(wtforms.ValidationError):
        password_length_validator(None, Field("1234567890123456789"))

    current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"] = 8
    password_length_validator(None, Field("12345678"))

    with pytest.raises(wtforms.ValidationError):
        password_length_validator(None, Field("1234567"))
    with pytest.raises(wtforms.ValidationError):
        password_length_validator(None, Field("1"))

    current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"] = 0
    password_length_validator(None, Field(""))

    current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"] = None
    password_length_validator(None, Field(""))


def test_password_strength_progress_bar(testclient, logged_user):
    """Test that password strength progress bar displays correctly in HTMX response."""
    res = testclient.get("/profile/user/auth/password")
    res = testclient.post(
        "/profile/user/auth/password",
        {
            "csrf_token": res.form["csrf_token"].value,
            "password1": "i'm a little pea",
        },
        headers=htmx_headers("password1"),
    )
    res.mustcontain('data-percent="100"')


def test_maximum_password_length_config(testclient):
    """Test that password length validator respects MAX_PASSWORD_LENGTH configuration with defaults."""

    class Field:
        def __init__(self, data):
            self.data = data

    password_too_long_validator(None, Field("a" * 1000))
    with pytest.raises(wtforms.ValidationError):
        password_too_long_validator(None, Field("a" * 1001))

    current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] = 500
    password_too_long_validator(None, Field("a" * 500))
    with pytest.raises(wtforms.ValidationError):
        password_too_long_validator(None, Field("a" * 501))

    current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] = None
    password_too_long_validator(None, Field("a" * 4096))
    with pytest.raises(wtforms.ValidationError):
        password_too_long_validator(None, Field("a" * 4097))

    current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] = 0
    password_too_long_validator(None, Field("a" * 4096))
    with pytest.raises(wtforms.ValidationError):
        password_too_long_validator(None, Field("a" * 4097))

    current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] = 5000
    password_too_long_validator(None, Field("a" * 4096))
    with pytest.raises(wtforms.ValidationError):
        password_too_long_validator(None, Field("a" * 4097))


@mock.patch("httpx2.Client.get")
def test_compromised_password_validator(api_get, testclient):
    """Test that compromised password validator checks against HIBP API and rejects compromised passwords."""
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True

    # This content simulates a result from the hibp api containing the suffixes of the following password hashes: 'password', '987654321', 'correct horse battery staple', 'zxcvbn123', 'azertyuiop123'
    class Response:
        content = b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:3\r\nCAA6D483CC3887DCE9D1B8EB91408F1EA7A:3\r\nAD6438836DBE526AA231ABDE2D0EEF74D42:3\r\n8289894DDB6317178960AB5AE98B81BBF97:1\r\n5FF0B6F9EAC40D5CA7B4DAA7B64F0E6F4AA:2\r\n"

    api_get.return_value = Response

    class Field:
        def __init__(self, data):
            self.data = data

    compromised_password_validator(None, Field("i'm a little pea"))
    compromised_password_validator(None, Field("i'm a little chickpea"))
    compromised_password_validator(None, Field("i'm singing in the rain"))
    with pytest.raises(wtforms.ValidationError):
        compromised_password_validator(None, Field("password"))
    with pytest.raises(wtforms.ValidationError):
        compromised_password_validator(None, Field("987654321"))
    with pytest.raises(wtforms.ValidationError):
        compromised_password_validator(None, Field("correct horse battery staple"))
    with pytest.raises(wtforms.ValidationError):
        compromised_password_validator(None, Field("zxcvbn123"))
    with pytest.raises(wtforms.ValidationError):
        compromised_password_validator(None, Field("azertyuiop123"))

    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = False
    assert compromised_password_validator(None, Field("password")) is None


@mock.patch("httpx2.Client.get")
def test_compromised_password_validator_with_failure_of_api_request_without_form_validation(
    api_get, testclient, logged_user, caplog
):
    """Test that compromised password validation fails gracefully when HIBP API request fails during inline validation."""
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())

    res = testclient.get("/profile/user/auth/password")
    res = testclient.post(
        "/profile/user/auth/password",
        {
            "csrf_token": res.form["csrf_token"].value,
            "password1": "correct horse battery staple",
        },
        headers=htmx_headers("password1"),
    )

    res.mustcontain('data-percent="100"')

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) not in caplog.record_tuples


def test_readonly_fields_do_not_leak_between_forms(testclient):
    """A field set readonly in one form stays writable in the next one."""
    readonly_form = build_profile_form({"family_name"}, {"family_name", "title"})
    writable_form = build_profile_form(
        {"family_name", "title"}, {"family_name", "title"}
    )

    assert "readonly" in readonly_form["title"].render_kw
    assert "readonly" not in writable_form["title"].render_kw


def test_build_profile_form_keeps_the_given_field_names(testclient):
    """Building a profile form does not change the field names it is given."""
    write_field_names = {"family_name", "password", "photo"}
    build_profile_form(write_field_names, set())

    assert write_field_names == {"family_name", "password", "photo"}


def test_id_to_model_with_unknown_identifier(testclient, backend):
    """IDToModel raises a validation error when no model matches the identifier."""
    with pytest.raises(wtforms.ValidationError):
        IDToModel("User")("unknown")

    assert IDToModel("User", raise_on_errors=False)("unknown") is None


class BoundForm(FlaskForm):
    class Meta:
        csrf_class = BoundCSRF
        csrf_bind = ""


def bound_form(bind, token=None):
    formdata = ImmutableMultiDict({"csrf_token": token}) if token else None
    return BoundForm(formdata, meta={"csrf_bind": bind})


def test_bound_csrf_token(testclient):
    """A bound CSRF token is only valid for the same bound value."""
    token = bound_form("foo").csrf_token.current_token

    assert bound_form("foo", token).validate()
    assert not bound_form("bar", token).validate()


def test_bound_csrf_token_tampered(testclient):
    """A bound CSRF token without its signature, or with a wrong one, is invalid."""
    token = bound_form("foo").csrf_token.current_token
    unbound_token, _, signature = token.rpartition(".")

    assert not bound_form("foo", unbound_token).validate()
    assert not bound_form("foo", f"{unbound_token}.{signature[::-1]}").validate()
    assert not bound_form("foo").validate()
