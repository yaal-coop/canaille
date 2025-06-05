import re
import textwrap

from pydantic import BaseModel
from pydantic import ValidationError
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings

try:
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


def export_object_to_toml(
    obj,
    with_comments: bool = True,
    with_defaults: bool = True,
    line_length: int = 80,
):
    """Create a tomlkit document from an object."""

    def is_complex(obj) -> bool:
        return isinstance(obj, list | dict | BaseModel | BaseSettings)

    if isinstance(obj, BaseModel | BaseSettings):
        doc = tomlkit.document() if isinstance(obj, BaseSettings) else tomlkit.table()
        for field_name, field_info in obj.__class__.model_fields.items():
            field_value = getattr(obj, field_name)
            display_value = field_value is not None and (
                isinstance(field_value, BaseModel | BaseSettings)
                or field_value != field_info.default
            )
            display_comments = with_comments and field_info.description
            display_default_value = (
                with_defaults
                and not is_complex(field_info.default)
                and not is_complex(field_value)
            )

            if display_comments and (display_default_value or display_value):
                sanitized = sanitize_comments(field_info.description, line_length)
                for line in sanitized.splitlines():
                    doc.add(tomlkit.comment(line))

            if display_default_value:
                parsed = (
                    tomlkit.item(field_info.default).as_string()
                    if field_info.default is not None
                    and field_info.default is not PydanticUndefined
                    else ""
                )
                doc.add(tomlkit.comment(f"{field_name} = {parsed}".strip()))

            sub_value = export_object_to_toml(field_value)
            if display_value:
                doc.add(field_name, sub_value)
            doc.add(tomlkit.nl())
        return doc

    elif isinstance(obj, list):
        max_inline_items = 4
        is_multiline = len(obj) > max_inline_items or all(
            is_complex(item) for item in obj
        )
        doc = tomlkit.array().multiline(is_multiline)

        for item in obj:
            sub_value = export_object_to_toml(item)
            doc.append(sub_value)
        return doc

    elif isinstance(obj, dict):
        inline = all(not is_complex(item) for item in obj.values())
        doc = tomlkit.inline_table() if inline else tomlkit.table()
        for key, value in obj.items():
            sub_value = export_object_to_toml(value)
            doc.add(key, sub_value)
        return doc

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
