import base64
import hashlib
import hmac
import json
from base64 import b64encode
from io import BytesIO
from urllib.parse import urlparse

from flask import current_app
from flask import request

DOCUMENTATION_URL = "https://canaille.readthedocs.io"


def obj_to_b64(obj):
    return base64.b64encode(json.dumps(obj).encode("utf-8")).decode("utf-8")


def b64_to_obj(string):
    return json.loads(base64.b64decode(string.encode("utf-8")).decode("utf-8"))


def build_hash(*args):
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    message = obj_to_b64(str(args)).encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def default_fields():
    read = set()
    write = set()
    for acl in current_app.config["CANAILLE"]["ACL"].values():
        if not acl.get("FILTER"):
            read |= set(acl.get("READ", []))
            write |= set(acl.get("WRITE", []))

    return read, write


def get_current_domain():
    if current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.host


def get_current_mail_domain():
    if current_app.config["CANAILLE"]["SMTP"]["FROM_ADDR"]:
        return current_app.config["CANAILLE"]["SMTP"]["FROM_ADDR"].split("@")[-1]

    return get_current_domain().split(":")[0]


def validate_uri(value):
    parsed = urlparse(value)
    return (parsed.scheme in ["http", "https"] or "." in parsed.scheme) and bool(
        parsed.netloc
    )


class classproperty:
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


def get_b64encoded_qr_image(data):
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    return b64encode(buffered.getvalue()).decode("utf-8")


def mask_email(email):
    atpos = email.find("@")
    if atpos > 0:
        return email[0] + "#####" + email[atpos - 1 :]
    return None


def mask_phone(phone):
    return phone[0:3] + "#####" + phone[-2:]
