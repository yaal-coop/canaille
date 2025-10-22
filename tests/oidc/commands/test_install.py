from canaille.oidc.installation import install


def test_install_jwks(configuration):
    """Test that ACTIVE_JWKS is generated during installation in debug mode."""
    del configuration["CANAILLE_OIDC"]["ACTIVE_JWKS"]

    install(configuration, debug=False)
    assert "ACTIVE_JWKS" not in configuration["CANAILLE_OIDC"]

    install(configuration, debug=True)
    assert configuration["CANAILLE_OIDC"]["ACTIVE_JWKS"]
