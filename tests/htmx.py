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
    return {"fieldlist_add": f"{list_name}-0"}


def fieldlist_remove(list_name):
    """Return the form data of a click on the button that removes an entry from a field list."""
    return {"fieldlist_remove": f"{list_name}-0"}


def click_fieldlist_add(form, list_name, **kwargs):
    """Submit ``form`` with the button that adds an entry to a field list."""
    return _click_fieldlist_button(form, "fieldlist_add", list_name, **kwargs)


def click_fieldlist_remove(form, list_name, **kwargs):
    """Submit ``form`` with the button that removes an entry from a field list."""
    return _click_fieldlist_button(form, "fieldlist_remove", list_name, **kwargs)


def _click_fieldlist_button(form, name, list_name, **kwargs):
    for button in form.fields.get(name, []):
        value = button.value_if_submitted()
        if value.startswith(f"{list_name}-"):
            return form.submit(name, value=value, **kwargs)

    raise AssertionError(f"The form has no {name} button for {list_name}")
