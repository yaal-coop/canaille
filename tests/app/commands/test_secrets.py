import pytest

from canaille.app import models
from canaille.commands import cli


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_OIDC"] = {"ENABLE_OIDC": True}
    return configuration


def test_reencrypt(testclient, cli_runner, backend, user):
    """Secrets encrypted with a previous key are encrypted with the current one."""
    client = models.Client(client_id="client", client_secret="client-secret")
    backend.save(client)

    old_key = testclient.app.config["SECRET_KEY"]
    testclient.app.config["SECRET_KEY"] = "new-secret-key"
    testclient.app.config["SECRET_KEY_FALLBACKS"] = [old_key]

    res = cli_runner.invoke(cli, ["secrets", "reencrypt"])
    assert res.exit_code == 0, res.stderr
    assert res.stdout == "2 secrets encrypted\n"

    testclient.app.config["SECRET_KEY_FALLBACKS"] = []
    backend.reload(client)
    backend.reload(user)
    assert client.client_secret == "client-secret"
    assert user.secret_token == "fefe9b10"

    backend.delete(client)


def test_reencrypt_without_secret_key(testclient, cli_runner, backend):
    testclient.app.config["SECRET_KEY"] = None

    res = cli_runner.invoke(cli, ["secrets", "reencrypt"])
    assert res.exit_code == 1
    assert "SECRET_KEY is not set" in res.stderr


def test_reencrypt_undecryptable_secrets(testclient, cli_runner, backend, user):
    """Secrets encrypted with an unknown key are reported."""
    if "memory" in backend.__class__.__module__:
        pytest.skip()

    testclient.app.config["SECRET_KEY"] = "new-secret-key"

    res = cli_runner.invoke(cli, ["secrets", "reencrypt"])
    assert res.exit_code == 1
    assert res.stdout == "0 secrets encrypted\n"
    assert "1 secrets cannot be decrypted" in res.stderr
