import datetime

from canaille.commands import cli
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
from werkzeug.security import gen_salt


def test_clean_command(testclient, slapd_connection, client, user):
    AuthorizationCode.ldap_object_classes(slapd_connection)
    code = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-code",
        client=client.dn,
        subject=user.dn,
        redirect_uri="https://foo.bar/callback",
        response_type="code",
        scope="openid profile",
        nonce="nonce",
        issue_date=(datetime.datetime.now() - datetime.timedelta(days=1)),
        lifetime="3600",
        challenge="challenge",
        challenge_method="method",
        revokation="",
    )
    code.save(slapd_connection)

    Token.ldap_object_classes(slapd_connection)
    token = Token(
        token_id=gen_salt(48),
        access_token="my-token",
        client=client.dn,
        subject=user.dn,
        type=None,
        refresh_token=gen_salt(48),
        scope="openid profile",
        issue_date=(datetime.datetime.now() - datetime.timedelta(days=1)),
        lifetime=str(3600),
    )
    token.save(slapd_connection)

    assert AuthorizationCode.get(code="my-code", conn=slapd_connection)
    assert Token.get(access_token="my-token", conn=slapd_connection)
    assert code.is_expired()
    assert token.is_expired()

    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["clean"])

    assert not AuthorizationCode.get(code="my-code", conn=slapd_connection)
    assert not Token.get(access_token="my-token", conn=slapd_connection)
