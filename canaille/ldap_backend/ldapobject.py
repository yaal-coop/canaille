import itertools
from collections.abc import Iterable

import ldap.dn
import ldap.filter
from flask import g

from .utils import ldap_to_python
from .utils import python_to_ldap


def python_attrs_to_ldap(attrs, encode=True):
    return {
        name: [
            python_to_ldap(value, attribute_ldap_syntax(name), encode=encode)
            for value in (values if isinstance(values, list) else [values])
        ]
        for name, values in attrs.items()
    }


def attribute_ldap_syntax(attribute_name):
    ldap_attrs = LDAPObject.ldap_object_attributes()
    if attribute_name not in ldap_attrs:
        return None

    if ldap_attrs[attribute_name].syntax:
        return ldap_attrs[attribute_name].syntax

    return attribute_ldap_syntax(ldap_attrs[attribute_name].sup[0])


class LDAPObjectMetaclass(type):
    ldap_to_python_class = {}

    def __new__(cls, name, bases, attrs):
        klass = super().__new__(cls, name, bases, attrs)
        if attrs.get("ldap_object_class"):
            for oc in attrs["ldap_object_class"]:
                cls.ldap_to_python_class[oc] = klass
        return klass

    def __setattr__(cls, name, value):
        super().__setattr__(name, value)
        if name == "ldap_object_class":
            for oc in value:
                cls.ldap_to_python_class[oc] = cls


class LDAPObjectQuery:
    def __init__(self, klass, items):
        self.klass = klass
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return (self.decorate(obj[1]) for obj in self.items[item])

        return self.decorate(self.items[item][1])

    def __iter__(self):
        return (self.decorate(obj[1]) for obj in self.items)

    def __eq__(self, other):
        if isinstance(other, Iterable):
            return all(
                a == b
                for a, b in itertools.zip_longest(
                    iter(self), iter(other), fillvalue=object()
                )
            )
        return super().__eq__(other)

    def __bool__(self):
        return bool(self.items)

    def decorate(self, args):
        klass = self.guess_class(self.klass, args["objectClass"])
        obj = klass()
        obj.attrs = args
        obj.exists = True
        return obj

    def guess_class(self, klass, object_classes):
        if klass == LDAPObject:
            for oc in object_classes:
                if oc.decode() in LDAPObjectMetaclass.ldap_to_python_class:
                    return LDAPObjectMetaclass.ldap_to_python_class[oc.decode()]
        return klass


