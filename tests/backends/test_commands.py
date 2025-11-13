import datetime
from typing import Annotated

import click

from canaille.backends.commands import click_type
from canaille.backends.commands import is_multiple
from canaille.core.models import User


def test_click_type():
    """Test click_type function with various attribute types."""
    assert click_type(bool) == click.BOOL
    assert click_type(bool | None) == click.BOOL
    assert click_type(list[bool]) == click.BOOL

    assert click_type(datetime.datetime) == datetime.datetime.fromisoformat
    assert click_type(datetime.datetime | None) == datetime.datetime.fromisoformat

    assert callable(click_type(User))
    assert callable(click_type(User | None))
    assert callable(click_type(list[User]))
    assert callable(click_type(Annotated[User, {"backref": "groups"}]))
    assert callable(click_type(list[Annotated[User, {"backref": "groups"}]]))

    assert click_type(str) is str
    assert click_type(int) is int
    assert click_type(str | None) is str
    assert click_type(list[str]) is str


def test_is_multiple():
    """Test is_multiple function with various attribute types."""
    assert is_multiple(list[str]) is True
    assert is_multiple(str) is False
    assert is_multiple(str | None) is False
