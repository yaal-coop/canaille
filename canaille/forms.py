import wtforms.form
from flask import current_app
from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from flask_wtf.file import FileField

from .models import Group
from .models import User


def unique_login(form, field):
    if User.get(field.data):
        raise wtforms.ValidationError(
            _("The login '{login}' already exists").format(login=field.data)
        )


def unique_email(form, field):
    if User.get(filter=f"(mail={field.data})"):
        raise wtforms.ValidationError(
            _("The email '{email}' already exists").format(email=field.data)
        )


def unique_group(form, field):
    if Group.get(field.data):
        raise wtforms.ValidationError(
            _("The group '{group}' already exists").format(group=field.data)
        )


def existing_login(form, field):
    if current_app.config.get("HIDE_INVALID_LOGINS", False) and not User.get(
        field.data
    ):
        raise wtforms.ValidationError(
            _("The login '{login}' does not exist").format(login=field.data)
        )


class LoginForm(FlaskForm):
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


class PasswordForm(FlaskForm):
    password = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.DataRequired()],
    )


class FullLoginForm(LoginForm, PasswordForm):
    pass


class ForgottenPasswordForm(FlaskForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired(), existing_login],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )


class PasswordResetForm(FlaskForm):
    password = wtforms.PasswordField(
        _("Password"), validators=[wtforms.validators.DataRequired()]
    )
    confirmation = wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password", _("Password and confirmation do not match.")
            ),
        ],
    )


PROFILE_FORM_FIELDS = dict(
    uid=wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe")},
        validators=[wtforms.validators.DataRequired()],
    ),
    cn=wtforms.StringField(_("Name")),
    givenName=wtforms.StringField(
        _("Given name"),
        render_kw={
            "placeholder": _("John"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    sn=wtforms.StringField(
        _("Family Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("Doe"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    mail=wtforms.EmailField(
        _("Email address"),
        validators=[wtforms.validators.DataRequired(), wtforms.validators.Email()],
        description=_(
            "This email will be used as a recovery address to reset the password if needed"
        ),
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    telephoneNumber=wtforms.TelField(
        _("Phone number"), render_kw={"placeholder": _("555-000-555")}
    ),
    jpegPhoto=FileField(
        _("Photo"),
        validators=[FileAllowed(["jpg", "jpeg"])],
        render_kw={"accept": "image/jpg, image/jpeg"},
    ),
    jpegPhoto_delete=wtforms.BooleanField(_("Delete the photo")),
    password1=wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.Optional(), wtforms.validators.Length(min=8)],
    ),
    password2=wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password1", message=_("Password and confirmation do not match.")
            )
        ],
    ),
    employeeNumber=wtforms.StringField(
        _("Number"),
        render_kw={
            "placeholder": _("1234"),
        },
    ),
    labeledURI=wtforms.URLField(
        _("Website"),
        render_kw={
            "placeholder": _("https://mywebsite.tld"),
        },
    ),
)


def profile_form(write_field_names, readonly_field_names):
    if "userPassword" in write_field_names:
        write_field_names |= {"password1", "password2"}

    if "jpegPhoto" in write_field_names:
        write_field_names |= {"jpegPhoto_delete"}

    fields = {
        name: PROFILE_FORM_FIELDS.get(name)
        for name in write_field_names | readonly_field_names
        if PROFILE_FORM_FIELDS.get(name)
    }

    if (
        "groups" in write_field_names | readonly_field_names
        and Group.available_groups()
    ):
        fields["groups"] = wtforms.SelectMultipleField(
            _("Groups"),
            choices=[(group[1], group[0]) for group in Group.available_groups()],
            render_kw={"placeholder": _("users, admins ...")},
        )

    form = wtforms.form.BaseForm(fields)
    for field in form:
        if field.name in readonly_field_names - write_field_names:
            field.render_kw["readonly"] = "true"

    return form


class GroupForm(FlaskForm):
    name = wtforms.StringField(
        _("Name"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("group"),
        },
    )
    description = wtforms.StringField(
        _("Description"),
        validators=[wtforms.validators.Optional()],
    )


class InvitationForm(FlaskForm):
    uid = wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe")},
        validators=[wtforms.validators.DataRequired(), unique_login],
    )
    uid_editable = wtforms.BooleanField(_("Username editable by the invitee"))
    mail = wtforms.EmailField(
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
        choices=lambda: [(group[1], group[0]) for group in Group.available_groups()],
        render_kw={},
    )
