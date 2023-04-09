from canaille.oidc.installation import install as install_oidc


class InstallationException(Exception):
    pass


def install(config):
    install_oidc(config)
