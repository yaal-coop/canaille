import os

import toml

from canaille import create_app
from canaille.app.flask import set_parameter_in_url_query


def test_set_parameter_in_url_query():
    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", hello="world")
        == "https://auth.mydomain.tld?foo=baz&hello=world"
    )


def test_environment_configuration(configuration, tmp_path):
    config_path = os.path.join(tmp_path, "config.toml")
    with open(config_path, "w") as fd:
        toml.dump(configuration, fd)

    os.environ["CONFIG"] = config_path
    app = create_app()
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "admin@mydomain.tld"

    del os.environ["CONFIG"]
    os.remove(config_path)
