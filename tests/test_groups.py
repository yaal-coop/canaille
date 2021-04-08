from canaille.models import Group

def test_no_group(app, slapd_connection):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == []

def test_foo_group(app, slapd_connection, foo_group):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == [("foo", foo_group.dn)]