import wtforms
from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm


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


class ProfileForm(FlaskForm):
    sub = wtforms.StringField(
        _("Username"),
        render_kw={"placeholder": _("jdoe")},
        validators=[wtforms.validators.DataRequired()],
    )
    #    name = wtforms.StringField(_("Name"))
    given_name = wtforms.StringField(
        _("Given name"),
        render_kw={
            "placeholder": _("John"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )
    family_name = wtforms.StringField(
        _("Family Name"),
        render_kw={
            "placeholder": _("Doe"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )
    #    preferred_username = wtforms.StringField(_("Preferred username"))
    #    gender = wtforms.StringField(_("Gender"))
    #    birthdate = wtforms.DateField(_("Birth date"))
    #    zoneinfo = wtforms.StringField(_("Zoneinfo"))
    #    locale = wtforms.StringField(_("Language"))
    email = wtforms.EmailField(
        _("Email address"),
        validators=[wtforms.validators.DataRequired(), wtforms.validators.Email()],
        render_kw={
            "placeholder": _("jane@doe.com"),
            "spellcheck": "false",
            "autocorrect": "off",
        },
    )
    #    address = wtforms.StringField(_("Address"))
    phone_number = wtforms.TelField(
        _("Phone number"), render_kw={"placeholder": _("555-000-555")}
    )
    #    picture = wtforms.StringField(_("Photo"))
    #    website = wtforms.URLField(_("Website"))
    password1 = wtforms.PasswordField(
        _("Password"),
        validators=[wtforms.validators.Optional(), wtforms.validators.Length(min=8)],
    )
    password2 = wtforms.PasswordField(
        _("Password confirmation"),
        validators=[
            wtforms.validators.EqualTo(
                "password1", message=_("Password and confirmation do not match.")
            )
        ],
    )
