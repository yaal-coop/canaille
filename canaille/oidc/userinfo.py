from authlib.oidc import core as oidc_core
from flask import current_app


class UserInfo(oidc_core.UserInfo):
    REGISTERED_CLAIMS = oidc_core.UserInfo.REGISTERED_CLAIMS + ["groups"]
    SCOPES_CLAIMS_MAPPING = {
        "groups": ["groups"],
        **oidc_core.UserInfo.SCOPES_CLAIMS_MAPPING,
    }


def make_address_claim(user):
    payload = {}
    mapping = {
        "formatted_address": "formatted",
        "street": "street_address",
        "locality": "locality",
        "region": "region",
        "postal_code": "postal_code",
    }
    for user_attr, claim in mapping.items():
        if val := getattr(user, user_attr):
            payload[claim] = val

    return payload


def generate_user_claims(user, jwt_mapping_config=None):
    jwt_mapping_config = {
        **(current_app.config["CANAILLE_OIDC"]["USERINFO_MAPPING"]),
        **(jwt_mapping_config or {}),
    }

    data = {}
    for claim in UserInfo.REGISTERED_CLAIMS:
        raw_claim = jwt_mapping_config.get(claim.upper())
        if raw_claim:
            formatted_claim = current_app.jinja_env.from_string(raw_claim).render(
                user=user
            )
            if formatted_claim:
                # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
                # it's better to not insert a null or empty string value
                data[claim] = formatted_claim

        if claim == "address" and (address := make_address_claim(user)):
            data[claim] = address

        if claim == "groups" and user.groups:
            data[claim] = [group.display_name for group in user.groups]

        if claim == "updated_at":
            data[claim] = int(float(data[claim]))

    return data
