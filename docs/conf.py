# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import sys
import django
sys.path.insert(0, '/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bibxml.settings')
django.setup()


# -- Project information -----------------------------------------------------

project = 'IETF BibXML service'
copyright = '2022'
author = 'Ribose under the IETF BibXML SOW'

# The full version, including alpha/beta/rc tags
release = '0.1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    # 'sphinx.ext.linkcode',
    'sphinx.ext.todo',
]

todo_include_todos = True

viewcode_follow_imported_members = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

extlinks = {
    'issue': (
        'https://github.com/ietf-ribose/bibxml-service/issues/%s',
        'bibxml-service GitHub issue #%s',
    ),
    'github': (
        'https://github.com/ietf-ribose/bibxml-service/blob/main/%s',
        '%s on GitHub',
    ),
}

html_css_files = [
    'custom.css',
]

autodoc_member_order = 'bysource'


primary_domain = 'py'


intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/stable', 'https://docs.djangoproject.com/en/stable/_objects/'),
}


# def linkcode_resolve(domain, info):
#     if domain != 'py':
#         return None
#     if not info['module']:
#         return None
#     filename = info['module'].replace('.', '/')
#     print(info)
#     return (
#         "https://github.com/ietf-ribose/bibxml-service/blob/main/{}.py"
#         .format(
#             filename,
#         )
#     )


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'haiku'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
