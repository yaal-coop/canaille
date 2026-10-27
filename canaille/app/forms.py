import datetime
import hashlib
import math
import re

import wtforms.validators
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtforms_htmx import HtmxFlaskForm
from wtforms_htmx.mutations import list_add
from wtforms_htmx.mutations import list_remove
from wtforms_htmx_components import ComboboxField

from canaille.app import models
from canaille.app.http import http
from canaille.app.i18n import gettext as _
from canaille.app.i18n import timezone_selector
from canaille.app.mails_sending_conditions import check_if_send_mail_to_admins
from canaille.backends import Backend

from . import validate_uri
from .flask import request_is_partial


def is_uri(form, field):
    if not validate_uri(field.data):
        raise wtforms.ValidationError(_("This is not a valid URL"))


def unique_values(form, field):
    values = set()
    for subfield in field:
        if subfield.data in values:
            subfield.errors.append(_("This value is a duplicate"))
            raise wtforms.ValidationError(_("This value is a duplicate"))

        if subfield.data:
            values.add(subfield.data)


def phone_number(form, field):
    number = field.data.replace(" ", "").replace("-", "").replace(".", "")
    if not re.match(
        r"(?P<country_code>\+\d{1,3})?\s?\(?(?P<area_code>\d{1,4})\)?[\s.-]?(?P<local_number>\d{3}[\s.-]?\d{4})",
        number,
    ):
        raise wtforms.ValidationError(_("Not a valid phone number"))


def password_length_validator(form, field):
    minimum_password_length = current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"]
    if minimum_password_length:
        if len(field.data) < minimum_password_length:
            raise wtforms.ValidationError(
                _(
                    "Field must be at least {minimum_password_length} characters long."
                ).format(minimum_password_length=str(minimum_password_length))
            )


def password_too_long_validator(form, field):
    maximum_password_length = min(
        current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] or 4096, 4096
    )
    if len(field.data) > maximum_password_length:
        raise wtforms.ValidationError(
            _(
                "Field cannot be longer than {maximum_password_length} characters."
            ).format(maximum_password_length=str(maximum_password_length))
        )


def password_strength_calculator(password):
    try:
        from zxcvbn_rs_py import zxcvbn
    except ImportError:
        return None

    strength_score = 0

    if password and type(password) is str:
        strength_score = int(zxcvbn(password).score)
        strength_score = strength_score * 100 // 4

    return strength_score


def compromised_password_validator(form, field):
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"]:
        return None

    hashed_password = hashlib.sha1(field.data.encode("utf-8")).hexdigest()
    hashed_password_prefix, hashed_password_suffix = (
        hashed_password[:5].upper(),
        hashed_password[5:].upper(),
    )

    api_url = (
        current_app.config["CANAILLE"]["PASSWORD_COMPROMISSION_CHECK_API_URL"]
        + hashed_password_prefix
    )

    try:
        response = http().client.get(api_url, timeout=10)
    except Exception:
        if not request_is_partial():
            current_app.logger.exception(
                "Password compromise investigation failed on HIBP API."
            )
            check_if_send_mail_to_admins(form, api_url, hashed_password_suffix)
        return None

    decoded_response = response.content.decode("utf8").split("\r\n")

    for each in decoded_response:
        if hashed_password_suffix == each.split(":")[0]:
            raise wtforms.ValidationError(
                _(
                    "This password appears on public compromission databases and is not secure."
                )
            )


def email_validator(form, field):
    """Check the email address format, and skip the next validators when it is invalid."""
    try:
        import email_validator  # noqa: F401
    except ImportError:
        return

    try:
        wtforms.validators.Email()(form, field)
    except wtforms.validators.ValidationError as exc:
        raise wtforms.validators.StopValidation(str(exc)) from exc


def _parent_list(field):
    """Return the FieldList that holds ``field``, if any."""
    if getattr(field, "index", None) is None or field._form is None:
        return None

    list_name = field.short_name.rpartition("-")[0]
    parent = field._form._fields.get(list_name)
    return parent if isinstance(parent, wtforms.FieldList) else None


def field_wrapper(meta, field, render_kw):
    """Render a field with the Fomantic-UI macros of ``macro/form.html``.

    A FieldList entry gets the ``render_kw`` of its list.
    """
    parent = _parent_list(field)
    render_kw = {
        **((parent.render_kw if parent else None) or {}),
        **(field.render_kw or {}),
        **render_kw,
    }
    macros = current_app.jinja_env.get_template("macro/form.html").module
    return macros.field_wrapper(
        field, render_kw, parent, combobox=isinstance(field, ComboboxField)
    )


def fieldlist_buttons(list_name):
    """Return the buttons that add an entry to a field list, and remove its last one."""
    return (
        wtforms.ButtonField().triggers(list_name, list_add),
        wtforms.ButtonField().triggers(list_name, list_remove),
    )


class Form(HtmxFlaskForm):
    class Meta:
        field_wrapper = field_wrapper

    action = wtforms.ButtonField()


class TableForm(FlaskForm):
    """A form for table rendering of object collections."""

    def __init__(
        self, cls=None, page_size: int = 25, fields=None, filter=None, **kwargs
    ):
        filter = filter or {}
        super().__init__(**kwargs)
        if self.query.data:
            self.items = Backend.instance.fuzzy(cls, self.query.data, fields, **filter)
        else:
            self.items = Backend.instance.query(cls, **filter)

        self.page_size = page_size
        self.nb_items = len(self.items)
        self.page_max = max(1, math.ceil(self.nb_items / self.page_size))
        first_item = (self.page.data - 1) * self.page_size
        last_item = min((self.page.data) * self.page_size, self.nb_items)
        self.items_slice = self.items[first_item:last_item]

    page = wtforms.IntegerField(default=1)
    query = wtforms.StringField(default="", filters=[str.strip])

    def validate_page(self, field):
        if field.data < 1 or field.data > self.page_max:
            raise wtforms.validators.ValidationError(_("The page number is not valid"))


class DateTimeUTCField(wtforms.DateTimeLocalField):
    def _value(self):
        if not self.data:
            return ""

        user_timezone = timezone_selector()
        locale_dt = self.data.astimezone(user_timezone)
        return locale_dt.strftime(self.format[0])

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        date_str = " ".join(valuelist)
        user_timezone = timezone_selector()
        for format in self.strptime_format:
            try:
                unaware_dt = datetime.datetime.strptime(date_str, format)
                locale_dt = user_timezone.localize(unaware_dt)
                utc_dt = locale_dt.astimezone(datetime.UTC)
                self.data = utc_dt
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid datetime value."))


def is_readonly(field) -> bool:
    return field.render_kw and "readonly" in field.render_kw


def set_readonly(field) -> None:
    field.render_kw = field.render_kw or {}
    field.render_kw["readonly"] = True
    field.flags.readonly = True
    field.validators = list(field.validators) + [wtforms.validators.ReadOnly()]


class IDToModel:
    def __init__(self, model_name, raise_on_errors=True):
        self.model_name = model_name
        self.raise_on_errors = raise_on_errors

    def __call__(self, data):
        model = getattr(models, self.model_name)
        instance = (
            data if isinstance(data, model) else Backend.instance.get(model, data)
        )
        if instance:
            return instance

        if self.raise_on_errors:
            raise wtforms.ValidationError()
