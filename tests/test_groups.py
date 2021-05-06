from canaille.models import Group

def test_no_group(app, slapd_connection):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == []

def test_foo_group(app, slapd_connection, user, foo_group):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == [("foo", foo_group.dn)]
        assert foo_group.get_members(conn=slapd_connection) == [user]
        assert user.groups == [foo_group]