class LDAPObject(metaclass=LDAPObjectMetaclass):
    _object_class_by_name = None
    _attribute_type_by_name = None
    _may = None
    _must = None
    base = None
    root_dn = None
    rdn_attribute = None
    attribute_table = None
    ldap_object_class = None

    def __init__(self, dn=None, **kwargs):
        self.attrs = {}
        self.changes = {}
        self.exists = False

        for name, value in kwargs.items():
            setattr(self, name, value)

    def __repr__(self):
        reverse_attributes = {v: k for k, v in (self.attribute_table or {}).items()}
        attribute_name = reverse_attributes.get(self.rdn_attribute, self.rdn_attribute)
        return (
            f"<{self.__class__.__name__} {attribute_name}={self.rdn_value}>"
            if self.rdn_attribute
            else "<LDAPOBject>"
        )

    def __eq__(self, other):
        if not (
            isinstance(other, self.__class__)
            and self.may() == other.may()
            and self.must() == other.must()
            and all(
                hasattr(self, attr) == hasattr(other, attr)
                for attr in self.may() + self.must()
            )
        ):
            return False

        self_attributes = python_attrs_to_ldap(
            {
                attr: getattr(self, attr)
                for attr in self.may() + self.must()
                if hasattr(self, attr)
            }
        )
        other_attributes = python_attrs_to_ldap(
            {
                attr: getattr(other, attr)
                for attr in self.may() + self.must()
                if hasattr(self, attr)
            }
        )
        return self_attributes == other_attributes

    def __hash__(self):
        return hash(self.id)

    def __getattr__(self, name):
        name = self.attribute_table.get(name, name)

        if name not in self.ldap_object_attributes():
            return super().__getattribute__(name)

        single_value = self.ldap_object_attributes()[name].single_value
        if name in self.changes:
            return self.changes[name][0] if single_value else self.changes[name]

        if not self.attrs.get(name):
            return None if single_value else []

        # Lazy conversion from ldap format to python format
        if any(isinstance(value, bytes) for value in self.attrs[name]):
            syntax = attribute_ldap_syntax(name)
            self.attrs[name] = [
                ldap_to_python(value, syntax) for value in self.attrs[name]
            ]

        if single_value:
            return self.attrs.get(name)[0]
        else:
            return self.attrs.get(name)

    def __setattr__(self, name, value):
        if self.attribute_table:
            name = self.attribute_table.get(name, name)

        if name in self.ldap_object_attributes():
            value = [value] if not isinstance(value, list) else value
            self.changes[name] = value

        else:
            super().__setattr__(name, value)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    @property
    def rdn_value(self):
        value = getattr(self, self.rdn_attribute)
        return (value[0] if isinstance(value, list) else value).strip()

    @property
    def dn(self):
        return f"{self.rdn_attribute}={ldap.dn.escape_dn_chars(self.rdn_value)},{self.base},{self.root_dn}"

    @classmethod
    def may(cls):
        if not cls._may:
            cls.update_ldap_attributes()
        return cls._may

    @classmethod
    def must(cls):
        return cls._must

    @classmethod
    def ldap_connection(cls):
        return g.ldap_connection

    @classmethod
    def initialize(cls, conn=None):
        conn = conn or cls.ldap_connection()
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

        conn = conn or cls.ldap_connection()

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

        conn = conn or cls.ldap_connection()

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

    @classmethod
    def get(cls, id=None, filter=None, conn=None, **kwargs):
        try:
            return cls.query(id, filter, conn, **kwargs)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            return None

    @classmethod
    def query(cls, base=None, filter=None, conn=None, **kwargs):
        conn = conn or cls.ldap_connection()

        if base is None:
            base = f"{cls.base},{cls.root_dn}"
        elif "=" not in base:
            base = f"{cls.rdn_attribute}={base},{cls.base},{cls.root_dn}"

        class_filter = (
            "".join([f"(objectClass={oc})" for oc in cls.ldap_object_class])
            if getattr(cls, "ldap_object_class")
            else ""
        )
        if class_filter:
            class_filter = f"(|{class_filter})"
        arg_filter = ""
        kwargs = python_attrs_to_ldap(
            {
                (cls.attribute_table or {}).get(name, name): values
                for name, values in kwargs.items()
            },
            encode=False,
        )
        for key, value in kwargs.items():
            if len(value) == 1:
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
        return LDAPObjectQuery(cls, result)

    @classmethod
    def fuzzy(cls, query, attributes=None, **kwargs):
        query = ldap.filter.escape_filter_chars(query)
        attributes = attributes or cls.may() + cls.must()
        attributes = [cls.attribute_table.get(name, name) for name in attributes]
        filter = (
            "(|" + "".join(f"({attribute}=*{query}*)" for attribute in attributes) + ")"
        )
        return cls.query(filter=filter, **kwargs)

    @classmethod
    def update_ldap_attributes(cls):
        all_object_classes = cls.ldap_object_classes()
        this_object_classes = {
            all_object_classes[name] for name in cls.ldap_object_class
        }
        done = set()

        cls._may = []
        cls._must = []
        while len(this_object_classes) > 0:
            object_class = this_object_classes.pop()
            done.add(object_class)
            this_object_classes |= {
                all_object_classes[ocsup]
                for ocsup in object_class.sup
                if ocsup not in done
            }
            cls._may.extend(object_class.may)
            cls._must.extend(object_class.must)

        cls._may = list(set(cls._may))
        cls._must = list(set(cls._must))

    def reload(self, conn=None):
        conn = conn or self.ldap_connection()
        result = conn.search_s(self.id, ldap.SCOPE_SUBTREE, None, ["+", "*"])
        self.changes = {}
        self.attrs = result[0][1]

    def save(self, conn=None):
        conn = conn or self.ldap_connection()

        setattr(self, "objectClass", self.ldap_object_class)

        # Object already exists in the LDAP database
        if self.exists:
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
                for name, value in python_attrs_to_ldap(changes).items()
                if value is not None and value != [None]
            }
            modlist = [(ldap.MOD_DELETE, name, None) for name in deletions] + [
                (ldap.MOD_REPLACE, name, values)
                for name, values in formatted_changes.items()
            ]
            conn.modify_s(self.id, modlist)

        # Object does not exist yet in the LDAP database
        else:
            changes = {
                name: value
                for name, value in {**self.attrs, **self.changes}.items()
                if value and value[0]
            }
            formatted_changes = {
                name: value
                for name, value in python_attrs_to_ldap(changes).items()
                if value is not None and value != None
            }
            attributes = [(name, values) for name, values in formatted_changes.items()]
            conn.add_s(self.id, attributes)

        self.exists = True
        self.attrs = {**self.attrs, **self.changes}
        self.changes = {}

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)

    def delete(self, conn=None):
        conn = conn or self.ldap_connection()
        conn.delete_s(self.id)

    def keys(self):
        ldap_keys = self.may() + self.must()
        inverted_table = {value: key for key, value in self.attribute_table.items()}
        return [inverted_table.get(key, key) for key in ldap_keys]
