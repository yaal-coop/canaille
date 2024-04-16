from canaille.backends import Backend
from canaille.oidc.installation import install as install_oidc


class InstallationException(Exception):
    pass


def install(config, debug=False):
    install_oidc(config, debug=debug)
    Backend.instance.install(config)
