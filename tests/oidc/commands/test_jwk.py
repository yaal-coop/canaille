import json

import tomlkit
from joserfc import jwk

from canaille.commands import cli


def test_create_rsa_key(cli_runner):
    """Test the default RSA key creation command."""
    res = cli_runner.invoke(cli, ["jwk", "create", "rsa"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "RSA")

def test_create_rsa_key_format_toml(cli_runner):
    """Test the RSA key creation command with output toml."""
    res = cli_runner.invoke(cli, ["jwk", "create", "rsa", "--format", "toml"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("KEY=" + res.stdout).unwrap()
    jwk.import_key(payload["KEY"], "RSA")


def test_create_rsa_key_with_size(cli_runner):
    """Test the RSA key creation command with a size parameter."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "rsa", "--size", "1024"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "RSA")


def test_create_oct_key(cli_runner):
    """Test the default Oct key creation command."""
    res = cli_runner.invoke(cli, ["jwk", "create", "oct"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "oct")

def test_create_oct_key_format_toml(cli_runner):
    """Test the Oct key creation command with output toml."""
    res = cli_runner.invoke(cli, ["jwk", "create", "oct", "--format", "toml"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("KEY=" + res.stdout).unwrap()
    jwk.import_key(payload["KEY"], "oct")

def test_create_oct_key_with_size(cli_runner):
    """Test the Oct key creation command with a size parameter."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "oct", "--size", "128"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "oct")


def test_create_ec_key(cli_runner):
    """Test the default EC key creation command."""
    res = cli_runner.invoke(cli, ["jwk", "create", "ec"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "EC")

def test_create_ec_key_format_toml(cli_runner):
    """Test the EC key creation command with output toml."""
    res = cli_runner.invoke(cli, ["jwk", "create", "ec", "--format", "toml"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("KEY=" + res.stdout).unwrap()
    jwk.import_key(payload["KEY"], "EC")


def test_create_ec_key_with_crv(cli_runner):
    """Test the EC key creation command with a crv param."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "ec", "--crv", "secp256k1"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "EC")


def test_create_opk_key(cli_runner):
    """Test the default OPK key creation command."""
    res = cli_runner.invoke(cli, ["jwk", "create", "okp"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "OKP")

def test_create_okp_key_format_toml(cli_runner):
    """Test the OKP key creation command with output toml."""
    res = cli_runner.invoke(cli, ["jwk", "create", "okp", "--format", "toml"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("KEY=" + res.stdout).unwrap()
    jwk.import_key(payload["KEY"], "OKP")

def test_create_opk_key_with_crv(cli_runner):
    """Test the OPK key creation command with a crv param."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "okp", "--crv", "X448"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "OKP")
