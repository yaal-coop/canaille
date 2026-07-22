import json

import tomlkit
from joserfc import jwk
from joserfc.jwk import OctKey

from canaille.commands import cli
from canaille.oidc.provider import _get_signing_key


def test_create_rsa_key(cli_runner):
    """Test the default RSA key creation command."""
    res = cli_runner.invoke(cli, ["jwk", "create", "rsa"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "RSA")


def test_create_rsa_key_format_json(cli_runner):
    """Test the RSA key creation command with explicit --format json."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "rsa", "--format", "json"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "RSA")


def test_create_rsa_key_format_toml(cli_runner):
    """Test the RSA key creation command with output toml."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "rsa", "--format", "toml"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("_=" + res.stdout).unwrap()["_"]
    jwk.import_key(payload, "RSA")


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
    res = cli_runner.invoke(
        cli, ["jwk", "create", "oct", "--format", "toml"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("_=" + res.stdout).unwrap()["_"]
    jwk.import_key(payload, "oct")


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
    res = cli_runner.invoke(
        cli, ["jwk", "create", "ec", "--format", "toml"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("_=" + res.stdout).unwrap()["_"]
    jwk.import_key(payload, "EC")


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
    res = cli_runner.invoke(
        cli, ["jwk", "create", "okp", "--format", "toml"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = tomlkit.loads("_=" + res.stdout).unwrap()["_"]
    jwk.import_key(payload, "OKP")


def test_create_opk_key_with_crv(cli_runner):
    """Test the OPK key creation command with a crv param."""
    res = cli_runner.invoke(
        cli, ["jwk", "create", "okp", "--crv", "X448"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    jwk.import_key(payload, "OKP")


def test_export_json(cli_runner, server_jwk, old_server_jwk):
    """Export the key metadata as JSON, active and inactive by default."""
    res = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    assert res.exit_code == 0, res.output

    payload = json.loads(res.stdout)
    assert {entry["kid"] for entry in payload} == {server_jwk.kid, old_server_jwk.kid}

    for entry in payload:
        assert entry["kty"] == "RSA"
        assert entry["alg"] == "RS512"
        assert entry["use"] == "sig"
        # The raw key material is not part of the JSON output.
        assert "public_pem" not in entry


def test_export_json_active_only(cli_runner, server_jwk, old_server_jwk):
    """The --active-only flag excludes the inactive keys."""
    res = cli_runner.invoke(
        cli, ["jwk", "export", "--active-only"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output

    payload = json.loads(res.stdout)
    kids = {entry["kid"] for entry in payload}
    assert kids == {server_jwk.kid}
    assert old_server_jwk.kid not in kids


def test_export_json_single_key(cli_runner, server_jwk):
    """Passing a KID exports that single key as a JSON object."""
    res = cli_runner.invoke(
        cli, ["jwk", "export", server_jwk.kid], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output

    payload = json.loads(res.stdout)
    assert isinstance(payload, dict)
    assert payload["kid"] == server_jwk.kid
    assert payload["kty"] == "RSA"
    assert payload["alg"] == "RS512"


def test_export_pem(cli_runner):
    """The pem format emits the raw public keys and no private material."""
    res = cli_runner.invoke(
        cli, ["jwk", "export", "--format", "pem"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output

    assert res.stdout.count("-----BEGIN PUBLIC KEY-----") == 2
    assert "PRIVATE" not in res.stdout


def test_export_pem_single_key(cli_runner, server_jwk):
    """Passing a KID with the pem format emits that single public key."""
    res = cli_runner.invoke(
        cli,
        ["jwk", "export", server_jwk.kid, "--format", "pem"],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert res.stdout.startswith("-----BEGIN PUBLIC KEY-----")
    assert res.stdout.count("-----BEGIN PUBLIC KEY-----") == 1

    # The exported PEM is a public key that hashes back to the requested kid.
    imported = jwk.import_key(res.stdout.encode(), "RSA")
    imported.ensure_kid()
    assert imported.kid == server_jwk.kid
    assert "d" not in imported.as_dict(private=False)


def test_export_unknown_kid(cli_runner):
    """Selecting an unknown KID fails."""
    res = cli_runner.invoke(cli, ["jwk", "export", "unknown"], catch_exceptions=False)
    assert res.exit_code == 1
    assert "No key found" in res.output


def test_export_symmetric_kid(cli_runner, app):
    """Selecting a symmetric key by KID fails as it has no public part."""
    oct_key = OctKey.generate_key(128, auto_kid=True)
    app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"].append(oct_key.as_dict(private=True))

    res = cli_runner.invoke(cli, ["jwk", "export", oct_key.kid], catch_exceptions=False)
    assert res.exit_code == 1
    assert "symmetric" in res.output


def test_export_matches_signing_key(cli_runner, app):
    """The exported (kid, alg) match what the provider actually signs with."""
    res = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    payload = json.loads(res.stdout)

    with app.app_context():
        signing_key, alg = _get_signing_key(None)

    entry = next(entry for entry in payload if entry["kid"] == signing_key.kid)
    assert entry["alg"] == alg


def test_export_is_deterministic(cli_runner):
    """Two runs produce a byte-identical output."""
    first = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    second = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    assert first.stdout == second.stdout


def test_export_skips_symmetric_keys(cli_runner, app, server_jwk):
    """Symmetric keys have no public part and are skipped with a warning."""
    oct_key = OctKey.generate_key(128, auto_kid=True)
    app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"].append(oct_key.as_dict(private=True))

    res = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert "Skipping symmetric key" in res.stderr

    payload = json.loads(res.stdout)
    kids = {entry["kid"] for entry in payload}
    assert oct_key.kid not in kids
    assert server_jwk.kid in kids


def test_export_refuses_autogenerated_keys(cli_runner, app):
    """Refuse to export the non-persistent auto-generated keys."""
    app.extensions["canaille_oidc_jwks_autogenerated"] = True

    res = cli_runner.invoke(cli, ["jwk", "export"], catch_exceptions=False)
    assert res.exit_code == 1
    assert "ACTIVE_JWKS" in res.output
