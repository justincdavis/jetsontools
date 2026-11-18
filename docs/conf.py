# Copyright (c) 2024 Justin Davis (davisjustin302@gmail.com)
#
# MIT License
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.metadata
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "src")))

# -- Project information -----------------------------------------------------

project = "jetsontools"
copyright = "2024, Justin Davis"
author = "Justin Davis"
version = importlib.metadata.version("jetsontools")

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "myst_parser",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]

templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/modules.rst"]

napoleon_use_ivar = True

autodoc_default_options = {
    "member-order": "bysource",
    "show-inheritance": True,
    "separator": "---",
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"
html_theme_options = {
    "sidebar_hide_name": False,
}
html_static_path = ["_static"]

html_show_sourcelink = False
html_title = "jetsontools"
html_copy_source = False

html_sidebars = {
    "**": ["sidebar/scroll-start.html", "sidebar/brand.html", "sidebar/navigation.html", "sidebar/scroll-end.html"],
}

html_css_files = [
    "center.css",
]
