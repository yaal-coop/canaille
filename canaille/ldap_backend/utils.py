import datetime
from enum import Enum

LDAP_NULL_DATE = "000001010000Z"


class Syntax(str, Enum):
    # fmt: off
    BOOLEAN =          "1.3.6.1.4.1.1466.115.121.1.7"
    DIRECTORY_STRING = "1.3.6.1.4.1.1466.115.121.1.15"
    FAX_IMAGE =        "1.3.6.1.4.1.1466.115.121.1.23"
    GENERALIZED_TIME = "1.3.6.1.4.1.1466.115.121.1.24"
    IA5_STRING =       "1.3.6.1.4.1.1466.115.121.1.26"
    INTEGER =          "1.3.6.1.4.1.1466.115.121.1.27"
    JPEG =             "1.3.6.1.4.1.1466.115.121.1.28"
    NUMERIC_STRING =   "1.3.6.1.4.1.1466.115.121.1.36"
    OCTET_STRING =     "1.3.6.1.4.1.1466.115.121.1.40"
    POSTAL_ADDRESS =   "1.3.6.1.4.1.1466.115.121.1.41"
    PRINTABLE_STRING = "1.3.6.1.4.1.1466.115.121.1.44"
    TELEPHONE_NUMBER = "1.3.6.1.4.1.1466.115.121.1.50"
    # fmt: on


def ldap_to_python(value, syntax):
    if syntax == Syntax.GENERALIZED_TIME:
        value = value.decode("utf-8")
        if value == LDAP_NULL_DATE:
            # python cannot represent datetimes with year 0
            return datetime.datetime.min
        else:
            return datetime.datetime.strptime(value, "%Y%m%d%H%M%SZ") if value else None

    if syntax == Syntax.INTEGER:
        return int(value.decode("utf-8"))

    if syntax == Syntax.JPEG:
        return value

    if syntax == Syntax.BOOLEAN:
        return value.decode("utf-8").upper() == "TRUE"

    return value.decode("utf-8")


def python_to_ldap(value, syntax):
    if syntax == Syntax.GENERALIZED_TIME and isinstance(value, datetime.datetime):
        if value == datetime.datetime.min:
            return LDAP_NULL_DATE.encode("utf-8")
        else:
            return value.strftime("%Y%m%d%H%M%SZ").encode("utf-8")

    if syntax == Syntax.INTEGER and isinstance(value, int):
        return str(value).encode("utf-8")

    if syntax == Syntax.JPEG:
        return value if value else None

    if syntax == Syntax.BOOLEAN and isinstance(value, bool):
        return ("TRUE" if value else "FALSE").encode("utf-8")

    return value.encode("utf-8") if value else None
