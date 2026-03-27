#!/bin/bash

echo "Cleaning Python cache files..."

find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -name ".DS_Store" -delete
find . -type d -name ".ipynb_checkpoints" -exec rm -r {} +
find . -type d -name ".pytest_cache" -exec rm -r {} +
find . -type d -name ".mypy_cache" -exec rm -r {} +

echo "Done."