from canaille.models import User
from canaille.oauth2utils import generate_user_claims

STANDARD_CLAIMS = [
    "sub",
    "name",
    "given_name",
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
    "SUB": "{uid}",
    "NAME": "{cn}",
    "PHONE_NUMBER": "{telephoneNumber}",
    "EMAIL": "{mail}",
    "GIVEN_NAME": "{givenName}",
    "FAMILY_NAME": "{sn}",
    "PREFERRED_USERNAME": "{displayName}",
    "LOCALE": "{preferredLanguage}",
}


def test_generate_user_standard_claims_with_default_config(slapd_connection, user):
    User.ldap_object_classes(slapd_connection)

    data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert data == {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "email": "john@doe.com",
        "sub": "user",
    }


def test_custom_config_format_claim_is_well_formated(slapd_connection, user):
    User.ldap_object_classes(slapd_connection)
    jwt_mapping_config = DEFAULT_JWT_MAPPING_CONFIG.copy()
    jwt_mapping_config["EMAIL"] = "{uid}@mydomain.tld"

    data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "user@mydomain.tld"


def test_claim_is_omitted_if_empty(slapd_connection, user):
    # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
    # it's better to not insert a null or empty string value
    User.ldap_object_classes(slapd_connection)
    user.mail = ""
    user.save(slapd_connection)

    data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert "email" not in data


def test_custom_format_claim_is_formatted_with_empty_value_and_not_omitted(slapd_connection, user):
    # If the jwt mapping config is customized, it's not canaille's responsability to verify value consistency when one user attribute is not set or null.
    # Attribute field is left empty in the formatted string.
    User.ldap_object_classes(slapd_connection)
    jwt_mapping_config = DEFAULT_JWT_MAPPING_CONFIG.copy()
    jwt_mapping_config["EMAIL"] = "{givenName}@mydomain.tld"

    data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "@mydomain.tld"
