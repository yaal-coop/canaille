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
