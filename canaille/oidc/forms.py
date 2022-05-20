import wtforms
from flask_wtf import FlaskForm


class LogoutForm(FlaskForm):
    answer = wtforms.SubmitField()
