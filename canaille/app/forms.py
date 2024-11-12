import datetime
import math
import re

import wtforms.validators
from flask import abort
from flask import current_app
from flask import flash
from flask import make_response
from flask import request
from flask_wtf import FlaskForm
from wtforms.meta import DefaultMeta

from canaille.app import models
from canaille.app.i18n import DEFAULT_LANGUAGE_CODE
from canaille.app.i18n import gettext as _
from canaille.app.i18n import locale_selector
from canaille.app.i18n import timezone_selector
from canaille.backends import Backend
from canaille.core.mails import send_compromised_password_check_failure_mail

from . import validate_uri
from .flask import request_is_htmx


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
        strength_score = zxcvbn(password).score
        strength_score = strength_score * 100 // 4

    return strength_score


def check_if_send_mail_to_admins(form, api_url, hashed_password_suffix):
    if current_app.features.has_smtp and not request_is_htmx():
        flash(
            _(
                "Password compromise investigation failed. "
                "Please contact the administrators."
            ),
            "error",
        )

        admin_group_display_name = current_app.config["CANAILLE"]["ACL"]["ADMIN"][
            "FILTER"
        ]["groups"]

        group_user = Backend.instance.query(models.User)

        admins = [
            user
            for user in group_user
            if any(
                group.display_name == admin_group_display_name for group in user.groups
            )
        ]

        if form.user is not None:
            user_name = form.user.user_name
            user_email = form.user.emails[0]
        else:
            user_name = form["user_name"].data
            user_email = form["emails"].data[0]

        number_emails_send = 0

        for admin in admins:
            if send_compromised_password_check_failure_mail(
                api_url, user_name, user_email, hashed_password_suffix, admin.emails[0]
            ):
                number_emails_send += 1
            else:
                pass

        if number_emails_send > 0:
            flash(
                _(
                    "We have informed your administrator about the failure of the password compromise investigation."
                ),
                "success",
            )
        else:
            flash(
                _(
                    "An error occurred while communicating the incident to the administrators. "
                    "Please update your password as soon as possible. "
                    "If this still happens, please contact the administrators."
                ),
                "error",
            )
            return None

        return number_emails_send
    return None


def compromised_password_validator(form, field):
    try:
        from hashlib import sha1

        import requests
    except ImportError:
        return None

    hashed_password = sha1(field.data.encode("utf-8")).hexdigest()
    hashed_password_prefix, hashed_password_suffix = (
        hashed_password[:5].upper(),
        hashed_password[5:].upper(),
    )

    api_url = f"https://api.pwnedpasswords.com/range/{hashed_password_prefix}"

    try:
        response = requests.api.get(api_url, timeout=10)
    except Exception as e:
        print("Error: " + str(e))

        check_if_send_mail_to_admins(form, api_url, hashed_password_suffix)

        return None

    decoded_response = response.content.decode("utf8").split("\r\n")

    for each in decoded_response:
        if hashed_password_suffix == each.split(":")[0]:
            raise wtforms.ValidationError(_("This password is compromised."))


def email_validator(form, field):
    try:
        import email_validator  # noqa: F401
    except ImportError:
        pass

    wtforms.validators.Email()(form, field)


meta = DefaultMeta()


class I18NFormMixin:
    def __init__(self, *args, **kwargs):
        preferred_locale = locale_selector()
        meta.locales = (
            [preferred_locale, DEFAULT_LANGUAGE_CODE] if preferred_locale else False
        )
        super().__init__(*args, meta=meta, **kwargs)


