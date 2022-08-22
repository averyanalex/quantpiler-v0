import sys
import os
import re

sys.path.insert(0, os.path.abspath(".."))

project = "Quantpiler"
author = "Alexander Averyanov"
copyright = "2022, Alexander Averyanov"

version = ""
with open("../quantpiler/__init__.py") as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE
    ).group(1)

release = version

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "nbsphinx",
]

nbsphinx_execute = "never"
autodoc_mock_imports = ["qiskit"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
