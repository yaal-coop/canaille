from urllib.parse import urlparse

from flask import current_app

from canaille.app.i18n import lazy_gettext as _

SCOPE_DETAILS = {
    "profile": (
        "id card outline",
        _("Info about yourself, such as your name."),
    ),
    "email": ("at", _("Your e-mail address.")),
    "address": ("envelope open outline", _("Your postal address.")),
    "phone": ("phone", _("Your phone number.")),
    "groups": ("users", _("Groups you belong to.")),
}

def is_trusted_domain(domain):
    if not domain:
        return False

    parsed = urlparse(domain)
    hostname = parsed.hostname
    if not hostname:
        return False

    trusted_domains = current_app.config["CANAILLE_OIDC"]["TRUSTED_DOMAINS"]
    for domain in trusted_domains:
        # Wildcard match: .example.com matches example.com and all subdomains
        if domain.startswith("."):
            domain_without_dot = domain[1:]
            if hostname == domain_without_dot or hostname.endswith(domain):
                return True

        # Exact match only for non-wildcard domains
        elif hostname == domain:
            return True

    return False