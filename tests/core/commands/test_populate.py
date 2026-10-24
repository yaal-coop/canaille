import io

import pytest
from PIL import Image

from canaille.app import models
from canaille.commands import cli
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_populate_users(cli_runner, backend):
    """Test that the populate users command creates the specified number of users."""
    assert len(backend.query(models.User)) == 0
    res = cli_runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.User)) == 10
    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_users_with_avatars(testclient, backend):
    """Test that users are created with avatars in a format the backend supports."""
    users = fake_users(5)
    assert len(users) == 5

    expected = "PNG" if "PNG" in backend.photo_formats else "JPEG"
    for user in users:
        assert isinstance(user.photo, bytes)
        assert Image.open(io.BytesIO(user.photo)).format == expected

    for user in users:
        backend.delete(user)


def test_populate_groups(cli_runner, backend):
    """Test that the populate groups command creates the specified number of groups."""
    fake_users(10)

    assert len(backend.query(models.Group)) == 0
    res = cli_runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.Group)) == 10

    for group in backend.query(models.Group):
        backend.delete(group)

    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_groups_without_users(cli_runner, backend):
    """Test that groups can be populated without adding users to them."""
    if "ldap" in backend.__class__.__module__:
        pytest.skip()
    assert fake_groups(nb_users_max=0)


def test_fake_users_have_unique_user_names(testclient, backend, monkeypatch):
    """Fake users get distinct user names, even when faker suggests the same one twice."""
    from faker.providers.profile import Provider

    profile = Provider.profile
    user_names = iter(["jdoe", "jdoe", "jsmith"])

    def duplicated_profile(self, *args, **kwargs):
        result = profile(self, *args, **kwargs)
        result["username"] = next(user_names)
        return result

    monkeypatch.setattr(Provider, "profile", duplicated_profile)

    users = fake_users(2)

    assert sorted(user.user_name for user in users) == ["jdoe", "jsmith"]

    for user in users:
        backend.delete(user)
