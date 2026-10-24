"""Fomantic-UI widgets for the wtforms-htmx-components comboboxes."""

from markupsafe import Markup
from markupsafe import escape
from wtforms.widgets import html_params

from canaille.app.i18n import gettext as _


class ChipsWidget:
    """Render the values of a multi combobox as removable Fomantic-UI labels.

    A read-only or disabled combobox has no remove button.
    """

    def __call__(self, field, **kwargs):
        readonly = bool(field.flags.readonly)
        disabled = bool(field.flags.disabled)
        remove = field._form.remove
        chips = []
        for option in field:
            label = option.label.text
            button = (
                ""
                if readonly or disabled
                else remove(
                    value=option.data,
                    label=Markup('<i class="delete icon"></i>'),
                    id=False,
                    class_="combobox-remove",
                    aria_label=_("Remove %(label)s", label=label),
                )
            )
            hidden = html_params(
                type="hidden", name=field.name, value=option.data, disabled=disabled
            )
            chips.append(
                f'<div class="ui label" {html_params(data_value=option.data)}>'
                f"{escape(label)} {button}<input {hidden}></div>"
            )

        attrs = {"id": field.id, "class": "combobox-chips", **kwargs}
        return Markup(f"<div {html_params(**attrs)}>{''.join(chips)}</div>")


class ListboxWidget:
    """Render the suggestions of a combobox as a menu like the Fomantic-UI dropdown one."""

    def __init__(self, multi=False):
        self.multi = multi

    def __call__(self, field, **kwargs):
        attrs = {"id": field.id, "role": "listbox", **kwargs}
        if self.multi:
            attrs["aria-multiselectable"] = "true"

        items = [
            option(
                label=option.choice.label,
                role="option",
                class_="item",
                **option._form.htmx_submit_attrs(option),
            )
            for option in field
        ]
        return Markup(f"<div {html_params(**attrs)}>{''.join(items)}</div>")
