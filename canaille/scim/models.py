from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Literal

from flask import url_for
from pydantic import EmailStr
from pydantic import Field
from scim2_models import AnyExtension
from scim2_models import AuthenticationScheme
from scim2_models import Bulk
from scim2_models import CaseExact
from scim2_models import ChangePassword
from scim2_models import ComplexAttribute
from scim2_models import ETag
from scim2_models import Extension
from scim2_models import ExternalReference
from scim2_models import Filter
from scim2_models import Meta
from scim2_models import Mutability
from scim2_models import Patch
from scim2_models import Reference
from scim2_models import Required
from scim2_models import Resource
from scim2_models import ResourceType
from scim2_models import Returned
from scim2_models import Schema
from scim2_models import SchemaExtension
from scim2_models import ServiceProviderConfig
from scim2_models import Sort
from scim2_models import Uniqueness

from canaille.app import DOCUMENTATION_URL


class Name(ComplexAttribute):
    formatted: Annotated[str | None, Required.true] = None
    """The full name, including all middle names, titles, and suffixes as
    appropriate, formatted for display (e.g., 'Ms. Barbara J Jensen, III')."""

    family_name: Annotated[str | None, Required.true] = None
    """The family name of the User, or last name in most Western languages
    (e.g., 'Jensen' given the full name 'Ms. Barbara J Jensen, III')."""

    given_name: str | None = None
    """The given name of the User, or first name in most Western languages
    (e.g., 'Barbara' given the full name 'Ms. Barbara J Jensen, III')."""


class Email(ComplexAttribute):
    value: Annotated[EmailStr | None, Required.true] = None
    """Email addresses for the user."""


class PhoneNumber(ComplexAttribute):
    value: Annotated[str | None, Required.true] = None
    """Phone number of the User."""


class Photo(ComplexAttribute):
    value: Annotated[
        Reference[ExternalReference] | None,
        Mutability.read_only,
        CaseExact.true,
        Required.true,
    ] = None
    """URL of a photo of the User."""


class Address(ComplexAttribute):
    formatted: str | None = None
    """The full mailing address, formatted for display or use with a mailing
    label."""

    street_address: str | None = None
    """The full street address component, which may include house number,
    street name, P.O.

    box, and multi-line extended street address information.
    """

    locality: str | None = None
    """The city or locality component."""

    region: str | None = None
    """The state or region component."""

    postal_code: str | None = None
    """The zip code or postal code component."""

    country: Annotated[str | None, Mutability.read_only, Returned.never] = None
    """The country name component (not used by Canaille)."""

    type: Annotated[str | None, Mutability.read_only, Returned.never] = None
    """A label indicating the attribute's function (not used by Canaille)."""


class GroupMembership(ComplexAttribute):
    value: Annotated[str | None, Mutability.read_only] = None
    """The identifier of the User's group."""

    ref: Annotated[
        Reference[Literal["User"] | Literal["Group"]] | None,
        Mutability.read_only,
    ] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""

    display: Annotated[str | None, Mutability.read_only] = None
    """A human-readable name, primarily used for display purposes."""


class User(Resource[AnyExtension]):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:User"
    ]

    external_id: Annotated[str | None, Mutability.read_only, Returned.never] = None

    user_name: Annotated[
        str | None, Uniqueness.server, Required.true, Mutability.immutable
    ] = None
    """Unique identifier for the User, typically used by the user to directly
    authenticate to the service provider."""

    name: Annotated[Name | None, Required.true] = None
    """The components of the user's real name."""

    Name: ClassVar[type[ComplexAttribute]] = Name

    display_name: str | None = None
    """The name of the User, suitable for display to end-users."""

    profile_url: Reference[ExternalReference] | None = None
    """A fully qualified URL pointing to a page representing the User's online
    profile."""

    title: str | None = None
    """The user's title, such as "Vice President"."""

    preferred_language: str | None = None
    """Indicates the User's preferred written or spoken language.

    Generally used for selecting a localized user interface; e.g.,
    'en_US' specifies the language English and country US.
    """

    active: Annotated[bool | None, Required.true] = None
    """A Boolean value indicating the User's administrative status."""

    password: Annotated[str | None, Mutability.write_only, Returned.never] = None
    """The User's cleartext password."""

    emails: list[Email] | None = None
    """Email addresses for the user."""

    Emails: ClassVar[type[ComplexAttribute]] = Email

    phone_numbers: list[PhoneNumber] | None = None
    """Phone numbers for the User."""

    PhoneNumbers: ClassVar[type[ComplexAttribute]] = PhoneNumber

    photos: Annotated[list[Photo] | None, Mutability.read_only] = None
    """URLs of photos of the User."""

    Photos: ClassVar[type[ComplexAttribute]] = Photo

    addresses: list[Address] | None = None
    """A physical mailing address for this User."""

    Addresses: ClassVar[type[ComplexAttribute]] = Address

    groups: Annotated[list[GroupMembership] | None, Mutability.read_only] = None
    """A list of groups to which the user belongs, either through direct
    membership, through nested groups, or dynamically calculated."""

    Groups: ClassVar[type[ComplexAttribute]] = GroupMembership


class GroupMember(ComplexAttribute):
    value: Annotated[str | None, Mutability.immutable, Required.true] = None
    """Identifier of the member of this Group."""

    ref: Annotated[
        Reference[Literal["User"] | Literal["Group"]] | None,
        Mutability.immutable,
        Required.true,
    ] = Field(None, serialization_alias="$ref")
    """The reference URI of a target resource, if the attribute is a
    reference."""

    display: Annotated[str | None, Mutability.read_only] = None
    """A human-readable name, primarily used for display purposes."""


class Group(Resource[Any]):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:core:2.0:Group"
    ]

    external_id: Annotated[str | None, Mutability.read_only, Returned.never] = None

    display_name: Annotated[str | None, Required.true, Mutability.immutable] = None
    """A human-readable name for the Group."""

    members: Annotated[list[GroupMember] | None, Required.true] = None
    """A list of members of the Group."""

    Members: ClassVar[type[ComplexAttribute]] = GroupMember


class EnterpriseUser(Extension):
    schemas: Annotated[list[str], Required.true] = [
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    ]

    employee_number: str | None = None
    """Numeric or alphanumeric identifier assigned to a person, typically based
    on order of hire or association with an organization."""

    organization: str | None = None
    """Identifies the name of an organization."""

    department: str | None = None
    """Identifies the name of a department."""


def get_service_provider_config():
    return ServiceProviderConfig(
        meta=Meta(
            resource_type="ServiceProviderConfig",
            location=url_for("scim.query_service_provider_config", _external=True),
        ),
        documentation_uri=DOCUMENTATION_URL,
        patch=Patch(supported=True),
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
