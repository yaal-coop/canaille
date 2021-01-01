import wtforms
import wtforms.form
from flask import current_app
from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from .models import User


class LoginForm(FlaskForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
            "inputmode": "email",
        },
    )
    password = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.DataRequired()],
    )

    def validate_login(self, field):
        if current_app.config.get("HIDE_INVALID_LOGINS", False) and not User.get(
            field.data
        ):
            raise wtforms.ValidationError(
                _("The login '{login}' does not exist").format(login=field.data)
            )


class ForgottenPasswordForm(FlaskForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )

    def validate_login(self, field):
        if current_app.config.get("HIDE_INVALID_LOGINS", False) and not User.get(
            field.data
        ):
            raise wtforms.ValidationError(
                _("The login '{login}' does not exist").format(login=field.data)
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
        render_kw={
            "placeholder": _("Doe"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    mail=wtforms.EmailField(
        _("Email address"),
        validators=[wtforms.validators.DataRequired(), wtforms.validators.Email()],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    ),
    telephoneNumber=wtforms.TelField(
        _("Phone number"), render_kw={"placeholder": _("555-000-555")}
    ),
    jpegPhoto=FileField(_("Photo"), validators=[FileRequired()]),
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
)


def profile_form(field_names):
    if "userPassword" in field_names:
        field_names += ["password1", "password2"]
    fields = {
        name: PROFILE_FORM_FIELDS.get(name)
        for name in field_names
        if PROFILE_FORM_FIELDS.get(name)
    }
    return wtforms.form.BaseForm(fields)
