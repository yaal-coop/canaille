from flask import current_app


def send_sms(recipient, sender, text):
    try:
        import smpplib.client
        import smpplib.consts
        import smpplib.gsm
    except ImportError as exc:
        raise RuntimeError(
            "You are trying to send a sms but the 'sms' extra is not installed."
        ) from exc

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
                    try:
                        client.unbind()
                    except smpplib.exceptions.PDUError:
                        pass
    except Exception as exc:
        current_app.logger.warning(f"Could not send sms: {exc}")
        return False
    finally:
        if client:  # pragma: no branch
            client.disconnect()

    return True
