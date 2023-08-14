from canaille.oidc.installation import install


def test_install_keypair(configuration):
    del configuration["OIDC"]["JWT"]["PRIVATE_KEY"]
    del configuration["OIDC"]["JWT"]["PUBLIC_KEY"]

    install(configuration, debug=False)
    assert "PRIVATE_KEY" not in configuration["OIDC"]["JWT"]
    assert "PUBLIC_KEY" not in configuration["OIDC"]["JWT"]

    install(configuration, debug=True)
    assert configuration["OIDC"]["JWT"]["PRIVATE_KEY"]
    assert configuration["OIDC"]["JWT"]["PUBLIC_KEY"]
