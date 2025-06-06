import datetime

from flask import current_app
from flask import g
from flask import request

DEFAULT_LANGUAGE_CODE = "en"

try:
    from flask_babel import Babel
    from flask_babel import get_locale
    from flask_babel import gettext
    from flask_babel import lazy_gettext

    babel = Babel()
except ImportError:

    def identity(string, *args, **kwargs):
        return string

    def get_locale():
        return "en_US"

    gettext = identity
    lazy_gettext = identity
    babel = None


def mock_babel(app):  # pragma: no cover
    """Jinja stubs when flask-babel is not installed."""
    app.jinja_env.filters.update(
        datetimeformat=identity,
        dateformat=identity,
        timeformat=identity,
        timedeltaformat=identity,
        numberformat=identity,
        decimalformat=identity,
        currencyformat=identity,
        percentformat=identity,
        scientificformat=identity,
    )
    app.jinja_env.add_extension("jinja2.ext.i18n")
    app.jinja_env.install_gettext_callables(
        gettext=identity,
        ngettext=identity,
        newstyle=True,
        pgettext=identity,
        npgettext=identity,
    )


def setup_i18n(app):
    @app.before_request
    def before_request():
        g.available_language_codes = available_language_codes()

    @app.context_processor
    def global_processor():
        return {
            "locale": get_locale(),
        }

    if not babel:  # pragma: no cover
        mock_babel(app)
        return

    babel.init_app(
        app, locale_selector=locale_selector, timezone_selector=timezone_selector
    )


def locale_selector():
    available_language_codes = getattr(g, "available_language_codes", [])
    if (
        g.get("session")
        and g.session.user.preferred_language in available_language_codes
    ):
        return g.session.user.preferred_language

    if current_app.config["CANAILLE"]["LANGUAGE"]:
        return current_app.config["CANAILLE"]["LANGUAGE"]

    return request.accept_languages.best_match(available_language_codes)


def timezone_selector():
    if not babel:  # pragma: no cover
        return datetime.timezone.utc

    import pytz
    from babel.dates import LOCALTZ

    try:
        return pytz.timezone(current_app.config["CANAILLE"]["TIMEZONE"])
    except pytz.exceptions.UnknownTimeZoneError:
        return LOCALTZ


def native_language_name_from_code(code):
    try:
        from gettext import translation

        import pycountry
    except ImportError:
        return code

    language = pycountry.languages.get(alpha_2=code[:2])
    if code == DEFAULT_LANGUAGE_CODE:
        return language.name

    translation = translation("iso639-3", pycountry.LOCALES_DIR, languages=[code])
    return translation.gettext(language.name)


def available_language_codes():
    return (
        [str(translation) for translation in babel.list_translations()]
        if babel
        else [DEFAULT_LANGUAGE_CODE]
    )


def reload_translations():
    if not babel:  # pragma: no cover
        return

    from flask_babel import refresh

    return refresh()
