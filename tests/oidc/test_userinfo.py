from authlib.oidc.core import UserInfo
from canaille.models import User
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
        "website": "https://john.example",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile email")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.example",
        "email": "john@doe.com",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile address")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.example",
        "address": "1235, somewhere",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile phone")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.example",
        "phone_number": "555-000-000",
    }
    assert generate_user_claims(user, claims_from_scope("openid profile groups")) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.example",
        "groups": ["foo"],
    }


def test_userinfo(testclient, token, user, foo_group):
    token.scope = ["openid"]
    token.save()
    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=403,
    )

    token.scope = ["openid profile"]
    token.save()
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
        "website": "https://john.example",
    }

    token.scope = ["openid profile email"]
    token.save()
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
        "website": "https://john.example",
        "email": "john@doe.com",
    }

    token.scope = ["openid profile address"]
    token.save()
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
        "website": "https://john.example",
        "address": "1235, somewhere",
    }

    token.scope = ["openid profile phone"]
    token.save()
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
        "website": "https://john.example",
        "phone_number": "555-000-000",
    }

    token.scope = ["openid profile groups"]
    token.save()
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
        "website": "https://john.example",
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
DEFAULT_JWT_MAPPING_CONFIG = {
    "SUB": "{{ user.uid[0] }}",
    "NAME": "{{ user.cn[0] }}",
    "PHONE_NUMBER": "{{ user.telephoneNumber[0] }}",
    "EMAIL": "{{ user.mail[0] }}",
    "GIVEN_NAME": "{{ user.givenName[0] }}",
    "FAMILY_NAME": "{{ user.sn[0] }}",
    "PREFERRED_USERNAME": "{{ user.displayName }}",
    "LOCALE": "{{ user.preferredLanguage }}",
}


def test_generate_user_standard_claims_with_default_config(
    testclient, slapd_connection, user
):
    user.preferredLanguage = ["fr"]

    data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert data == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "email": "john@doe.com",
        "locale": "fr",
        "phone_number": "555-000-000",
    }


def test_custom_config_format_claim_is_well_formated(
    testclient, slapd_connection, user
):
    jwt_mapping_config = DEFAULT_JWT_MAPPING_CONFIG.copy()
    jwt_mapping_config["EMAIL"] = "{{ user.uid[0] }}@mydomain.tld"

    data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "user@mydomain.tld"


def test_claim_is_omitted_if_empty(testclient, slapd_connection, user):
    # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
    # it's better to not insert a null or empty string value
    user.mail = ""
    user.save()

    data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert "email" not in data
