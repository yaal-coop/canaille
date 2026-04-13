import email.message
import mimetypes
import os
import smtplib
import urllib.error
import urllib.request
from email.utils import make_msgid

from flask import current_app
from werkzeug.security import safe_join

from canaille.app import get_current_mail_domain
from canaille.app.flask import cache
from canaille.app.flask import dramatiq

try:
    import flask_themer
except ImportError:
    flask_themer = None

LOGO_FETCH_TIMEOUT = 5
LOGO_CACHE_TIMEOUT = 24 * 60 * 60
THEME_STATIC_PREFIX = "/_theme/"


def logo():
    logo_url = current_app.config["CANAILLE"]["LOGO"]
    if not logo_url or not current_app.config["SERVER_NAME"]:
        return None, None, None

    logo_raw = _fetch_logo(logo_url)
    if logo_raw is None:
        return None, None, None

    logo_filename = logo_url.split("/")[-1]
    logo_cid = make_msgid(domain=get_current_mail_domain())
    return logo_cid, logo_filename, logo_raw


@cache.memoize(timeout=LOGO_CACHE_TIMEOUT)
def _fetch_logo(logo_url):
    """Return the logo bytes, or ``None`` if it cannot be fetched.

    External ``http(s)://`` URLs are retrieved with a short timeout.
    Application-local paths are resolved directly from the filesystem.
    """
    if logo_url.startswith(("http://", "https://")):
        return _fetch_external_logo(logo_url)

    return _read_local_logo(logo_url)


def _read_local_logo(logo_url):
    """Resolve a Canaille-local logo URL to a file on disk."""
    path = _resolve_static_file(logo_url) or _resolve_theme_static_file(logo_url)
    if path is None or not os.path.isfile(path):
        return None

    with open(path, "rb") as fd:
        return fd.read()


def _resolve_static_file(logo_url):
    """Resolve an URL served by Flask's built-in static route."""
    static_url_path = current_app.static_url_path
    static_folder = current_app.static_folder
    if not static_url_path or not static_folder:  # pragma: no cover
        return None

    prefix = static_url_path.rstrip("/") + "/"
    if not logo_url.startswith(prefix):
        return None

    return safe_join(static_folder, logo_url[len(prefix) :])


def _resolve_theme_static_file(logo_url):
    """Resolve an URL served by the flask_themer theme static blueprint."""
    if flask_themer is None or not logo_url.startswith(
        THEME_STATIC_PREFIX
    ):  # pragma: no cover
        return None

    remainder = logo_url[len(THEME_STATIC_PREFIX) :]
    theme_name, _, filename = remainder.partition("/")
    if not theme_name or not filename:
        return None

    themer = current_app.extensions.get(flask_themer.EXTENSION_KEY)
    if themer is None or theme_name not in themer.themes:
        return None

    for loader in themer.loaders:
        theme_static = os.path.join(str(loader.path), theme_name, "static")
        candidate = safe_join(theme_static, filename)
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def _fetch_external_logo(logo_url):
    try:
        with urllib.request.urlopen(logo_url, timeout=LOGO_FETCH_TIMEOUT) as f:
            return f.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def type_from_filename(filename):
    filetype = mimetypes.guess_type(filename)
    if not filetype or not filetype[0]:
        # For some reasons GHA fails to guess webp mimetypes
        # According to MDN, the default mimetype should be application/octet-stream
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        return "application", "octet-stream"

    maintype, subtype = filetype[0].split("/")
    return maintype, subtype


@dramatiq.actor
def send_email(subject, recipient, text, html, attachments=None):
    current_app.logger.debug(f"Sending a mail to {recipient}: {subject}")
    msg = email.message.EmailMessage()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    msg["Subject"] = subject
    msg["To"] = f"<{recipient}>"

    name = current_app.config["CANAILLE"]["NAME"]
    address = current_app.config["CANAILLE"]["SMTP"]["FROM_ADDR"]

    if not address:
        domain = get_current_mail_domain()
        address = f"admin@{domain}"

    msg["From"] = f'"{name}" <{address}>'

    attachments = attachments or []
    for cid, filename, value in attachments:
        maintype, subtype = type_from_filename(filename)
        msg.get_payload()[1].add_related(
            value, maintype=maintype, subtype=subtype, cid=cid
        )

    smtp = None
    try:
        connection_func = (
            smtplib.SMTP_SSL
            if current_app.config["CANAILLE"]["SMTP"]["SSL"]
            else smtplib.SMTP
        )
        with connection_func(
            host=current_app.config["CANAILLE"]["SMTP"]["HOST"],
            port=current_app.config["CANAILLE"]["SMTP"]["PORT"],
        ) as smtp:
            if current_app.config["CANAILLE"]["SMTP"]["TLS"]:
                smtp.starttls()
            if current_app.config["CANAILLE"]["SMTP"]["LOGIN"]:
                smtp.login(
                    user=current_app.config["CANAILLE"]["SMTP"]["LOGIN"],
                    password=current_app.config["CANAILLE"]["SMTP"]["PASSWORD"],
                )
            smtp.send_message(msg)

    except smtplib.SMTPRecipientsRefused:
        pass

    except OSError as exc:
        current_app.logger.warning(f"Could not send email: {exc}")
        return False

    current_app.logger.info("The mail has been sent correctly.")
    return True
