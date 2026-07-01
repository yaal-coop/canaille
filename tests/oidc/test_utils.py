from canaille.oidc.utils import unique_scopes


def test_unique_scopes():
    assert unique_scopes("openid profile openid email profile") == [
        "openid",
        "profile",
        "email",
    ]
    assert unique_scopes("openid   profile") == ["openid", "profile"]
    assert unique_scopes("") == []
    assert unique_scopes(None) == []
