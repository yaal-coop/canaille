from canaille.app import models
from canaille.backends.ldap.backend import setup_ldap_models
from canaille.backends.ldap.ldapobject import LDAPObject


def test_guess_object_from_dn(backend, testclient, foo_group):
    foo_group.members = [foo_group]
    foo_group.save()
    dn = foo_group.dn
    g = LDAPObject.get(dn)
    assert isinstance(g, models.Group)
    assert g == foo_group
    assert g.display_name == foo_group.display_name


def test_object_class_update(backend, testclient):
    testclient.app.config["CANAILLE_LDAP"]["USER_CLASS"] = ["inetOrgPerson"]
    setup_ldap_models(testclient.app.config)

    user1 = models.User(cn="foo1", sn="bar1", user_name="baz1")
    user1.save()

    assert set(user1.get_ldap_attribute("objectClass")) == {"inetOrgPerson"}
    assert set(models.User.get(id=user1.id).get_ldap_attribute("objectClass")) == {
        "inetOrgPerson"
    }

    testclient.app.config["CANAILLE_LDAP"]["USER_CLASS"] = [
        "inetOrgPerson",
        "extensibleObject",
    ]
    setup_ldap_models(testclient.app.config)

    user2 = models.User(cn="foo2", sn="bar2", user_name="baz2")
    user2.save()

    assert set(user2.get_ldap_attribute("objectClass")) == {
        "inetOrgPerson",
        "extensibleObject",
    }
    assert set(models.User.get(id=user2.id).get_ldap_attribute("objectClass")) == {
        "inetOrgPerson",
        "extensibleObject",
    }

    user1 = models.User.get(id=user1.id)
    assert user1.get_ldap_attribute("objectClass") == ["inetOrgPerson"]

    user1.save()
    assert set(user1.get_ldap_attribute("objectClass")) == {
        "inetOrgPerson",
        "extensibleObject",
    }
    assert set(models.User.get(id=user1.id).get_ldap_attribute("objectClass")) == {
        "inetOrgPerson",
        "extensibleObject",
    }

    user1.delete()
    user2.delete()


def test_keep_old_object_classes(backend, testclient, slapd_server):
    """When using a populated LDAP database, some objects may have existing
    objectClass not handled by Canaille.

    In such a case Canaille should keep the unmanaged objectClass and
    attributes.
    """

    user = models.User(cn="foo", sn="bar", user_name="baz")
    user.save()

    ldif = f"""dn: {user.dn}
changetype: modify
add: objectClass
objectClass: posixAccount
-
add: uidNumber
uidNumber: 1000
-
add: gidNumber
gidNumber: 1000
-
add: homeDirectory
homeDirectory: /home/foobar
"""

    process = slapd_server.ldapmodify(ldif)
    assert process.returncode == 0

    user.reload()

    # saving an object should not raise a ldap.OBJECT_CLASS_VIOLATION exception
    user.save()

    user.delete()
