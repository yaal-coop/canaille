#!/usr/bin/env python3
import configparser
import os
import sys
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

config = configparser.ConfigParser()
config.read("../setup.cfg")

# -- General configuration ------------------------------------------------


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_issues",
]

templates_path = ["_templates"]
source_suffix = [".rst"]
master_doc = "index"
project = "canaille"
copyright = "2020, Yaal"
author = "Yaal"

release = config["metadata"]["version"]
version = "%s.%s" % tuple(map(int, release.split(".")[:2]))
language = None
exclude_patterns = []
pygments_style = "sphinx"
todo_include_todos = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

issues_uri = "https://gitlab.com/yaal/canaille/-/issues/{issue}"
issues_pr_uri = "https://gitlab.com/yaal/canaille/-/merge_requests/{pr}"
issues_commit_uri = "https://gitlab.com/yaal/canaille/-/commit/{commit}"

# -- Options for HTML output ----------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = []


# -- Options for HTMLHelp output ------------------------------------------

htmlhelp_basename = "canailledoc"
html_logo = "_static/logo.png"


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
