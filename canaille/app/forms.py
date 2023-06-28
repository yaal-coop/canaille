import datetime
import math
import re

import pytz
import wtforms
from canaille.app.i18n import DEFAULT_LANGUAGE_CODE
from canaille.app.i18n import locale_selector
from canaille.app.i18n import timezone_selector
from flask import abort
from flask import current_app
from flask import make_response
from flask import request
from flask_babel import gettext as _
from flask_wtf import FlaskForm
from wtforms.meta import DefaultMeta

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
        """
        Returns a tuple containing a field and its rendering context
        """
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
        """
        If the request is a HTMX request, this will only render the field
        that triggered the request (after having validated the form). This
        uses the Flask abort method to interrupt the flow with an exception.
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
        """
        Checks wether the current request is the result of the users
        adding or removing a field from a FieldList.
        """
        FIELDLIST_ADD_BUTTON = "fieldlist_add"
        FIELDLIST_REMOVE_BUTTON = "fieldlist_remove"

        fieldlist_suffix = rf"{self.SEPARATOR}(\d+)$"
        if field_name := request.form.get(FIELDLIST_ADD_BUTTON):
            fieldlist_name = re.sub(fieldlist_suffix, "", field_name)
            fieldlist, context = self.field_from_name(fieldlist_name)

            if not fieldlist or not isinstance(fieldlist, wtforms.FieldList):
                abort(400)

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
                abort(400)

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


class HTMXForm(HTMXFormMixin, I18NFormMixin, FlaskForm):
    pass


class HTMXBaseForm(HTMXFormMixin, I18NFormMixin, wtforms.form.BaseForm):
    pass


class TableForm(I18NFormMixin, FlaskForm):
    def __init__(self, cls=None, page_size=25, fields=None, filter=None, **kwargs):
        filter = filter or {}
        super().__init__(**kwargs)
        if self.query.data:
            self.items = cls.fuzzy(self.query.data, fields, **filter)
        else:
            self.items = cls.query(**filter)

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
                utc_dt = locale_dt.astimezone(pytz.utc)
                self.data = utc_dt
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid datetime value."))
