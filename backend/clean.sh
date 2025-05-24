#!/bin/bash
# cleanup.sh

echo "Deleting macOS artifacts..."
find . -name '._*' -delete
find . -name '.DS_Store' -delete

echo "Deleting compiled Python files..."
find . -name '__pycache__' -type d -exec rm -r {} +
find . -name '*.pyc' -delete

echo "Done."
