from canaille.models import User
from canaille.oidc.oauth2utils import generate_user_claims

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
    "PREFERRED_USERNAME": "{{ user.displayName[0] }}",
    "LOCALE": "{{ user.preferredLanguage[0] }}",
}


def test_generate_user_standard_claims_with_default_config(
    testclient, slapd_connection, user
):
    User.ldap_object_classes(slapd_connection)

    with testclient.app.app_context():
        data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert data == {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "email": "john@doe.com",
        "sub": "user",
    }


def test_custom_config_format_claim_is_well_formated(
    testclient, slapd_connection, user
):
    User.ldap_object_classes(slapd_connection)
    jwt_mapping_config = DEFAULT_JWT_MAPPING_CONFIG.copy()
    jwt_mapping_config["EMAIL"] = "{{ user.uid[0] }}@mydomain.tld"

    with testclient.app.app_context():
        data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "user@mydomain.tld"


def test_claim_is_omitted_if_empty(testclient, slapd_connection, user):
    # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
    # it's better to not insert a null or empty string value
    User.ldap_object_classes(slapd_connection)
    user.mail = ""
    user.save(slapd_connection)

    with testclient.app.app_context():
        data = generate_user_claims(user, STANDARD_CLAIMS, DEFAULT_JWT_MAPPING_CONFIG)

    assert "email" not in data


def test_custom_format_claim_is_formatted_with_empty_value_and_not_omitted(
    testclient, slapd_connection, user
):
    # If the jwt mapping config is customized, it's not canaille's responsability to verify value consistency when one user attribute is not set or null.
    # Attribute field is left empty in the formatted string.
    User.ldap_object_classes(slapd_connection)
    jwt_mapping_config = DEFAULT_JWT_MAPPING_CONFIG.copy()
    jwt_mapping_config["EMAIL"] = "{{ user.givenName[0] }}@mydomain.tld"

    with testclient.app.app_context():
        data = generate_user_claims(user, STANDARD_CLAIMS, jwt_mapping_config)

    assert data["email"] == "@mydomain.tld"
