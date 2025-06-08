"""Methods related to HOTP and TOTP."""

import secrets

from flask import current_app

SECRET_TOKEN_LENGTH = 8
HOTP_LOOK_AHEAD_WINDOW = 10
HOTP_START_COUNTER = 0


def make_otp_secret():
    return secrets.token_hex(SECRET_TOKEN_LENGTH)


def get_otp_authentication_setup_uri(user, secret):
    import otpauth

    method = current_app.features.otp_method
    if method == "TOTP":
        otp = otpauth.TOTP(secret.encode("utf-8"))
        return otp.to_uri(
            label=user.user_name, issuer=current_app.config["CANAILLE"]["NAME"]
        ), otp.b32_secret

    elif method == "HOTP":
        otp = otpauth.HOTP(secret.encode("utf-8"))
        return otp.to_uri(
            label=user.user_name,
            issuer=current_app.config["CANAILLE"]["NAME"],
            counter=HOTP_START_COUNTER,
        ), otp.b32_secret

    else:  # pragma: no cover
        raise RuntimeError("Invalid one-time passcode method")


def is_otp_valid(
    otp, method, secret_token, hotp_counter=HOTP_START_COUNTER
) -> tuple[bool, int]:
    """Return whether the OTP code is valid, and the new hotp_counter for the user."""
    import otpauth

    if method == "TOTP":
        result = otpauth.TOTP(secret_token.encode("utf-8")).verify(otp)
        return result, hotp_counter

    else:
        # if user token's counter is ahead of canaille's, try to catch up to it
        for counter in range(hotp_counter, hotp_counter + HOTP_LOOK_AHEAD_WINDOW + 1):
            if otpauth.HOTP(secret_token.encode("utf-8")).verify(otp, counter):
                return True, counter + 1
        return False, hotp_counter + 1