class HTMXFormMixin:
    SEPARATOR = "-"
    render_field_macro_file = "macro/form.html"
    render_field_extra_context = {}

    def field_from_name(self, field_name):
        """Return a tuple containing a field and its rendering context."""
        if self.SEPARATOR not in field_name:
            field = self[field_name] if field_name in self else None
            return field, {}

        parts = field_name.split(self.SEPARATOR)
        fieldlist_name = self.SEPARATOR.join(parts[:-1])
        try:
            indice = int(parts[-1])
        except ValueError:
            return None, {}
        fieldlist, _ = self.field_from_name(fieldlist_name)
        context = {"parent_list": fieldlist, "parent_indice": indice}
        return fieldlist[indice], context

    def validate(self, *args, **kwargs):
        """If the request is a HTMX request, this will only render the field
        that triggered the request (after having validated the form).

        This uses the Flask abort method to interrupt the flow with an
        exception.
        """
        if not request_is_htmx():
            return super().validate(*args, **kwargs)

        field_name = request.headers.get("HX-Trigger-Name")
        field, context = self.field_from_name(field_name)
        if field:
            self.validate_field(field, *args, **kwargs)
            self.render_field(field, **context)

        abort(400, f"{field_name} is not a valid field for inline validation")

    def validate_field(self, field, *args, **kwargs):
        field.widget.hide_value = False
        self.process(request.form)
        return field.validate(self, *args, **kwargs)

    def render_field(self, field, *args, **kwargs):
        form_macro = current_app.jinja_env.get_template(self.render_field_macro_file)
        response = make_response(
            form_macro.module.render_field(
                field, *args, **kwargs, **self.render_field_extra_context
            )
        )
        abort(response)

    def form_control(self):
        """Check whether the current request is the result of the users adding
        or removing a field from a FieldList."""
        FIELDLIST_ADD_BUTTON = "fieldlist_add"
        FIELDLIST_REMOVE_BUTTON = "fieldlist_remove"

        fieldlist_suffix = rf"{self.SEPARATOR}(\d+)$"
        if field_name := request.form.get(FIELDLIST_ADD_BUTTON):
            fieldlist_name = re.sub(fieldlist_suffix, "", field_name)
            fieldlist, context = self.field_from_name(fieldlist_name)

            if not fieldlist or not isinstance(fieldlist, wtforms.FieldList):
                abort(400, f"{field_name} is not a valid field list")

            if fieldlist.render_kw and (
                "readonly" in fieldlist.render_kw or "disabled" in fieldlist.render_kw
            ):
                abort(403)

            if request_is_htmx():
                self.validate_field(fieldlist)

            fieldlist.append_entry()

            if request_is_htmx():
                self.render_field(fieldlist, **context)

            return True

        if field_name := request.form.get(FIELDLIST_REMOVE_BUTTON):
            fieldlist_name = re.sub(fieldlist_suffix, "", field_name)
            fieldlist, context = self.field_from_name(fieldlist_name)

            if not fieldlist or not isinstance(fieldlist, wtforms.FieldList):
                abort(400, f"{field_name} is not a valid field list")

            if fieldlist.render_kw and (
                "readonly" in fieldlist.render_kw or "disabled" in fieldlist.render_kw
            ):
                abort(403)

            if request_is_htmx():
                self.validate_field(fieldlist)

            fieldlist.pop_entry()

            if request_is_htmx():
                self.render_field(fieldlist, **context)

            return True

        return False


class Form(HTMXFormMixin, I18NFormMixin, FlaskForm):
    pass


class BaseForm(HTMXFormMixin, I18NFormMixin, wtforms.form.BaseForm):
    pass


class TableForm(I18NFormMixin, FlaskForm):
    def __init__(self, cls=None, page_size=25, fields=None, filter=None, **kwargs):
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
    query = wtforms.StringField(default="")

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
                utc_dt = locale_dt.astimezone(datetime.timezone.utc)
                self.data = utc_dt
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid datetime value."))


def is_readonly(field):
    return field.render_kw and "readonly" in field.render_kw


def set_readonly(field):
    field.render_kw = field.render_kw or {}
    field.render_kw["readonly"] = True
    field.validators = list(field.validators) + [wtforms.validators.ReadOnly()]


def set_writable(field):
    del field.render_kw["readonly"]
    field.validators = [
        v for v in field.validators if not isinstance(v, wtforms.validators.ReadOnly)
    ]


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
