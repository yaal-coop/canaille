from canaille.models import Group


def test_equality(slapd_connection, foo_group, bar_group):
    Group.ldap_object_attributes(conn=slapd_connection)
    assert foo_group != bar_group
    foo_group2 = Group.get(dn=foo_group.dn, conn=slapd_connection)
    assert foo_group == foo_group2
