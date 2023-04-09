import wtforms.form
from canaille.app.forms import HTMXBaseForm
from canaille.app.forms import HTMXForm
from canaille.app.forms import is_uri
from canaille.app.i18n import native_language_name_from_code
from flask import current_app
from flask import g
from flask_babel import lazy_gettext as _
from flask_wtf.file import FileAllowed
from flask_wtf.file import FileField

from .models import Group
from .models import User


def unique_login(form, field):
    if User.get_from_login(field.data) and (
        not getattr(form, "user", None) or form.user.uid[0] != field.data
    ):
        raise wtforms.ValidationError(
            _("The login '{login}' already exists").format(login=field.data)
        )


def unique_email(form, field):
    if User.get(mail=field.data) and (
        not getattr(form, "user", None) or form.user.mail[0] != field.data
    ):
        raise wtforms.ValidationError(
            _("The email '{email}' is already used").format(email=field.data)
        )


def unique_group(form, field):
    if Group.get(field.data):
        raise wtforms.ValidationError(
            _("The group '{group}' already exists").format(group=field.data)
        )


def existing_login(form, field):
    if not current_app.config.get(
        "HIDE_INVALID_LOGINS", True
    ) and not User.get_from_login(field.data):
        raise wtforms.ValidationError(
            _("The login '{login}' does not exist").format(login=field.data)
        )


class LoginForm(HTMXForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired(), existing_login],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "inputmode": "email",
        },
    )


class PasswordForm(HTMXForm):
    password = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.DataRequired()],
    )


class FullLoginForm(LoginForm, PasswordForm):
    pass


class ForgottenPasswordForm(HTMXForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired(), existing_login],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )


class PasswordResetForm(HTMXForm):
    password = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "autocomplete": "new-password",
        },
    )
    confirmation = wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password", _("Password and confirmation do not match.")
            ),
        ],
        render_kw={
            "autocomplete": "new-password",
        },
    )


class FirstLoginForm(HTMXForm):
    pass


def available_language_choices():
    languages = [
        (lang_code, native_language_name_from_code(lang_code))
        for lang_code in g.available_language_codes
    ]
    languages.sort()
    return [("auto", _("Automatic"))] + languages


PROFILE_FORM_FIELDS = dict(
    user_name=wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe")},
        validators=[wtforms.validators.DataRequired(), unique_login],
    ),
    formatted_name=wtforms.StringField(_("Name")),
    title=wtforms.StringField(
        _("Title"), render_kw={"placeholder": _("Vice president")}
    ),
    given_name=wtforms.StringField(
        _("Given name"),
        render_kw={
            "placeholder": _("John"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    family_name=wtforms.StringField(
        _("Family Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("Doe"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    display_name=wtforms.StringField(
        _("Display Name"),
        validators=[wtforms.validators.Optional()],
        render_kw={
            "placeholder": _("Johnny"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    email=wtforms.EmailField(
        _("Email address"),
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Email(),
            unique_email,
        ],
        description=_(
            "This email will be used as a recovery address to reset the password if needed"
        ),
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    phone_number=wtforms.TelField(
        _("Phone number"), render_kw={"placeholder": _("555-000-555")}
    ),
    formatted_address=wtforms.StringField(
        _("Address"),
        render_kw={
            "placeholder": _("132, Foobar Street, Gotham City 12401, XX"),
        },
    ),
    street=wtforms.StringField(
        _("Street"),
        render_kw={
            "placeholder": _("132, Foobar Street"),
        },
    ),
    postal_code=wtforms.StringField(
        _("Postal Code"),
        render_kw={
            "placeholder": "12401",
        },
    ),
    locality=wtforms.StringField(
        _("Locality"),
        render_kw={
            "placeholder": _("Gotham City"),
        },
    ),
    region=wtforms.StringField(
        _("Region"),
        render_kw={
            "placeholder": _("North Pole"),
        },
    ),
    photo=FileField(
        _("Photo"),
        validators=[FileAllowed(["jpg", "jpeg"])],
        render_kw={"accept": "image/jpg, image/jpeg"},
    ),
    photo_delete=wtforms.BooleanField(_("Delete the photo")),
    password1=wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.Optional(), wtforms.validators.Length(min=8)],
        render_kw={
            "autocomplete": "new-password",
        },
    ),
    password2=wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password1", message=_("Password and confirmation do not match.")
            )
        ],
        render_kw={
            "autocomplete": "new-password",
        },
    ),
    employee_number=wtforms.StringField(
        _("User number"),
        render_kw={
            "placeholder": _("1234"),
        },
    ),
    department=wtforms.StringField(
        _("Department"),
        render_kw={
            "placeholder": _("1234"),
        },
    ),
    organization=wtforms.StringField(
        _("Organization"),
        render_kw={
            "placeholder": _("Cogip LTD."),
        },
    ),
    profile_url=wtforms.URLField(
        _("Website"),
        render_kw={
            "placeholder": _("https://mywebsite.tld"),
        },
        validators=[wtforms.validators.Optional(), is_uri],
    ),
    preferred_language=wtforms.SelectField(
        _("Preferred language"),
        choices=available_language_choices,
    ),
    groups=wtforms.SelectMultipleField(
        _("Groups"),
        choices=lambda: [(group.id, group.display_name) for group in Group.query()],
        render_kw={"placeholder": _("users, admins …")},
    ),
)


def profile_form(write_field_names, readonly_field_names, user=None):
    if "password" in write_field_names:
        write_field_names |= {"password1", "password2"}

    if "photo" in write_field_names:
        write_field_names |= {"photo_delete"}

    fields = {
        name: PROFILE_FORM_FIELDS.get(name)
        for name in write_field_names | readonly_field_names
        if PROFILE_FORM_FIELDS.get(name)
    }

    if "groups" in fields and not Group.query():
        del fields["groups"]

    form = HTMXBaseForm(fields)
    form.user = user
    for field in form:
        if field.name in readonly_field_names - write_field_names:
            field.render_kw["readonly"] = "true"

    return form


class CreateGroupForm(HTMXForm):
    display_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired(), unique_group],
        render_kw={
            "placeholder": _("group"),
        },
    )
    description = wtforms.StringField(
        _("Description"),
        validators=[wtforms.validators.Optional()],
    )


class EditGroupForm(HTMXForm):
    display_name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "readonly": "true",
        },
    )
    description = wtforms.StringField(
        _("Description"),
        validators=[wtforms.validators.Optional()],
    )


class InvitationForm(HTMXForm):
    user_name = wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe")},
        validators=[wtforms.validators.DataRequired(), unique_login],
    )
    user_name_editable = wtforms.BooleanField(_("Username editable by the invitee"))
    email = wtforms.EmailField(
        _("Email address"),
        validators=[
            wtforms.validators.DataRequired(),
            wtforms.validators.Email(),
            unique_email,
        ],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )
    groups = wtforms.SelectMultipleField(
        _("Groups"),
        choices=lambda: [(group.id, group.display_name) for group in Group.query()],
        render_kw={},
    )
