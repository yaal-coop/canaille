import wtforms
from flask_babel import gettext as _
from flask_wtf import FlaskForm


class LoginForm(FlaskForm):
    login = wtforms.StringField(
        _("Login"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "mdupont"},
    )
    password = wtforms.PasswordField(
        _("Password"), validators=[wtforms.validators.DataRequired()]
    )


class ProfileForm(FlaskForm):
    sub = wtforms.StringField(
        _("Username"),
        render_kw={"readonly": "true"},
    )
    #    name = wtforms.StringField(_("Name"))
    given_name = wtforms.StringField(_("Given name"))
    family_name = wtforms.StringField(_("Family Name"))
    # preferred_username = wtforms.StringField(_("Preferred username"))
    #    gender = wtforms.StringField(_("Gender"))
    #    birthdate = wtforms.fields.html5.DateField(_("Birth date"))
    #    zoneinfo = wtforms.StringField(_("Zoneinfo"))
    #    locale = wtforms.StringField(_("Language"))
    email = wtforms.fields.html5.EmailField(_("Email address"))
    # address = wtforms.StringField(_("Address"))
    phone_number = wtforms.fields.html5.TelField(_("Phone number"))
    #    picture = wtforms.StringField(_("Photo"))
    #    website = wtforms.fields.html5.URLField(_("Website"))
