#!/usr/bin/env python3
import datetime
import os
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
    "sphinx_issues",
    "sphinx_sitemap",
]

templates_path = ["_templates"]
source_suffix = [".rst"]
master_doc = "index"
project = "canaille"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"

version = metadata.version("canaille")
language = "en"
exclude_patterns = []
pygments_style = "sphinx"
todo_include_todos = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "authlib": ("https://docs.authlib.org/en/latest", None),
    "flask": ("https://flask.palletsprojects.com", None),
    "flask-babel": ("https://python-babel.github.io/flask-babel", None),
    "flask-wtf": ("https://flask-wtf.readthedocs.io", None),
}

issues_uri = "https://gitlab.com/yaal/canaille/-/issues/{issue}"
issues_pr_uri = "https://gitlab.com/yaal/canaille/-/merge_requests/{pr}"
issues_commit_uri = "https://gitlab.com/yaal/canaille/-/commit/{commit}"

# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
html_static_path = []
html_baseurl = "https://canaille.readthedocs.io/"
html_theme_options = {
    "accent_color": "yellow",
    "gitlab_url": "https://gitlab.com/yaal/canaille",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "nav_links": [
        {
            "title": "Homepage",
            "url": "https://canaille.yaal.coop",
            "summary": "The homepage for the Canaille project",
        },
        {"title": "PyPI", "url": "https://pypi.org/project/Canaille/"},
    ],
}

# -- Options for HTMLHelp output ------------------------------------------

htmlhelp_basename = "canailledoc"
html_logo = "_static/logo.webp"


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
