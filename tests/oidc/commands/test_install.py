import os

from canaille import create_app
from canaille.commands import cli
from flask_webtest import TestApp


def test_install_keypair(configuration, tmpdir):
    keys_dir = os.path.join(tmpdir, "keys")
    os.makedirs(keys_dir)
    configuration["OIDC"]["JWT"]["PRIVATE_KEY"] = os.path.join(keys_dir, "private.pem")
    configuration["OIDC"]["JWT"]["PUBLIC_KEY"] = os.path.join(keys_dir, "public.pem")

    assert not os.path.exists(configuration["OIDC"]["JWT"]["PRIVATE_KEY"])
    assert not os.path.exists(configuration["OIDC"]["JWT"]["PUBLIC_KEY"])

    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout

    assert os.path.exists(configuration["OIDC"]["JWT"]["PRIVATE_KEY"])
    assert os.path.exists(configuration["OIDC"]["JWT"]["PUBLIC_KEY"])
