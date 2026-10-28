import datetime

from werkzeug.security import gen_salt

from canaille.app import models
from canaille.commands import cli


def test_clean_command(cli_runner, backend, client, user):
    """Test that the clean command removes expired authorization codes, tokens and device codes."""
    valid_code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-valid-code",
        client=client,
        subject=user,
        redirect_uri="https://foobar.test/callback",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        lifetime=3600,
        challenge="challenge",
        challenge_method="method",
    )
    backend.save(valid_code)
    expired_code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-expired-code",
        client=client,
        subject=user,
        redirect_uri="https://foobar.test/callback",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=(
            datetime.datetime.now(datetime.UTC).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
        challenge="challenge",
        challenge_method="method",
    )
    backend.save(expired_code)

    valid_token = models.Token(
        token_id=gen_salt(48),
        access_token="my-valid-token",
        client=client,
        subject=user,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=(datetime.datetime.now(datetime.UTC).replace(microsecond=0)),
        lifetime=3600,
    )
    backend.save(valid_token)
    expired_token = models.Token(
        token_id=gen_salt(48),
        access_token="my-expired-token",
        client=client,
        subject=user,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=(
            datetime.datetime.now(datetime.UTC).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
    )
    backend.save(expired_token)

    valid_device_code = models.DeviceCode(
        device_code_id=gen_salt(48),
        device_code="my-valid-device-code",
        user_code="VALI-DCOD",
        client=client,
        scope=["openid", "profile"],
        status="pending",
        issue_date=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
        lifetime=3600,
    )
    backend.save(valid_device_code)
    expired_device_code = models.DeviceCode(
        device_code_id=gen_salt(48),
        device_code="my-expired-device-code",
        user_code="EXPI-REDC",
        client=client,
        scope=["openid", "profile"],
        status="denied",
        issue_date=(
            datetime.datetime.now(datetime.UTC).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
    )
    backend.save(expired_device_code)

    assert backend.get(models.AuthorizationCode, code="my-expired-code")
    assert backend.get(models.Token, access_token="my-expired-token")
    assert expired_code.is_expired()
    assert expired_token.is_expired()

    res = cli_runner.invoke(cli, ["clean"])
    assert res.exit_code == 0, res.stdout

    assert backend.get(models.AuthorizationCode) == valid_code
    assert backend.get(models.Token, subject=user) == valid_token
    assert backend.get(models.DeviceCode) == valid_device_code


def test_clean_command_deleted_users(
    cli_runner, testclient, backend, client, consent, monkeypatch
):
    """The clean command removes the consents and codes of deleted users."""
    user = models.User(
        user_name="temp-user",
        formatted_name="Temp User",
        family_name="User",
    )
    backend.save(user)
    orphan_consent = models.Consent(
        consent_id=gen_salt(48),
        client=client,
        subject=user,
        scope=["openid"],
        issue_date=datetime.datetime.now(datetime.UTC),
    )
    backend.save(orphan_consent)
    orphan_code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=gen_salt(48),
        client=client,
        subject=user,
        redirect_uri="https://foobar.test/callback",
        response_type="code",
        scope=["openid"],
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=3600,
    )
    backend.save(orphan_code)
    orphan_consent_id = orphan_consent.consent_id
    orphan_code_id = orphan_code.authorization_code_id

    with monkeypatch.context() as patch:
        patch.setitem(testclient.app.config["CANAILLE_OIDC"], "ENABLE_OIDC", False)
        backend.delete(user)

    res = cli_runner.invoke(cli, ["clean"])
    assert res.exit_code == 0, res.stdout

    assert not backend.get(models.Consent, consent_id=orphan_consent_id)
    assert not backend.get(
        models.AuthorizationCode, authorization_code_id=orphan_code_id
    )
    assert backend.get(models.Consent, consent_id=consent.consent_id)
