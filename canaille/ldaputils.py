import ldap
from flask import g


class LDAPObject:
    _object_class_by_name = None
    _attribute_type_by_name = None
    may = None
    must = None
    base = None
    root_dn = None
    id = None

    def __init__(self, dn=None, **kwargs):
        self.attrs = {}
        self.changes = {}

        if hasattr(self, "object_class") and not "objectClass" in kwargs:
            kwargs["objectClass"] = self.object_class

        for k, v in kwargs.items():
            self.attrs[k] = [v] if not isinstance(v, list) else v

        self.may = []
        self.must = []
        if "objectClass" in kwargs:
            self.update_ldap_attributes()

    def update_ldap_attributes(self):
        by_name = self.ocs_by_name()
        ocs = {by_name[name] for name in self.attrs["objectClass"]}
        done = set()

        while len(ocs) > 0:
            oc = ocs.pop()
            done.add(oc)
            for ocsup in oc.sup:
                if ocsup not in done:
                    ocs.add(by_name[ocsup])

            self.may.extend(oc.may)
            self.must.extend(oc.must)

        self.may = list(set(self.may))
        self.must = list(set(self.must))

    def __repr__(self):
        try:
            id = getattr(self, self.id)
        except AttributeError:
            id = "?"

        return "<{} {}={}>".format(self.__class__.__name__, self.id, id)

    @classmethod
    def ldap(cls):
        return g.ldap

    def keys(self):
        return self.must + self.may

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
        return f"{self.id}={id},{self.base},{self.root_dn}"

    @classmethod
    def initialize(cls, conn=None):
        conn = conn or cls.ldap()
        cls.ocs_by_name(conn)
        cls.attr_type_by_name(conn)

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
    def ocs_by_name(cls, conn=None):
        if cls._object_class_by_name:
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
            oc = subschema.get_obj(ldap.schema.models.ObjectClass, oid)
            for name in oc.names:
                cls._object_class_by_name[name] = oc

        return cls._object_class_by_name

    @classmethod
    def attr_type_by_name(cls, conn=None):
        if cls._attribute_type_by_name:
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
            oc = subschema.get_obj(ldap.schema.models.AttributeType, oid)
            for name in oc.names:
                cls._attribute_type_by_name[name] = oc

        return cls._attribute_type_by_name

    def reload(self, conn=None):
        conn = conn or self.ldap()
        result = conn.search_s(self.dn, ldap.SCOPE_SUBTREE)
        self.changes = {}
        self.attrs = {
            k: [elt.decode("utf-8") for elt in v] for k, v in result[0][1].items()
        }

    def save(self, conn=None):
        conn = conn or self.ldap()
        try:
            match = bool(conn.search_s(self.dn, ldap.SCOPE_SUBTREE))
        except ldap.NO_SUCH_OBJECT:
            match = False

        if match:
            mods = {
                k: v
                for k, v in self.changes.items()
                if v and v[0] and self.attrs.get(k) != v
            }
            attributes = [
                (
                    ldap.MOD_REPLACE,
                    k,
                    [elt.encode("utf-8") if isinstance(elt, str) else elt for elt in v],
                )
                for k, v in mods.items()
            ]
            conn.modify_s(self.dn, attributes)

        else:
            mods = {}
            for k, v in self.attrs.items():
                if v and v[0]:
                    mods[k] = v
            for k, v in self.changes.items():
                if v and v[0]:
                    mods[k] = v

            attributes = [
                (k, [elt.encode("utf-8") if isinstance(elt, str) else elt for elt in v])
                for k, v in mods.items()
            ]
            conn.add_s(self.dn, attributes)

        for k, v in self.changes.items():
            self.attrs[k] = v
        self.changes = {}

    @classmethod
    def get(cls, dn=None, filter=None, conn=None):
        try:
            return cls.filter(dn, filter, conn)[0]
        except (IndexError, ldap.NO_SUCH_OBJECT):
            return None

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
        for k, v in kwargs.items():
            if not isinstance(v, list):
                arg_filter += f"({k}={v})"
            elif len(v) == 1:
                arg_filter += f"({k}={v[0]})"
            else:
                arg_filter += "(|" + "".join([f"({k}={_v})" for _v in v]) + ")"

        filter = filter or ""
        ldapfilter = f"(&{class_filter}{arg_filter}{filter})"
        base = base or f"{cls.base},{cls.root_dn}"
        result = conn.search_s(base, ldap.SCOPE_SUBTREE, ldapfilter or None)

        return [
            cls(
                **{k: [elt.decode("utf-8") for elt in v] for k, v in args.items()},
            )
            for _, args in result
        ]

    def __getattr__(self, name):
        if (not self.may or name not in self.may) and (
            not self.must or name not in self.must
        ):
            return super().__getattribute__(name)

        if (
            not self.attr_type_by_name()
            or not self.attr_type_by_name()[name].single_value
        ):
            return self.changes.get(name, self.attrs.get(name, []))

        return self.changes.get(name, self.attrs.get(name, [None]))[0]

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

        if (self.may and name in self.may) or (self.must and name in self.must):
            if self.attr_type_by_name()[name].single_value:
                self.changes[name] = [value]
            else:
                self.changes[name] = value
