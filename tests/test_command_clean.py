import datetime
from canaille.commands import clean, client
from canaille.models import AuthorizationCode, Token, Client
from werkzeug.security import gen_salt


def test_clean_command(testclient, slapd_connection, client, user):
    AuthorizationCode.ocs_by_name(slapd_connection)
    code = AuthorizationCode(
        oauthCode="my-code",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthRedirectURI="https://foo.bar/callback",
        oauthResponseType="code",
        oauthScope="openid profile",
        oauthNonce="nonce",
        oauthAuthorizationDate=(
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y%m%d%H%M%SZ"),
        oauthAuthorizationLifetime="3600",
        oauthCodeChallenge="challenge",
        oauthCodeChallengeMethod="method",
        oauthRevokation="",
    )
    code.save(slapd_connection)

    Token.ocs_by_name(slapd_connection)
    token = Token(
        oauthAccessToken="my-token",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthTokenType=None,
        oauthRefreshToken=gen_salt(48),
        oauthScope="openid profile",
        oauthIssueDate=(datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
            "%Y%m%d%H%M%SZ"
        ),
        oauthTokenLifetime=str(3600),
    )
    token.save(slapd_connection)

    assert AuthorizationCode.get("my-code", conn=slapd_connection)
    assert Token.get("my-token", conn=slapd_connection)
    assert code.is_expired()
    assert token.is_expired()

    runner = testclient.app.test_cli_runner()
    runner.invoke(clean)

    assert not AuthorizationCode.get("my-code", conn=slapd_connection)
    assert not Token.get("my-token", conn=slapd_connection)


def test_client_create(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()
    runner.invoke(
        client,
        args=[
            "create",
            "--id=id",
            "--name=name",
            "--contact=contact@mydomain.tld",
            "--uri=https://mydomain.tld",
            "--redirect-uri=https://mydomain.tld/redirect",
            "--logo-uri=https://mydomain.tld/logo.png",
            "--secret=secret",
            "--secret-exp-data=01-01-1970",
            "--grant-type=authorization_code",
            "--response-type=code",
            "--scope=openid profile",
            "--tos-uri=https://mydomain.tld/tos",
            "--policy-uri=https://mydomain.tld/policty",
            "--jwk=0",
            "--jwk-uri=https://mydomain.tld/jwk",
            "--token-endpoint-auth-method=none",
            "--software-id=software",
            "--software-version=0",
        ],
    )
