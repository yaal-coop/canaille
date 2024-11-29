import smpplib.client
import smpplib.consts
import smpplib.gsm
from flask import current_app

from canaille.app.themes import render_template


def send_one_time_password_sms(phone_number, otp):
    website_name = current_app.config["CANAILLE"]["NAME"]

    text_body = render_template(
        "sms/sms_otp.txt",
        website_name=website_name,
        otp=otp,
    )
    return send_sms(recipient=phone_number, sender=website_name, text=text_body)


def send_sms(recipient, sender, text):
    port = current_app.config["CANAILLE"]["SMPP"]["PORT"]
    host = current_app.config["CANAILLE"]["SMPP"]["HOST"]
    login = current_app.config["CANAILLE"]["SMPP"]["LOGIN"]
    password = current_app.config["CANAILLE"]["SMPP"]["PASSWORD"]

    try:
        client = smpplib.client.Client(host, port, allow_unknown_opt_params=True)
        client.connect()
        try:
            client.bind_transmitter(system_id=login, password=password)
            pdu = client.send_message(
                source_addr_ton=smpplib.consts.SMPP_TON_INTL,
                source_addr=sender,
                dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                destination_addr=recipient,
                short_message=bytes(text, "utf-8"),
            )
            current_app.logger.debug(pdu.generate())
        finally:
            if client.state in [
                smpplib.consts.SMPP_CLIENT_STATE_BOUND_TX
            ]:  # pragma: no cover
                # if bound to transmitter
                try:
                    client.unbind()
                except smpplib.exceptions.UnknownCommandError:
                    # https://github.com/podshumok/python-smpplib/issues/2
                    try:
                        client.unbind()
                    except smpplib.exceptions.PDUError:
                        pass
    finally:
        if client:  # pragma: no branch
            client.disconnect()
