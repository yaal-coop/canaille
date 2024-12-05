import datetime
from enum import Enum

from canaille.backends import Backend

LDAP_NULL_DATE = "000001010000Z"


class Syntax(str, Enum):
    # fmt: off
    BINARY =             "1.3.6.1.4.1.1466.115.121.1.5"
    BOOLEAN =            "1.3.6.1.4.1.1466.115.121.1.7"
    CERTIFICATE =        "1.3.6.1.4.1.1466.115.121.1.8"
    COUNTRY_STRING =     "1.3.6.1.4.1.1466.115.121.1.11"
    DISTINGUISHED_NAME = "1.3.6.1.4.1.1466.115.121.1.12"
    DIRECTORY_STRING =   "1.3.6.1.4.1.1466.115.121.1.15"
    FAX_IMAGE =          "1.3.6.1.4.1.1466.115.121.1.23"
    GENERALIZED_TIME =   "1.3.6.1.4.1.1466.115.121.1.24"
    IA5_STRING =         "1.3.6.1.4.1.1466.115.121.1.26"
    INTEGER =            "1.3.6.1.4.1.1466.115.121.1.27"
    JPEG =               "1.3.6.1.4.1.1466.115.121.1.28"
    NUMERIC_STRING =     "1.3.6.1.4.1.1466.115.121.1.36"
    OCTET_STRING =       "1.3.6.1.4.1.1466.115.121.1.40"
    POSTAL_ADDRESS =     "1.3.6.1.4.1.1466.115.121.1.41"
    PRINTABLE_STRING =   "1.3.6.1.4.1.1466.115.121.1.44"
    TELEPHONE_NUMBER =   "1.3.6.1.4.1.1466.115.121.1.50"
    UTC_TIME =           "1.3.6.1.4.1.1466.115.121.1.53"
    # fmt: on


def ldap_to_python(value, syntax):
    from .ldapobject import LDAPObject

    if syntax == Syntax.GENERALIZED_TIME:
        value = value.decode("utf-8")
        if value == LDAP_NULL_DATE:
            # python cannot represent datetimes with year 0
            return datetime.datetime.min
        if value.endswith("Z"):
            format_string = (
                "%Y%m%d%H%M%S.%fZ" if "." in value else "%Y%m%d%H%M%SZ"
            )  # microseconds
            return datetime.datetime.strptime(value, format_string).replace(
                tzinfo=datetime.timezone.utc
            )
        return datetime.datetime.strptime(value, "%Y%m%d%H%M%S%z")

    if syntax == Syntax.INTEGER:
        return int(value.decode("utf-8"))

    if syntax in (Syntax.JPEG, Syntax.FAX_IMAGE):
        return value

    if syntax == Syntax.BOOLEAN:
        return value.decode("utf-8").upper() == "TRUE"

    if syntax == Syntax.DISTINGUISHED_NAME:
        return Backend.instance.get(LDAPObject, value.decode("utf-8"))

    return value.decode("utf-8")


def python_to_ldap(value, syntax, encode=True):
    encodable = True
    if syntax == Syntax.GENERALIZED_TIME and isinstance(value, datetime.datetime):
        if value == datetime.datetime.min:
            value = LDAP_NULL_DATE
        elif not value.tzinfo or value.tzinfo == datetime.timezone.utc:
            value = value.strftime("%Y%m%d%H%M%SZ")
        else:
            value = value.strftime("%Y%m%d%H%M%S%z")

    if syntax == Syntax.INTEGER and isinstance(value, int):
        value = str(value)

    if syntax in (Syntax.JPEG, Syntax.FAX_IMAGE):
        encodable = False

    if syntax == Syntax.BOOLEAN and isinstance(value, bool):
        value = "TRUE" if value else "FALSE"

    if syntax == Syntax.DISTINGUISHED_NAME:
        value = value.dn if value else None

    if not value:
        return None

    return value.encode() if encode and encodable else value


def listify(value):
    return value if isinstance(value, list) else [value]


def cardinalize_attribute(python_unique, value):
    if not value:
        return None if python_unique else []

    if python_unique:
        return value[0]

    return [v for v in value if v is not None]


def python_attrs_to_ldap(attrs, encode=True, null_allowed=True):
    formatted_attrs = {
        name: [
            python_to_ldap(value, attribute_ldap_syntax(name), encode=encode)
            for value in listify(values)
        ]
        for name, values in attrs.items()
    }
    if not null_allowed:
        formatted_attrs = {
            key: [value for value in values if value]
            for key, values in formatted_attrs.items()
            if values
        }
    return formatted_attrs


def attribute_ldap_syntax(attribute_name):
    from .ldapobject import LDAPObject

    ldap_attrs = LDAPObject.ldap_object_attributes()
    if attribute_name not in ldap_attrs:
        return None

    if ldap_attrs[attribute_name].syntax:
        return ldap_attrs[attribute_name].syntax

    return attribute_ldap_syntax(ldap_attrs[attribute_name].sup[0])
