from canaille.oidc.configuration import JWTSettings
from canaille.oidc.oauth import claims_from_scope
from canaille.oidc.oauth import generate_user_claims


def test_claims_from_scope():
    assert claims_from_scope("openid") == {"sub"}
    assert claims_from_scope("openid profile") == {
        "sub",
        "name",
        "family_name",
        "given_name",
        "nickname",
        "preferred_username",
        "profile",
        "picture",
        "website",
        "gender",
        "birthdate",
        "zoneinfo",
        "locale",
        "updated_at",
    }
    assert claims_from_scope("openid profile email") == {
        "sub",
        "name",
        "family_name",
        "given_name",
        "nickname",
        "preferred_username",
        "profile",
        "picture",
        "website",
        "gender",
        "birthdate",
        "zoneinfo",
        "locale",
        "updated_at",
        "email",
        "email_verified",
    }
    assert claims_from_scope("openid profile address") == {
        "sub",
        "name",
        "family_name",
        "given_name",
        "nickname",
        "preferred_username",
        "profile",
        "picture",
        "website",
        "gender",
        "birthdate",
        "zoneinfo",
        "locale",
        "updated_at",
        "address",
    }
    assert claims_from_scope("openid profile phone") == {
        "sub",
        "name",
        "family_name",
        "given_name",
        "nickname",
        "preferred_username",
        "profile",
        "picture",
        "website",
        "gender",
        "birthdate",
        "zoneinfo",
        "locale",
        "updated_at",
        "phone_number",
        "phone_number_verified",
    }
    assert claims_from_scope("openid profile groups") == {
        "sub",
        "name",
        "family_name",
        "given_name",
        "nickname",
        "preferred_username",
        "profile",
        "picture",
        "website",
        "gender",
        "birthdate",
        "zoneinfo",
        "locale",
        "updated_at",
        "groups",
    }


def test_generate_user_claims(user, foo_group):
    assert generate_user_claims(user, claims_from_scope("openid")) == {"sub": "user"}
    assert generate_user_claims(user, claims_from_scope("openid profile")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile email")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "email": "john@doe.test",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile address")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "address": "1235, somewhere",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile phone")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "phone_number": "555-000-000",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile groups")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "groups": ["foo"],
    }


def test_userinfo(testclient, token, user, foo_group, backend):
    token.scope = ["openid"]
    backend.save(token)
    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=403,
    )

    token.scope = ["openid", "profile"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert res.json == {
        "sub": "user",
        "given_name": "John",
        "family_name": "Doe",
        "name": "John (johnny) Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
    }

    token.scope = ["openid", "profile", "email"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert res.json == {
        "sub": "user",
        "given_name": "John",
        "family_name": "Doe",
        "name": "John (johnny) Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "email": "john@doe.test",
    }

    token.scope = ["openid", "profile", "address"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert res.json == {
        "sub": "user",
        "family_name": "Doe",
        "given_name": "John",
        "name": "John (johnny) Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "address": "1235, somewhere",
    }

    token.scope = ["openid", "profile", "phone"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert res.json == {
        "sub": "user",
        "given_name": "John",
        "family_name": "Doe",
        "name": "John (johnny) Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "phone_number": "555-000-000",
    }

    token.scope = ["openid", "profile", "groups"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
    )
    assert res.json == {
        "sub": "user",
        "given_name": "John",
        "family_name": "Doe",
        "name": "John (johnny) Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "groups": ["foo"],
    }


STANDARD_CLAIMS = [
    "sub",
    "name",
    "ugiven_name",
    "family_name",
    "middle_name",
    "nickname",
    "preferred_username",
    "profile",
    "picture",
    "website",
    "email",
    "email_verified",
    "gender",
    "birthdate",
    "zoneinfo",
    "locale",
    "phone_number",
    "phone_number_verified",
    "address",
    "updated_at",
]


def test_generate_user_standard_claims_with_default_config(testclient, backend, user):
    user.preferred_language = "fr"

    default_jwt_mapping = JWTSettings().model_dump()
    data = generate_user_claims(user, STANDARD_CLAIMS, default_jwt_mapping)

    assert data == {
        "address": "1235, somewhere",
        "sub": "user",
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "email": "john@doe.test",
        "locale": "fr",
        "phone_number": "555-000-000",
        "website": "https://john.test",
    }


def test_custom_config_format_claim_is_well_formated(testclient, backend, user):
    jwt_mapping_config = JWTSettings().model_dump()
    jwt_mapping_config["EMAIL"] = "{{ user.user_name }}@mydomain.test"

    data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "user@mydomain.test"


def test_claim_is_omitted_if_empty(testclient, backend, user):
    # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
    # it's better to not insert a null or empty string value
    user.emails = []
    backend.save(user)

    default_jwt_mapping = JWTSettings().model_dump()
    data = generate_user_claims(user, STANDARD_CLAIMS, default_jwt_mapping)

    assert "email" not in data
