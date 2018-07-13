#!/bin/bash
set -euo pipefail

rm -rf dist
python setup.py sdist bdist_wheel
twine upload dist/*
