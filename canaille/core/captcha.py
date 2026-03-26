"""CAPTCHA generation and validation module."""

import base64
import secrets

from flask import current_app
from flask import g
from flask import session

CAPTCHA_WIDTH = 160
CAPTCHA_HEIGHT = 45
CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def should_show_captcha_on_login(user=None):
    """Determine if CAPTCHA should be shown on login form.

    Once the failure threshold is reached, the CAPTCHA remains active
    until a successful login, regardless of time elapsed.
    """
    if not current_app.features.has_captcha:
        return False

    threshold = current_app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"]

    if threshold == 0:
        return True

    if not user:
        if not g.auth or not g.auth.user:
            return False
        user = g.auth.user

    if not user.password_failure_timestamps:
        return False

    return len(user.password_failure_timestamps) >= threshold


def generate_captcha():
    """Generate a CAPTCHA (image + audio) and return data."""
    from captcha.image import ImageCaptcha

    length = current_app.config["CANAILLE"]["CAPTCHA_LENGTH"]

    text = "".join(secrets.choice(CAPTCHA_CHARS) for _ in range(length))

    image = ImageCaptcha(width=CAPTCHA_WIDTH, height=CAPTCHA_HEIGHT)
    image_bytes = image.generate(text)

    image_b64 = base64.b64encode(image_bytes.getvalue()).decode()
    data_uri = f"data:image/png;base64,{image_b64}"

    token = secrets.token_urlsafe(16)
    session[f"captcha_{token}"] = text.upper()

    return {"token": token, "image_data_uri": data_uri, "text": text}


def generate_audio_captcha(text) -> bytes:
    """Generate audio CAPTCHA for given text."""
    from captcha.audio import AudioCaptcha

    audio = AudioCaptcha()
    audio_data = audio.generate(text)
    return bytes(audio_data)


def verify_captcha(token, user_response) -> bool:
    """Verify CAPTCHA response."""
    if not token or not user_response:
        return False

    session_key = f"captcha_{token}"
    expected = session.pop(session_key, None)

    if not expected:
        return False

    return user_response.strip().upper() == expected
