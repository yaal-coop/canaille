import datetime
from canaille.commands import cli
from canaille.models import AuthorizationCode, Token
from werkzeug.security import gen_salt


def test_clean_command(testclient, slapd_connection, client, user):
    AuthorizationCode.ldap_object_classes(slapd_connection)
    code = AuthorizationCode(
        oauthCode="my-code",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthRedirectURI="https://foo.bar/callback",
        oauthResponseType="code",
        oauthScope="openid profile",
        oauthNonce="nonce",
        oauthAuthorizationDate=(datetime.datetime.now() - datetime.timedelta(days=1)),
        oauthAuthorizationLifetime="3600",
        oauthCodeChallenge="challenge",
        oauthCodeChallengeMethod="method",
        oauthRevokation="",
    )
    code.save(slapd_connection)

    Token.ldap_object_classes(slapd_connection)
    token = Token(
        oauthAccessToken="my-token",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthTokenType=None,
        oauthRefreshToken=gen_salt(48),
        oauthScope="openid profile",
        oauthIssueDate=(datetime.datetime.now() - datetime.timedelta(days=1)),
        oauthTokenLifetime=str(3600),
    )
    token.save(slapd_connection)

    assert AuthorizationCode.get("my-code", conn=slapd_connection)
    assert Token.get("my-token", conn=slapd_connection)
    assert code.is_expired()
    assert token.is_expired()

    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["clean"])

    assert not AuthorizationCode.get("my-code", conn=slapd_connection)
    assert not Token.get("my-token", conn=slapd_connection)
