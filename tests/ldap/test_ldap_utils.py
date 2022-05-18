import ldap.dn
from canaille.models import Group
from canaille.models import User


def test_equality(slapd_connection, foo_group, bar_group):
    Group.ldap_object_attributes(conn=slapd_connection)
    assert foo_group != bar_group
    foo_group2 = Group.get(dn=foo_group.dn, conn=slapd_connection)
    assert foo_group == foo_group2


def test_dn_when_leading_space_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        objectClass=["inetOrgPerson"],
        cn=" Doe",  # leading space
        sn="Doe",
        uid="user",
        mail="john@doe.com",
    )
    user.save(slapd_connection)

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=Doe,ou=users,dc=slapd-test,dc=python-ldap,dc=org"

    user.delete(slapd_connection)


def test_dn_when_ldap_special_char_in_id_attribute(slapd_connection):
    User.initialize(slapd_connection)
    user = User(
        objectClass=["inetOrgPerson"],
        cn="#Doe",  # special char
        sn="Doe",
        uid="user",
        mail="john@doe.com",
    )
    user.save(slapd_connection)

    assert ldap.dn.is_dn(user.dn)
    assert ldap.dn.dn2str(ldap.dn.str2dn(user.dn)) == user.dn
    assert user.dn == "cn=\\#Doe,ou=users,dc=slapd-test,dc=python-ldap,dc=org"

    user.delete(slapd_connection)
