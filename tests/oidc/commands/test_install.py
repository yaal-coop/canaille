from canaille.oidc.installation import install


def test_install_keypair(configuration):
    del configuration["CANAILLE_OIDC"]["JWT"]["PRIVATE_KEY"]
    del configuration["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"]

    install(configuration, debug=False)
    assert "PRIVATE_KEY" not in configuration["CANAILLE_OIDC"]["JWT"]
    assert "PUBLIC_KEY" not in configuration["CANAILLE_OIDC"]["JWT"]

    install(configuration, debug=True)
    assert configuration["CANAILLE_OIDC"]["JWT"]["PRIVATE_KEY"]
    assert configuration["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"]
