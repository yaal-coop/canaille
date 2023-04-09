import gettext

import pycountry
from flask import current_app
from flask import g
from flask import request
from flask_babel import Babel
from flask_babel import get_locale

DEFAULT_LANGUAGE_CODE = "en"

babel = Babel()


def setup_i18n(app):
    babel.init_app(app, locale_selector=locale_selector)

    @app.before_request
    def before_request():
        g.available_language_codes = available_language_codes()

    @app.context_processor
    def global_processor():
        return {
            "locale": get_locale(),
        }


def locale_selector():
    from .flask import current_user

    user = current_user()
    available_language_codes = getattr(g, "available_language_codes", [])
    if user is not None and user.preferredLanguage in available_language_codes:
        return user.preferredLanguage

    if current_app.config.get("LANGUAGE"):
        return current_app.config.get("LANGUAGE")

    return request.accept_languages.best_match(available_language_codes)


def native_language_name_from_code(code):
    language = pycountry.languages.get(alpha_2=code[:2])
    if code == DEFAULT_LANGUAGE_CODE:
        return language.name

    translation = gettext.translation(
        "iso639-3", pycountry.LOCALES_DIR, languages=[code]
    )
    return translation.gettext(language.name)


def available_language_codes():
    return [str(translation) for translation in babel.list_translations()]
