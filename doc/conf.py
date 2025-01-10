#!/usr/bin/env python3
import datetime
import os
import pathlib
import sys
from importlib import metadata
from unittest import mock

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../canaille"))


# Readthedocs does not support C modules, so
# we have to mock them.


class Mock(mock.MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return mock.MagicMock()


MOCK_MODULES = ["ldap"]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# -- General configuration ------------------------------------------------


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_click",
    "sphinx_design",
    "sphinx_issues",
    "sphinxcontrib.autodoc_pydantic",
    "jinja_autodoc",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"
project = "canaille"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"

version = metadata.version("canaille")
language = "en"
exclude_patterns = []
pygments_style = "sphinx"
todo_include_todos = True
toctree_collapse = False
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "authlib": ("https://docs.authlib.org/en/latest", None),
    "flask": ("https://flask.palletsprojects.com", None),
    "flask-alembic": ("https://flask-alembic.readthedocs.io/en/latest", None),
    "flask-babel": ("https://python-babel.github.io/flask-babel", None),
    "flask-wtf": ("https://flask-wtf.readthedocs.io", None),
    "pydantic": ("https://docs.pydantic.dev/latest", None),
    "pytest-iam": ("https://pytest-iam.readthedocs.io/en/latest/", None),
    "wtforms": ("https://wtforms.readthedocs.io", None),
    "scim2-cli": ("https://scim2-cli.readthedocs.io/en/latest", None),
}

issues_uri = "https://gitlab.com/yaal/canaille/-/issues/{issue}"
issues_pr_uri = "https://gitlab.com/yaal/canaille/-/merge_requests/{pr}"
issues_commit_uri = "https://gitlab.com/yaal/canaille/-/commit/{commit}"

# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
html_static_path = ["_static"]
html_baseurl = "https://canaille.readthedocs.io/"
html_theme_options = {
    "globaltoc_expand_depth": 3,
    "accent_color": "yellow",
    "light_logo": "_static/canaille-label-black.webp",
    "dark_logo": "_static/canaille-label-white.webp",
    "gitlab_url": "https://gitlab.com/yaal/canaille",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "discussion_url": "https://matrix.to/#/#canaille-discuss:yaal.coop",
    "nav_links": [
        {
            "title": "Demo",
            "children": [
                {
                    "title": "Canaille demo server",
                    "url": "https://demo.canaille.yaal.coop",
                },
                {
                    "title": "OIDC Client 1",
                    "url": "https://demo.client1.yaal.coop",
                },
                {
                    "title": "OIDC Client 2",
                    "url": "https://demo.client2.yaal.coop",
                },
            ],
        },
        {"title": "PyPI", "url": "https://pypi.org/project/Canaille"},
        {
            "title": "Weblate",
            "url": "https://hosted.weblate.org/projects/canaille/canaille",
        },
    ],
}
html_context = {
    "source_type": "gitlab",
    "source_user": "yaal",
    "source_repo": "canaille",
    "source_version": "main",
    "source_docs_path": "/doc/",
    "languages": [
        ("English", "/en/latest/%s.html"),
        ("Français", "/fr/latest/%s.html"),
    ],
}

# -- Options for HTMLHelp output ------------------------------------------

htmlhelp_basename = "canailledoc"


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {}
latex_documents = [
    (master_doc, "canaille.tex", "canaille Documentation", "Yaal", "manual")
]

# -- Options for manual page output ---------------------------------------

man_pages = [(master_doc, "canaille", "canaille Documentation", [author], 1)]

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = [
    (
        master_doc,
        "canaille",
        "canaille Documentation",
        author,
        "canaille",
        "One line description of project.",
        "Miscellaneous",
    )
]

# -- Options for autosectionlabel -----------------------------------------

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

# -- Options for autodoc_pydantic_settings -------------------------------------------

autodoc_pydantic_settings_show_json = False
autodoc_pydantic_settings_show_config_summary = False
autodoc_pydantic_settings_show_config_summary = False
autodoc_pydantic_settings_show_validator_summary = False
autodoc_pydantic_settings_show_validator_members = False
autodoc_pydantic_settings_show_field_summary = False
autodoc_pydantic_settings_signature_prefix = ""
autodoc_pydantic_field_signature_prefix = ""
autodoc_pydantic_field_list_validators = False

# -- Translation options ------------------------------------------------------
# Advised by https://docs.readthedocs.io/en/latest/guides/manage-translations-sphinx.html#create-translatable-files
gettext_uuid = True
gettext_compact = "doc"

jinja_template_path = str(
    pathlib.Path(__file__).parent.parent.resolve() / "canaille/templates"
)
