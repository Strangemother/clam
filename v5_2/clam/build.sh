#!/bin/bash
# Build and install the clam package

cd "$(dirname "$0")"

echo "Building package..."
python -m build

echo ""
echo "Installing in editable mode..."
pip install -e .

echo ""
echo "Done! Test with: clam cli"
