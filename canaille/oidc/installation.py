def install(config, debug=False):
    from joserfc import jwk

    if (
        not debug
        or config.get("CANAILLE_OIDC") is None
        or config["CANAILLE_OIDC"].get("ACTIVE_JWKS")
    ):
        return

    key = jwk.generate_key("RSA", 4096)
    config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [key.as_dict()]
