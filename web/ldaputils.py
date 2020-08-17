import ldap
from flask import g


class LDAPObjectHelper:
    _object_class_by_name = None
    _attribute_type_by_name = None
    may = None
    must = None
    base = None
    id = None

    def __init__(self, dn=None, **kwargs):
        self.attrs = {}
        for k, v in kwargs.items():
            self.attrs[k] = [v] if not isinstance(v, list) else v
        self.attrs.setdefault("objectClass", self.objectClass)

        by_name = self.ocs_by_name()
        ocs = [by_name[name] for name in self.objectClass]
        self.may = []
        self.must = []
        for oc in ocs:
            self.may.extend(oc.may)
            self.must.extend(oc.must)

    def __repr__(self):
        return "<{} {}={}>".format(
            self.__class__.__name__,
            self.id,
            getattr(self, self.id)
        )

    def keys(self):
        return self.must + self.may

    def __getitem__(self, item):
        return getattr(self, item)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)

    @property
    def dn(self):
        if not self.id in self.attrs:
            return None
        return f"{self.id}={self.attrs[self.id][0]},{self.base}"

    @classmethod
    def ocs_by_name(cls):
        if cls._object_class_by_name:
            return cls._object_class_by_name

        res = g.ldap.search_s(
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
    def attr_type_by_name(cls):
        if cls._attribute_type_by_name:
            return cls._attribute_type_by_name

        res = g.ldap.search_s(
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

    def save(self):
        try:
            match = bool(g.ldap.search_s(self.dn, ldap.SCOPE_SUBTREE))
        except ldap.NO_SUCH_OBJECT:
            match = False

        if match:
            attributes = [
                (ldap.MOD_REPLACE, k, [elt.encode("utf-8") for elt in v])
                for k, v in self.attrs.items()
            ]
            g.ldap.modify_s(self.dn, attributes)

        else:
            attributes = [
                (k, [elt.encode("utf-8") for elt in v]) for k, v in self.attrs.items()
            ]
            g.ldap.add_s(self.dn, attributes)

    @classmethod
    def get(cls, dn):
        if "=" not in dn:
            dn = f"{cls.id}={dn},{cls.base}"
        result = g.ldap.search_s(dn, ldap.SCOPE_SUBTREE)

        if not result:
            return None

        o = cls(
            **{k: [elt.decode("utf-8") for elt in v] for k, v in result[0][1].items()}
        )

        return o

    @classmethod
    def filter(cls, base=None, **kwargs):
        class_filter = "".join([f"(objectClass={oc})" for oc in cls.objectClass])
        arg_filter = "".join(f"({k}={v})" for k, v in kwargs.items())
        ldapfilter = f"(&{class_filter}{arg_filter})"
        result = g.ldap.search_s(base or cls.base, ldap.SCOPE_SUBTREE, ldapfilter)

        return [
            cls(**{k: [elt.decode("utf-8") for elt in v] for k, v in args.items()},)
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
            return self.attrs.get(name, [])

        return self.attrs.get(name, [None])[0]

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

        if (self.may and name in self.may) or (self.must and name in self.must):
            if self.attr_type_by_name()[name].single_value:
                self.attrs[name] = [value]
            else:
                self.attrs[name] = value
