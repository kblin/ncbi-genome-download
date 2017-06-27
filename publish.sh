#!/bin/bash
set -euo pipefail

PANDOC=pandoc

${PANDOC} -f markdown_github -t rst -o README.rst README.md
python setup.py sdist upload -r pypi
rm README.rst
