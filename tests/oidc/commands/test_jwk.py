import json

from joserfc.jwk import JWKRegistry

from canaille.commands import cli


def test_create_rsa_key(testclient):
    """Test the default RSA key creation command."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["jwk", "create", "rsa"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "RSA")


def test_create_rsa_key_with_size(testclient):
    """Test the RSA key creation command with a size parameter."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["jwk", "create", "rsa", "--size", "1024"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "RSA")


def test_create_oct_key(testclient):
    """Test the default Oct key creation command."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["jwk", "create", "oct"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "oct")


def test_create_oct_key_with_size(testclient):
    """Test the Oct key creation command with a size parameter."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["jwk", "create", "oct", "--size", "128"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "oct")


def test_create_ec_key(testclient):
    """Test the default EC key creation command."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["jwk", "create", "ec"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "EC")


def test_create_ec_key_with_crv(testclient):
    """Test the EC key creation command with a crv param."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["jwk", "create", "ec", "--crv", "secp256k1"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "EC")


def test_create_opk_key(testclient):
    """Test the default OPK key creation command."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["jwk", "create", "okp"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "OKP")


def test_create_opk_key_with_crv(testclient):
    """Test the OPK key creation command with a crv param."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["jwk", "create", "okp", "--crv", "X448"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    JWKRegistry.import_key(payload, "OKP")
