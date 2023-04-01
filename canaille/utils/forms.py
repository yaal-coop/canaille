import math

import wtforms
from flask import abort
from flask import current_app
from flask import make_response
from flask import request
from flask_babel import gettext as _
from flask_wtf import FlaskForm

from . import validate_uri
from .flask import request_is_htmx


def is_uri(form, field):
    if not validate_uri(field.data):
        raise wtforms.ValidationError(_("This is not a valid URL"))


class HTMXFormMixin:
    def validate(self, *args, **kwargs):
        """
        If the request is a HTMX request, this will only render the field
        that triggered the request (after having validated the form). This
        uses the Flask abort method to interrupt the flow with an exception.
        """
        if not request_is_htmx():
            return super().validate(*args, **kwargs)

        field = self[request.headers.get("HX-Trigger-Name")]
        field.widget.hide_value = False
        self.process(request.form)
        super().validate(*args, **kwargs)
        form_macro = current_app.jinja_env.get_template("macro/form.html")
        response = make_response(form_macro.module.render_field(field))
        abort(response)


class HTMXForm(HTMXFormMixin, FlaskForm):
    pass


class HTMXBaseForm(HTMXFormMixin, wtforms.form.BaseForm):
    pass


class TableForm(HTMXForm):
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
