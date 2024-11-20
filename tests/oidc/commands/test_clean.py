import datetime

from werkzeug.security import gen_salt

from canaille.app import models
from canaille.commands import cli


def test_clean_command(testclient, backend, client, user):
    valid_code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-valid-code",
        client=client,
        subject=user,
        redirect_uri="https://foobar.test/callback",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0),
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
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
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
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ),
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
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
    )
    backend.save(expired_token)

    assert backend.get(models.AuthorizationCode, code="my-expired-code")
    assert backend.get(models.Token, access_token="my-expired-token")
    assert expired_code.is_expired()
    assert expired_token.is_expired()

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["clean"])
    assert res.exit_code == 0, res.stdout

    assert backend.get(models.AuthorizationCode) == valid_code
    assert backend.get(models.Token) == valid_token
