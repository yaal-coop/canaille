def install(config, debug=False):
    from joserfc.jwk import JWKRegistry

    if (
        not debug
        or config.get("CANAILLE_OIDC") is None
        or config["CANAILLE_OIDC"].get("ACTIVE_JWKS")
    ):
        return

    jwk = JWKRegistry.generate_key("RSA", 1024)
    config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [jwk.as_dict()]
