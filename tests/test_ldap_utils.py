from canaille.models import Group

def test_equality(slapd_connection, foo_group, bar_group):
    Group.attr_type_by_name(conn=slapd_connection)
    assert foo_group != bar_group
    foo_group2 = Group.get(dn=foo_group.dn, conn=slapd_connection)
    assert foo_group == foo_group2