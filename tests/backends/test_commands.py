import datetime
from typing import Annotated

import click

from canaille.backends.commands import click_type
from canaille.backends.commands import get_union_models
from canaille.backends.commands import is_multiple
from canaille.backends.commands import union_model_getter
from canaille.core.models import Group
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


def test_get_union_models(monkeypatch):
    """Test get_union_models function with various attribute types."""
    monkeypatch.setattr("canaille.backends.commands.MODELS", {})

    # Non-union types should return None
    assert get_union_models(str) is None
    assert get_union_models(User) is None
    assert get_union_models(User | None) is None
    assert get_union_models(list[User]) is None

    # Union with only one model should return None
    assert get_union_models(User | str) is None

    # Without backend models, a union of models cannot be resolved
    assert get_union_models(User | Group) is None


def test_get_union_models_in_app_context(app):
    """Test get_union_models within Flask app context where MODELS is populated."""
    with app.app_context():
        result = get_union_models(User | Group)
        assert result is not None
        assert len(result) == 2
        model_names = [name for name, _ in result]
        assert "user" in model_names
        assert "group" in model_names


def test_union_model_getter_empty_identifier(app, backend):
    """Test union_model_getter returns None for empty identifier."""
    with app.app_context():
        model_types = get_union_models(User | Group)
        getter = union_model_getter(model_types)
        assert getter("") is None
        assert getter(None) is None
