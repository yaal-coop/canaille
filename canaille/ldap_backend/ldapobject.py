import datetime
from enum import Enum

import ldap.dn
import ldap.filter
from flask import g

LDAP_NULL_DATE = "000001010000Z"


class Syntax(str, Enum):
    # fmt: off
    BOOLEAN =          "1.3.6.1.4.1.1466.115.121.1.7"
    DIRECTORY_STRING = "1.3.6.1.4.1.1466.115.121.1.15"
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


class LDAPObject:
    _object_class_by_name = None
    _attribute_type_by_name = None
    may = None
    must = None
    base = None
    root_dn = None
    id = None
    attribute_table = None

    def __init__(self, dn=None, **kwargs):
        self.attrs = {}
        self.changes = {}

        if hasattr(self, "object_class") and not "objectClass" in kwargs:
            kwargs["objectClass"] = self.object_class

        for name, value in kwargs.items():
            attribute_name = (
                self.attribute_table[name]
                if self.attribute_table and name in self.attribute_table
                else name
            )
            self.attrs[attribute_name] = (
                [value] if not isinstance(value, list) else value
            )

        self.may = []
        self.must = []
        if "objectClass" in kwargs:
            self.update_ldap_attributes()

    def update_ldap_attributes(self):
        all_object_classes = self.ldap_object_classes()
        this_object_classes = {
            all_object_classes[name] for name in self.attrs["objectClass"]
        }
        done = set()

        while len(this_object_classes) > 0:
            object_class = this_object_classes.pop()
            done.add(object_class)
            for ocsup in object_class.sup:
                if ocsup not in done:
                    this_object_classes.add(all_object_classes[ocsup])

            self.may.extend(object_class.may)
            self.must.extend(object_class.must)

        self.may = list(set(self.may))
        self.must = list(set(self.must))

    def __repr__(self):
        try:
            id = getattr(self, self.id)
        except AttributeError:
            id = "?"

        return f"<{self.__class__.__name__} {self.id}={id}>"

    @classmethod
    def ldap(cls):
        return g.ldap

    def keys(self):
        ldap_keys = self.must + self.may

        if not self.attribute_table:
            return ldap_keys

        inverted_table = {value: key for key, value in self.attribute_table.items()}
        return [inverted_table.get(key, key) for key in ldap_keys]

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)

    def delete(self, conn=None):
        conn = conn or self.ldap()
        conn.delete_s(self.dn)

    @property
    def dn(self):
        if self.id in self.changes:
            id = self.changes[self.id][0]
        elif self.id in self.attrs:
            id = self.attrs[self.id][0]
        else:
            return None
        return f"{self.id}={ldap.dn.escape_dn_chars(id.strip())},{self.base},{self.root_dn}"

    @classmethod
    def initialize(cls, conn=None):
        conn = conn or cls.ldap()
        cls.ldap_object_classes(conn)
        cls.ldap_object_attributes(conn)

        acc = ""
        for organizationalUnit in cls.base.split(",")[::-1]:
            v = organizationalUnit.split("=")[1]
            dn = f"{organizationalUnit}{acc},{cls.root_dn}"
            acc = f",{organizationalUnit}"
            try:
                conn.add_s(
                    dn,
                    [
                        ("objectClass", [b"organizationalUnit"]),
                        ("ou", [v.encode("utf-8")]),
                    ],
                )
            except ldap.ALREADY_EXISTS:
                pass

    @classmethod
    def ldap_object_classes(cls, conn=None, force=False):
        if cls._object_class_by_name and not force:
            return cls._object_class_by_name

        conn = conn or cls.ldap()

        res = conn.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        object_class_oids = subschema.listall(ldap.schema.models.ObjectClass)
        cls._object_class_by_name = {}
        for oid in object_class_oids:
            object_class = subschema.get_obj(ldap.schema.models.ObjectClass, oid)
            for name in object_class.names:
                cls._object_class_by_name[name] = object_class

        return cls._object_class_by_name

    @classmethod
    def ldap_object_attributes(cls, conn=None, force=False):
        if cls._attribute_type_by_name and not force:
            return cls._attribute_type_by_name

        conn = conn or cls.ldap()

        res = conn.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        attribute_type_oids = subschema.listall(ldap.schema.models.AttributeType)
        cls._attribute_type_by_name = {}
        for oid in attribute_type_oids:
            object_class = subschema.get_obj(ldap.schema.models.AttributeType, oid)
            for name in object_class.names:
                cls._attribute_type_by_name[name] = object_class

        return cls._attribute_type_by_name

    @staticmethod
    def ldap_to_python(name, value):
        try:
            syntax = LDAPObject.ldap_object_attributes()[name].syntax
        except KeyError:
            return value

        if syntax == Syntax.GENERALIZED_TIME:
            value = value.decode("utf-8")
            if value == LDAP_NULL_DATE:
                # python cannot represent datetimes with year 0
                return datetime.datetime.min
            else:
                return (
                    datetime.datetime.strptime(value, "%Y%m%d%H%M%SZ")
                    if value
                    else None
                )

        if syntax == Syntax.INTEGER:
            return int(value.decode("utf-8"))

        if syntax == Syntax.JPEG:
            return value

        if syntax == Syntax.BOOLEAN:
            return value.decode("utf-8").upper() == "TRUE"

        return value.decode("utf-8")

    @staticmethod
    def python_to_ldap(name, value):
        try:
            syntax = LDAPObject.ldap_object_attributes()[name].syntax
        except KeyError:
            return value

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

    @staticmethod
    def ldap_attrs_to_python(attrs):
        return {
            name: [LDAPObject.ldap_to_python(name, value) for value in values]
            for name, values in attrs.items()
        }

    @staticmethod
    def python_attrs_to_ldap(attrs):
        return {
            name: [LDAPObject.python_to_ldap(name, value) for value in values]
            for name, values in attrs.items()
        }

    def reload(self, conn=None):
        conn = conn or self.ldap()
        result = conn.search_s(self.dn, ldap.SCOPE_SUBTREE, None, ["+", "*"])
        self.changes = {}
        self.attrs = self.ldap_attrs_to_python(result[0][1])

    def save(self, conn=None):
        conn = conn or self.ldap()
        try:
            match = bool(conn.search_s(self.dn, ldap.SCOPE_SUBTREE))
        except ldap.NO_SUCH_OBJECT:
            match = False

        # Object already exists in the LDAP database
        if match:
            deletions = [
                name
                for name, value in self.changes.items()
                if (value is None or value == [None]) and name in self.attrs
            ]
            changes = {
                name: value
                for name, value in self.changes.items()
                if name not in deletions and self.attrs.get(name) != value
            }
            formatted_changes = {
                name: value
                for name, value in self.python_attrs_to_ldap(changes).items()
                if value is not None and value != [None]
            }
            modlist = [(ldap.MOD_DELETE, name, None) for name in deletions] + [
                (ldap.MOD_REPLACE, name, values)
                for name, values in formatted_changes.items()
            ]
            conn.modify_s(self.dn, modlist)

        # Object does not exist yet in the LDAP database
        else:
            changes = {
                name: value
                for name, value in {**self.attrs, **self.changes}.items()
                if value and value[0]
            }
            formatted_changes = {
                name: value
                for name, value in self.python_attrs_to_ldap(changes).items()
                if value is not None and value != None
            }
            attributes = [(name, values) for name, values in formatted_changes.items()]
            conn.add_s(self.dn, attributes)

        self.attrs = {**self.attrs, **self.changes}
        self.changes = {}

    @classmethod
    def get(cls, dn=None, filter=None, conn=None, **kwargs):
        try:
            return cls.filter(dn, filter, conn, **kwargs)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            return None

    @classmethod
    def all(cls, conn=None):
        return cls.filter(conn=conn)

    @classmethod
    def filter(cls, base=None, filter=None, conn=None, **kwargs):
        conn = conn or cls.ldap()

        if base is None:
            base = f"{cls.base},{cls.root_dn}"
        elif "=" not in base:
            base = f"{cls.id}={base},{cls.base},{cls.root_dn}"

        class_filter = (
            "".join([f"(objectClass={oc})" for oc in cls.object_class])
            if hasattr(cls, "object_class")
            else ""
        )
        arg_filter = ""
        for key, value in kwargs.items():
            if cls.attribute_table:
                key = cls.attribute_table.get(key, key)

            if not isinstance(value, list):
                escaped_value = ldap.filter.escape_filter_chars(value)
                arg_filter += f"({key}={escaped_value})"

            elif len(value) == 1:
                escaped_value = ldap.filter.escape_filter_chars(value[0])
                arg_filter += f"({key}={escaped_value})"

            else:
                values = [ldap.filter.escape_filter_chars(v) for v in value]
                arg_filter += (
                    "(|" + "".join([f"({key}={value})" for value in values]) + ")"
                )

        if not filter:
            filter = ""
        elif not filter.startswith("(") and not filter.endswith(")"):
            filter = f"({filter})"

        ldapfilter = f"(&{class_filter}{arg_filter}{filter})"
        base = base or f"{cls.base},{cls.root_dn}"
        result = conn.search_s(base, ldap.SCOPE_SUBTREE, ldapfilter or None, ["+", "*"])

        return [cls(**cls.ldap_attrs_to_python(args)) for _, args in result]

    def __getattr__(self, name):
        attribute_name = (
            self.attribute_table[name]
            if self.attribute_table and name in self.attribute_table
            else name
        )

        if attribute_name in self.ldap_object_attributes():
            if (
                not self.ldap_object_attributes()
                or not self.ldap_object_attributes()[attribute_name].single_value
            ):
                return self.changes.get(name, self.attrs.get(attribute_name, []))
            else:
                return self.changes.get(
                    attribute_name, self.attrs.get(attribute_name, [None])
                )[0]

        return super().__getattribute__(attribute_name)

    def __setattr__(self, name, value):
        attribute_name = (
            self.attribute_table[name]
            if self.attribute_table and name in self.attribute_table
            else name
        )

        super().__setattr__(attribute_name, value)

        if attribute_name in self.ldap_object_attributes():
            if self.ldap_object_attributes()[attribute_name].single_value:
                self.changes[attribute_name] = [value]
            else:
                self.changes[attribute_name] = value

    def __eq__(self, other):
        return (
            self.may == other.may
            and self.must == other.must
            and all(
                getattr(self, attr) == getattr(other, attr)
                for attr in self.may + self.must
            )
        )

    def __hash__(self):
        return hash(self.dn)
