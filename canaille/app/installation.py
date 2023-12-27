from canaille.backends import BaseBackend
from canaille.oidc.installation import install as install_oidc


class InstallationException(Exception):
    pass


def install(config, debug=False):
    install_oidc(config, debug=debug)
    BaseBackend.get().install(config)
