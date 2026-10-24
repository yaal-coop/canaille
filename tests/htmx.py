"""Send form interactions the way a browser does, with or without htmx."""


def htmx_headers(trigger=None):
    """Return the headers of an htmx request, sent by the field ``trigger`` if any."""
    headers = {"HX-Request": "true"}
    if trigger:
        headers["HX-Trigger"] = trigger
        headers["HX-Trigger-Name"] = trigger

    return headers


def fieldlist_add(list_name):
    """Return the form data of a click on the button that adds an entry to a field list."""
    return {f"add_{list_name}": ""}


def fieldlist_remove(list_name):
    """Return the form data of a click on the button that removes an entry from a field list."""
    return {f"del_{list_name}": ""}


def click_fieldlist_add(form, list_name, **kwargs):
    """Submit ``form`` with the button that adds an entry to a field list."""
    return form.submit(f"add_{list_name}", **kwargs)


def click_fieldlist_remove(form, list_name, **kwargs):
    """Submit ``form`` with the button that removes an entry from a field list."""
    return form.submit(f"del_{list_name}", **kwargs)


def pick_in_combobox(form, name, query, value, **kwargs):
    """Search ``query`` in a combobox and click the suggestion ``value``, without htmx."""
    form[f"{name}-query"] = query
    res = form.submit(f"{name}-search", **kwargs)
    return res.forms[form.id].submit(f"{name}-suggestions", value=value, **kwargs)


def remove_from_combobox(form, name, value, **kwargs):
    """Click the remove button of the value ``value`` in a combobox, without htmx."""
    return form.submit(f"{name}-remove", value=value, **kwargs)


def combobox_values(form, name):
    """Return the values that a combobox sends."""
    return [field.value for field in form.fields.get(f"{name}-value", [])]


def combobox_is_readonly(form, name):
    """Tell whether a combobox renders its values only, without search nor removal."""
    return f"{name}-query" not in form.fields and f"{name}-remove" not in form.fields
