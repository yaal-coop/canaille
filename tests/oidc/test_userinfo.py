from unittest import mock

from joserfc import jwt

from canaille.oidc.configuration import UserInfoMappingSettings
from canaille.oidc.oauth import generate_user_claims


def test_generate_user_claims(user, foo_group):
    assert generate_user_claims(user) == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "locale": "en",
        "website": "https://john.test",
        "address": {
            "formatted": "1234, some street, 6789 some city, some state",
            "locality": "some city",
            "postal_code": "6789",
            "region": "some state",
            "street_address": "1234, some street",
        },
        "email": "john@doe.test",
        "phone_number": "555-000-000",
        "groups": ["foo"],
        "updated_at": user.last_modified.timestamp(),
    }


def test_get_userinfo(testclient, token, user, foo_group, backend):
    token.scope = ["openid"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=200,
    )
    assert res.json == {
        "sub": "user",
    }


def test_get_userinfo_jwt(testclient, token, user, client, backend, server_jwk):
    client.userinfo_signed_response_alg = "RS256"
    backend.save(client)

    res = testclient.get(
        "/oauth/userinfo",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/jwt",
        },
        status=200,
    )
    assert res.headers["Content-Type"] == "application/jwt"
    token = jwt.decode(res.text, server_jwk)
    assert token.claims == {
        "sub": "user",
        "name": "John (johnny) Doe",
        "given_name": "John",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "website": "https://john.test",
        "locale": "en",
        "updated_at": mock.ANY,
        "iss": "http://canaille.test",
        "aud": client.client_id,
    }


def test_post_userinfo(testclient, token, user, foo_group, backend):
    token.scope = ["openid"]
    backend.save(token)
    res = testclient.post(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=200,
    )
    assert res.json == {
        "sub": "user",
    }


def test_userinfo_scopes(testclient, token, user, foo_group, backend):
    token.scope = ["openid"]
    backend.save(token)
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=200,
    )
    assert res.json == {
        "sub": "user",
    }

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
        "updated_at": user.last_modified.timestamp(),
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
        "updated_at": user.last_modified.timestamp(),
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
        "address": {
            "formatted": "1234, some street, 6789 some city, some state",
            "locality": "some city",
            "postal_code": "6789",
            "region": "some state",
            "street_address": "1234, some street",
        },
        "updated_at": user.last_modified.timestamp(),
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
        "updated_at": user.last_modified.timestamp(),
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
        "updated_at": user.last_modified.timestamp(),
    }


def test_generate_user_standard_claims_with_default_config(testclient, backend, user):
    user.preferred_language = "fr"

    default_jwt_mapping = UserInfoMappingSettings().model_dump()
    data = generate_user_claims(user, default_jwt_mapping)

    assert data == {
        "address": {
            "formatted": "1234, some street, 6789 some city, some state",
            "locality": "some city",
            "postal_code": "6789",
            "region": "some state",
            "street_address": "1234, some street",
        },
        "sub": "user",
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "given_name": "John",
        "preferred_username": "Johnny",
        "email": "john@doe.test",
        "locale": "fr",
        "phone_number": "555-000-000",
        "website": "https://john.test",
        "updated_at": mock.ANY,
    }


def test_custom_config_format_claim_is_well_formated(testclient, backend, user):
    userinfo_mapping_config = UserInfoMappingSettings().model_dump()
    userinfo_mapping_config["EMAIL"] = "{{ user.user_name }}@mydomain.test"

    data = generate_user_claims(user, userinfo_mapping_config)

    assert data["email"] == "user@mydomain.test"


def test_claim_is_omitted_if_empty(testclient, backend, user):
    # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
    # it's better to not insert a null or empty string value
    user.emails = []
    backend.save(user)

    default_userinfo_mapping = UserInfoMappingSettings().model_dump()
    data = generate_user_claims(user, default_userinfo_mapping)

    assert "email" not in data
