import wtforms.form
import wtforms.validators
from flask import current_app

from canaille.app import models
from canaille.app.i18n import gettext
from canaille.app.i18n import lazy_gettext as _
from canaille.backends import Backend


def unique_user_name(form, field):
    if Backend.instance.get(models.User, user_name=field.data) and (
        not getattr(form, "user", None) or form.user.user_name != field.data
    ):
        raise wtforms.ValidationError(
            _("The user name '{user_name}' already exists").format(user_name=field.data)
        )


def unique_email(form, field):
    if Backend.instance.get(models.User, emails=field.data) and (
        not getattr(form, "user", None) or field.data not in form.user.emails
    ):
        raise wtforms.ValidationError(
            _("The email '{email}' is already used").format(email=field.data)
        )


def unique_group(form, field):
    if Backend.instance.get(models.Group, display_name=field.data):
        raise wtforms.ValidationError(
            _("The group '{group}' already exists").format(group=field.data)
        )


def existing_login(form, field):
    if not current_app.config["CANAILLE"][
        "HIDE_INVALID_LOGINS"
    ] and not Backend.instance.get_user_from_login(field.data):
        raise wtforms.ValidationError(
            _("The login '{login}' does not exist").format(login=field.data)
        )


def existing_group_member(form, field):
    if field.data is None:
        raise wtforms.ValidationError(
            gettext("The user you are trying to remove does not exist.")
        )

    if field.data not in form.group.members:
        raise wtforms.ValidationError(
            gettext(
                "The user '{user}' has already been removed from the group '{group}'"
            ).format(user=field.data.formatted_name, group=form.group.display_name)
        )


def non_empty_groups(form, field):
    """LDAP groups cannot be empty because groupOfNames.member is a MUST
    attribute.

    https://www.rfc-editor.org/rfc/rfc2256.html#section-7.10
    """
    if not form.user:
        return

    for group in form.user.groups:
        if len(group.members) == 1 and group not in field.data:
            raise wtforms.ValidationError(
                _(
                    "The group '{group}' cannot be removed, because it must have at least one user left."
                ).format(group=group.display_name)
            )
