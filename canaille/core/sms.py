from flask import current_app

from canaille.app.sms import send_sms
from canaille.app.templating import render_template


def send_one_time_password_sms(phone_number, otp):
    website_name = current_app.config["CANAILLE"]["NAME"]

    text_body = render_template(
        "core/sms/sms_otp.txt",
        website_name=website_name,
        otp=otp,
    )
    return send_sms(recipient=phone_number, sender=website_name, text=text_body)
