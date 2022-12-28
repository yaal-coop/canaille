from flask_babel import lazy_gettext as _

SCOPE_DETAILS = {
    "profile": (
        "id card outline",
        _("Personnal information about yourself, such as your name or your gender."),
    ),
    "email": ("at", _("Your email address.")),
    "address": ("envelope open outline", _("Your postal address.")),
    "phone": ("phone", _("Your phone number.")),
    "groups": ("users", _("Groups you are belonging to")),
}
