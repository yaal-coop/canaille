import datetime
import re
import textwrap
from inspect import isclass

from pydantic import BaseModel
from pydantic import ValidationError
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings

from canaille.backends.models import get_root_type

try:
    import isodate
    import tomlkit

    HAS_TOMLKIT = True
except ImportError:
    HAS_TOMLKIT = False


def sanitize_rst_text(text: str) -> str:
    """Remove inline RST syntax."""
    # Replace :foo:`~bar.Baz` with Baz
    text = re.sub(r":[\w:-]+:`~[\w\.]+\.(\w+)`", r"\1", text)

    # Replace :foo:`bar` and :foo:`bar <anything> with bar`
    text = re.sub(r":[\w:-]+:`([^`<]+)(?: <[^`>]+>)?`", r"\1", text)

    # Replace `label <URL>`_ with label (URL)
    text = re.sub(r"`([^`<]+) <([^`>]+)>`_", r"\1 (\2)", text)

    # Replace ``foo`` with `foo`
    text = re.sub(r"``([^`]+)``", r"\1", text)

    # Remove RST directives
    text = re.sub(r"\.\. [\w-]+::( \w+)?\n\n", "", text)

    return text


def sanitize_comments(text: str, line_length: int) -> str:
    """Remove RST syntax and wrap the docstring so it displays well as TOML comments."""

    def is_code_block(text: str) -> bool:
        return all(line.startswith("    ") for line in text.splitlines())

    def is_list(text: str) -> bool:
        return all(
            line.startswith("-") or line.startswith("  ") for line in text.splitlines()
        )

    text = sanitize_rst_text(text)
    paragraphs = text.split("\n\n")
    paragraphs = [
        textwrap.fill(paragraph, width=line_length)
        if not is_code_block(paragraph) and not is_list(paragraph)
        else paragraph
        for paragraph in paragraphs
    ]
    text = "\n\n".join(paragraphs)
    return text


def _is_complex(obj) -> bool:
    if isinstance(obj, BaseModel | BaseSettings):
        return True

    if isinstance(obj, list):
        return any(
            isinstance(item, list | dict | BaseModel | BaseSettings) for item in obj
        )

    if isinstance(obj, dict):
        return any(
            isinstance(value, list | dict | BaseModel | BaseSettings)
            for value in obj.values()
        )

    return False


def _python_to_toml(obj):
    if isinstance(obj, datetime.timedelta):
        return f'"{isodate.duration_isoformat(obj)}"'

    return (
        tomlkit.item(obj).as_string()
        if obj is not None and obj is not PydanticUndefined
        else ""
    )


def _export_model(obj, model, with_comments, with_defaults, line_length):
    doc = tomlkit.document() if isinstance(obj, BaseSettings) else tomlkit.table()
    for field_name, field_info in model.model_fields.items():
        field_value = getattr(obj, field_name) if obj is not None else None
        field_type = get_root_type(field_info.annotation)[0]
        is_model_type = isclass(field_type) and issubclass(
            field_type, BaseModel | BaseSettings
        )
        display_value = is_model_type or (
            field_value is not None and field_value != field_info.default
        )
        display_comments = with_comments and field_info.description
        display_default_value = (
            with_defaults
            and not _is_complex(field_info.default)
            and not _is_complex(field_value)
            and not is_model_type
        )

        if display_comments and (display_default_value or display_value):
            sanitized = sanitize_comments(field_info.description, line_length)
            for line in sanitized.splitlines():
                doc.add(tomlkit.comment(line))

        if display_default_value:
            parsed = _python_to_toml(field_info.default)
            doc.add(tomlkit.comment(f"{field_name} = {parsed}".strip()))

        if display_value:
            if is_model_type:
                sub_doc = _export_model(
                    field_value, field_type, with_comments, with_defaults, line_length
                )
            else:
                sub_doc = export_object_to_toml(field_value)
            doc.add(field_name, sub_doc)

        doc.add(tomlkit.nl())
    return doc


def _export_list(obj, with_comments, with_defaults, line_length):
    max_inline_items = 4
    is_multiline = len(obj) > max_inline_items or all(_is_complex(item) for item in obj)
    doc = tomlkit.array().multiline(is_multiline)

    for item in obj:
        sub_value = export_object_to_toml(item)
        doc.append(sub_value)
    return doc


def _export_dict(obj, with_comments, with_defaults, line_length):
    inline = all(not _is_complex(item) for item in obj.values())
    doc = tomlkit.inline_table() if inline else tomlkit.table()
    for key, value in obj.items():
        sub_value = export_object_to_toml(value)
        doc.add(key, sub_value)
    return doc


def export_object_to_toml(
    obj,
    with_comments: bool = True,
    with_defaults: bool = True,
    line_length: int = 80,
):
    """Create a tomlkit document from an object."""
    if isinstance(obj, BaseModel | BaseSettings):
        return _export_model(
            obj, obj.__class__, with_comments, with_defaults, line_length
        )

    elif isinstance(obj, list):
        return _export_list(obj, with_comments, with_defaults, line_length)

    elif isinstance(obj, dict):
        return _export_dict(obj, with_comments, with_defaults, line_length)

    elif isinstance(obj, datetime.timedelta):
        return isodate.duration_isoformat(obj)

    else:
        return obj


def export_config(model: BaseSettings):
    doc = export_object_to_toml(model)
    content = tomlkit.dumps(doc)

    # Remove end-of-line spaces
    content = re.sub(r" +\n", "\n", content)

    # Remove multiple new-lines
    content = re.sub(r"\n\n+", "\n\n", content)

    # Remove end-of-file new-line
    content = re.sub(r"\n+\Z", "\n", content)

    # De-double slashes
    content = re.sub(r"\\", "", content)

    return content


def example_settings(model: type[BaseModel]) -> BaseModel | None:
    """Init a pydantic BaseModel with values passed as Field 'examples'."""
    data = {
        field_name: field_info.examples[0]
        for field_name, field_info in model.model_fields.items()
        if field_info.examples
    }
    try:
        return model.model_validate(data)
    except ValidationError:  # pragma: no cover
        return None
