import datetime

from canaille.commands import cli
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
from werkzeug.security import gen_salt


def test_clean_command(testclient, backend, client, user):
    valid_code = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-valid-code",
        client=client,
        subject=user,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope="openid profile",
        nonce="nonce",
        issue_date=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0),
        lifetime=3600,
        challenge="challenge",
        challenge_method="method",
        revokation="",
    )
    valid_code.save()
    expired_code = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-expired-code",
        client=client,
        subject=user,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope="openid profile",
        nonce="nonce",
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
        challenge="challenge",
        challenge_method="method",
        revokation="",
    )
    expired_code.save()

    valid_token = Token(
        token_id=gen_salt(48),
        access_token="my-valid-token",
        client=client,
        subject=user,
        type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ),
        lifetime=3600,
    )
    valid_token.save()
    expired_token = Token(
        token_id=gen_salt(48),
        access_token="my-expired-token",
        client=client,
        subject=user,
        type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=(
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
            - datetime.timedelta(days=1)
        ),
        lifetime=3600,
    )
    expired_token.save()

    assert AuthorizationCode.get(code="my-expired-code")
    assert Token.get(access_token="my-expired-token")
    assert expired_code.is_expired()
    assert expired_token.is_expired()

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["clean"])
    assert res.exit_code == 0, res.stdout

    assert AuthorizationCode.query() == [valid_code]
    assert Token.query() == [valid_token]
