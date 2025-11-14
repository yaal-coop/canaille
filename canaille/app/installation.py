from canaille.backends import Backend


class InstallationException(Exception):
    pass


def install(config, debug=False):
    Backend.instance.install(config)
