import wtforms
from flask_babel import gettext
from flask_wtf import FlaskForm


class LoginForm(FlaskForm):
    login = wtforms.StringField(
        gettext("Username"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "mdupont"},
    )
    password = wtforms.PasswordField(
        gettext("Password"), validators=[wtforms.validators.DataRequired()]
    )
