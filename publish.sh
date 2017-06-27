#!/bin/bash
set -euo pipefail

PANDOC=pandoc

${PANDOC} -f markdown_github -t rst -o README.rst README.md
rm -rf dist
python setup.py sdist bdist_wheel
twine upload dist/*
rm README.rst
