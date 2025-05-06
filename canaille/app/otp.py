"""Methods related to HOTP and TOTP."""

import secrets

from blinker import signal
from flask import current_app

HOTP_LOOK_AHEAD_WINDOW = 10
SECRET_TOKEN_LENGTH = 8


def initialize_otp(user):
    user.secret_token = secrets.token_hex(SECRET_TOKEN_LENGTH)
    user.last_otp_login = None
    if current_app.features.otp_method == "HOTP":
        user.hotp_counter = 1


def before_user_save(user, data):
    if current_app.features.has_otp and not user.secret_token:
        initialize_otp(user)


def generate_otp(user, counter_delta=0):
    import otpauth

    method = current_app.features.otp_method
    if method == "TOTP":
        totp = otpauth.TOTP(user.secret_token.encode("utf-8"))
        return totp.string_code(totp.generate())

    elif method == "HOTP":
        hotp = otpauth.HOTP(user.secret_token.encode("utf-8"))
        return hotp.string_code(hotp.generate(user.hotp_counter + counter_delta))

    else:  # pragma: no cover
        raise RuntimeError("Invalid one-time passcode method")


def get_otp_authentication_setup_uri(user):
    import otpauth

    if not user.secret_token:
        initialize_otp(user)

    method = current_app.features.otp_method
    if method == "TOTP":
        otp = otpauth.TOTP(user.secret_token.encode("utf-8"))
        return otp.to_uri(
            label=user.user_name, issuer=current_app.config["CANAILLE"]["NAME"]
        ), otp.b32_secret

    elif method == "HOTP":
        otp = otpauth.HOTP(user.secret_token.encode("utf-8"))
        return otp.to_uri(
            label=user.user_name,
            issuer=current_app.config["CANAILLE"]["NAME"],
            counter=user.hotp_counter,
        ), otp.b32_secret

    else:  # pragma: no cover
        raise RuntimeError("Invalid one-time passcode method")


def is_totp_valid(user, user_otp):
    import otpauth

    try:
        return otpauth.TOTP(user.secret_token.encode("utf-8")).verify(user_otp)

    # hotfix for https://github.com/authlib/otpauth/pull/13
    except (ValueError, TypeError):
        return False


def is_hotp_valid(user, user_otp):
    import otpauth

    counter = user.hotp_counter
    is_valid = False
    # if user token's counter is ahead of canaille's, try to catch up to it
    while counter - user.hotp_counter <= HOTP_LOOK_AHEAD_WINDOW:
        # hotfix for https://github.com/authlib/otpauth/pull/13
        try:
            is_valid = otpauth.HOTP(user.secret_token.encode("utf-8")).verify(
                user_otp, counter
            )
        except (ValueError, TypeError):
            is_valid = False

        counter += 1
        if is_valid:
            user.hotp_counter = counter
            return True
    return False


def setup_otp(app):
    signal("before_user_save").connect(before_user_save)
