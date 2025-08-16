from typing import Annotated
from typing import Literal

import scim2_models
from flask import url_for
from pydantic import Field
from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import ChangePassword
from scim2_models import EnterpriseUser
from scim2_models import ETag
from scim2_models import Filter
from scim2_models import Meta
from scim2_models import Mutability
from scim2_models import Patch
from scim2_models import Reference
from scim2_models import Required
from scim2_models import ResourceType
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import SchemaExtension
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import Uniqueness

from canaille.app import DOCUMENTATION_URL


class User(scim2_models.User):
    # At the difference of SCIM User, Canaille User need a 'family_name'
    # (because the LDAP 'sn' is mandatory)
    class Name(scim2_models.Name):
        family_name: Annotated[str | None, Required.true] = None
        formatted: Annotated[str | None, Required.true] = None

    name: Annotated[Name | None, Required.true] = None

    # At the difference of SCIM User, Canaille User the 'user_name'
    # attribute is immutable (because it is part of the LDAP DN).
    user_name: Annotated[
        str | None, Uniqueness.server, Required.true, Mutability.immutable
    ] = None

    external_id: Annotated[str | None, Mutability.read_only, Returned.never] = None


class Group(scim2_models.Group):
    class Members(scim2_models.GroupMember):
        value: Annotated[str | None, Mutability.immutable, Required.true] = None

        ref: Annotated[
            Reference[Literal["User"] | Literal["Group"]] | None,
            Mutability.immutable,
            Required.true,
        ] = Field(None, serialization_alias="$ref")

    # At the difference of the SCIM Group, Canaille Group must have a display_name.
    # and 'members' cannot be null.
    display_name: Annotated[str | None, Required.true, Mutability.immutable] = None

    members: Annotated[list[Members] | None, Required.true] = None

    external_id: Annotated[str | None, Mutability.read_only, Returned.never] = None


def get_service_provider_config():
    return ServiceProviderConfig(
        meta=Meta(
            resource_type="ServiceProviderConfig",
            location=url_for("scim.query_service_provider_config", _external=True),
        ),
        documentation_uri=DOCUMENTATION_URL,
        patch=Patch(supported=False),
        bulk=Bulk(supported=False, max_operations=0, max_payload_size=0),
        change_password=ChangePassword(supported=True),
        filter=Filter(supported=False, max_results=0),
        sort=Sort(supported=False),
        etag=ETag(supported=False),
        authentication_schemes=[
            AuthenticationScheme(
                name="OAuth Bearer Token",
                description="Authentication scheme using the OAuth Bearer Token Standard",
                spec_uri="http://www.rfc-editor.org/info/rfc6750",
                documentation_uri=DOCUMENTATION_URL,
                type="oauthbearertoken",
                primary=True,
            ),
        ],
    )


def get_resource_types():
    """Return the resource types implemented by Canaille."""
    return {
        "User": ResourceType(
            id="User",
            name="User",
            endpoint=url_for("scim.query_users", _external=True),
            description="User accounts",
            schema_="urn:ietf:params:scim:schemas:core:2.0:User",
            schema_extensions=[
                SchemaExtension(
                    schema_="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
                    required=True,
                )
            ],
            meta=Meta(
                resource_type="ResourceType",
                location=url_for(
                    "scim.query_resource_type",
                    resource_type_name="User",
                    _external=True,
                ),
            ),
        ),
        "Group": ResourceType(
            id="Group",
            name="Group",
            endpoint=url_for("scim.query_groups", _external=True),
            description="Group management",
            schema_="urn:ietf:params:scim:schemas:core:2.0:Group",
            meta=Meta(
                resource_type="ResourceType",
                location=url_for(
                    "scim.query_resource_type",
                    resource_type_name="Group",
                    _external=True,
                ),
            ),
        ),
    }


def get_schemas():
    schemas = {
        model.model_fields["schemas"].default[0]: model.to_schema()
        for model in (
            ServiceProviderConfig,
            ResourceType,
            Schema,
            User,
            Group,
            EnterpriseUser,
        )
    }
    for schema_id, schema in schemas.items():
        schema.meta = Meta(
            resource_type="Schema",
            location=url_for("scim.query_schema", schema_id=schema_id, _external=True),
        )
    return schemas
