import datetime

import pytest
import time_machine

from canaille.app import models


def test_model_comparison(testclient, backend):
    foo1 = models.User(
        user_name="foo",
        family_name="foo",
        formatted_name="foo",
    )
    foo1.save()
    bar = models.User(
        user_name="bar",
        family_name="bar",
        formatted_name="bar",
    )
    bar.save()
    foo2 = backend.get(models.User, id=foo1.id)

    assert foo1 == foo2
    assert foo1 != bar

    foo1.delete()
    bar.delete()


def test_model_lifecycle(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
    )

    assert not user.id
    assert not backend.query(models.User)
    assert not backend.query(models.User, id=user.id)
    assert not backend.query(models.User, id="invalid")
    assert not backend.get(models.User, id=user.id)

    user.save()

    assert backend.query(models.User) == [user]
    assert backend.query(models.User, id=user.id) == [user]
    assert not backend.query(models.User, id="invalid")
    assert backend.get(models.User, id=user.id) == user

    user.family_name = "new_family_name"

    assert user.family_name == "new_family_name"

    user.reload()

    assert user.family_name == "family_name"

    user.delete()

    assert not backend.query(models.User, id=user.id)
    assert not backend.get(models.User, id=user.id)

    user.delete()


def test_model_attribute_edition(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
        display_name="display_name",
        emails=["email1@user.com", "email2@user.com"],
    )
    user.save()

    assert user.user_name == "user_name"
    assert user.family_name == "family_name"
    assert user.emails == ["email1@user.com", "email2@user.com"]

    user = backend.get(models.User, id=user.id)
    assert user.user_name == "user_name"
    assert user.family_name == "family_name"
    assert user.emails == ["email1@user.com", "email2@user.com"]

    user.family_name = "new_family_name"
    user.emails = ["email1@user.com"]
    user.save()

    assert user.family_name == "new_family_name"
    assert user.emails == ["email1@user.com"]

    user = backend.get(models.User, id=user.id)
    assert user.family_name == "new_family_name"
    assert user.emails == ["email1@user.com"]

    user.display_name = ""
    assert not user.display_name

    user.save()
    assert not user.display_name

    user.delete()


def test_model_indexation(testclient, backend):
    user = models.User(
        user_name="user_name",
        family_name="family_name",
        formatted_name="formatted_name",
        emails=["email1@user.com", "email2@user.com"],
    )
    user.save()

    assert backend.get(models.User, family_name="family_name") == user
    assert not backend.get(models.User, family_name="new_family_name")
    assert backend.get(models.User, emails=["email1@user.com"]) == user
    assert backend.get(models.User, emails=["email2@user.com"]) == user
    assert not backend.get(models.User, emails=["email3@user.com"])

    user.family_name = "new_family_name"
    user.emails = ["email2@user.com"]

    assert backend.get(models.User, family_name="family_name") != user
    assert backend.get(models.User, emails=["email1@user.com"]) != user
    assert not backend.get(models.User, emails=["email3@user.com"])

    user.save()

    assert not backend.get(models.User, family_name="family_name")
    assert backend.get(models.User, family_name="new_family_name") == user
    assert not backend.get(models.User, emails=["email1@user.com"])
    assert backend.get(models.User, emails=["email2@user.com"]) == user
    assert not backend.get(models.User, emails=["email3@user.com"])

    user.delete()

    assert not backend.get(models.User, family_name="family_name")
    assert not backend.get(models.User, family_name="new_family_name")
    assert not backend.get(models.User, emails=["email1@user.com"])
    assert not backend.get(models.User, emails=["email2@user.com"])
    assert not backend.get(models.User, emails=["email3@user.com"])


def test_fuzzy_unique_attribute(user, moderator, admin, backend):
    assert set(backend.query(models.User)) == {user, moderator, admin}
    assert set(backend.fuzzy(models.User, "Jack")) == {moderator}
    assert set(backend.fuzzy(models.User, "Jack", ["formatted_name"])) == {moderator}
    assert set(backend.fuzzy(models.User, "Jack", ["user_name"])) == set()
    assert set(backend.fuzzy(models.User, "Jack", ["user_name", "formatted_name"])) == {
        moderator
    }
    assert set(backend.fuzzy(models.User, "moderator")) == {moderator}
    assert set(backend.fuzzy(models.User, "oderat")) == {moderator}
    assert set(backend.fuzzy(models.User, "oDeRat")) == {moderator}
    assert set(backend.fuzzy(models.User, "ack")) == {moderator}


def test_fuzzy_multiple_attribute(user, moderator, admin, backend):
    assert set(backend.query(models.User)) == {user, moderator, admin}
    assert set(backend.fuzzy(models.User, "jack@doe.com")) == {moderator}
    assert set(backend.fuzzy(models.User, "jack@doe.com", ["emails"])) == {moderator}
    assert set(backend.fuzzy(models.User, "jack@doe.com", ["formatted_name"])) == set()
    assert set(
        backend.fuzzy(models.User, "jack@doe.com", ["emails", "formatted_name"])
    ) == {moderator}
    assert set(backend.fuzzy(models.User, "ack@doe.co")) == {moderator}
    assert set(backend.fuzzy(models.User, "doe.com")) == {user, moderator, admin}


def test_model_references(testclient, user, foo_group, admin, bar_group, backend):
    assert foo_group.members == [user]
    assert user.groups == [foo_group]
    assert foo_group in backend.query(models.Group, members=user)
    assert user in backend.query(models.User, groups=foo_group)

    assert user not in bar_group.members
    assert bar_group not in user.groups
    user.groups = user.groups + [bar_group]
    user.save()
    bar_group.reload()

    assert user in bar_group.members
    assert bar_group in user.groups

    bar_group.members = [admin]
    bar_group.save()
    user.reload()

    assert user not in bar_group.members
    assert bar_group not in user.groups


def test_model_creation_edition_datetime(testclient, backend):
    if "ldap" in backend.__class__.__module__:
        pytest.skip()

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        user = models.User(
            user_name="foo",
            family_name="foo",
            formatted_name="foo",
        )
        user.save()
        assert user.created == datetime.datetime(
            2020, 1, 1, 2, tzinfo=datetime.timezone.utc
        )
        assert user.last_modified == datetime.datetime(
            2020, 1, 1, 2, tzinfo=datetime.timezone.utc
        )

    with time_machine.travel("2021-01-01 02:00:00+00:00", tick=False):
        user.family_name = "bar"
        user.save()
        assert user.created == datetime.datetime(
            2020, 1, 1, 2, tzinfo=datetime.timezone.utc
        )
        assert user.last_modified == datetime.datetime(
            2021, 1, 1, 2, tzinfo=datetime.timezone.utc
        )

    user.delete()
