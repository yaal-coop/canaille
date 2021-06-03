from canaille.models import Group, User


def test_no_group(app, slapd_connection):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == []


def test_set_groups(app, slapd_connection, user, foo_group, bar_group):
    with app.app_context():
        Group.attr_type_by_name(conn=slapd_connection)
        a = User.attr_type_by_name(conn=slapd_connection)

        user = User.get(dn=user.dn, conn=slapd_connection)
        assert set(Group.available_groups(conn=slapd_connection)) == {
            ("foo", foo_group.dn),
            ("bar", bar_group.dn),
        }
        foo_dns = {g.dn for g in foo_group.get_members(conn=slapd_connection)}
        assert user.dn in foo_dns
        assert user.groups[0].dn == foo_group.dn

        user.set_groups([foo_group, bar_group], conn=slapd_connection)
        bar_dns = {g.dn for g in bar_group.get_members(conn=slapd_connection)}
        assert user.dn in bar_dns

        assert user.groups[1].dn == bar_group.dn

        user.set_groups([foo_group], conn=slapd_connection)
        foo_dns = {g.dn for g in foo_group.get_members(conn=slapd_connection)}
        bar_dns = {g.dn for g in bar_group.get_members(conn=slapd_connection)}

        assert user.dn in foo_dns
        assert user.dn not in bar_dns
