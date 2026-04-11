import ldap.dn
import ldap.filter

from .utils import python_attrs_to_ldap


def build_class_filter(object_classes):
    """Build an LDAP filter matching any of the given objectClasses."""
    if not object_classes:
        return ""

    class_filter = "".join(f"(objectClass={oc})" for oc in object_classes)
    return f"(|{class_filter})"


def build_attribute_filter(model, **kwargs):
    """Build an LDAP filter from Python attribute name/value pairs."""
    ldap_args = python_attrs_to_ldap(
        {
            model.python_attribute_to_ldap(name): values
            for name, values in kwargs.items()
            if values is not None
        },
        encode=False,
    )

    parts = []
    for key, value in ldap_args.items():
        if len(value) == 1:
            escaped_value = ldap.filter.escape_filter_chars(value[0])
            parts.append(f"({key}={escaped_value})")
        else:
            values = [ldap.filter.escape_filter_chars(v) for v in value]
            parts.append("(|" + "".join(f"({key}={v})" for v in values) + ")")

    return "".join(parts)


def build_fuzzy_filter(query, attributes):
    """Build an LDAP substring filter for fuzzy matching."""
    escaped = ldap.filter.escape_filter_chars(query)
    return "(|" + "".join(f"({attr}=*{escaped}*)" for attr in attributes) + ")"


def build_search_filter(*parts):
    """Combine filter parts into a single AND filter."""
    combined = "".join(part for part in parts if part)
    if not combined:
        return None
    return f"(&{combined})"


def resolve_base_dn(model, dn=None):
    """Resolve the base DN for a search."""
    if dn is None:
        return f"{model.base},{model.root_dn}"

    if "=" not in dn:
        escaped = ldap.dn.escape_dn_chars(dn)
        return f"{model.rdn_attribute}={escaped},{model.base},{model.root_dn}"

    return dn
