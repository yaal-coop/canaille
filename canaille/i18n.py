import gettext

import pycountry

DEFAULT_LANGUAGE_CODE = "en"


def native_language_name_from_code(code):
    language = pycountry.languages.get(alpha_2=code[:2])
    if code == DEFAULT_LANGUAGE_CODE:
        return language.name

    translation = gettext.translation(
        "iso639-3", pycountry.LOCALES_DIR, languages=[code]
    )
    return translation.gettext(language.name)


def available_language_codes(babel):
    return [str(translation) for translation in babel.list_translations()] + [
        DEFAULT_LANGUAGE_CODE
    ]
