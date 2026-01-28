#!/usr/bin/env bash
# Clean Python cache and pytest caches to avoid stale artifacts interfering with test collection
# Usage: ./backend/scripts/dev/clean_pycache.sh
set -euo pipefail

echo "Removing __pycache__ directories..."
find . -type d -name '__pycache__' -print0 | xargs -0 rm -rf || true

echo "Removing .pyc files..."
find . -type f -name '*.pyc' -print0 | xargs -0 rm -f || true

# Remove pytest cache and .pytest_cache if present
if [ -d .pytest_cache ]; then
  echo "Removing .pytest_cache..."
  rm -rf .pytest_cache
fi

# Also remove pip cache directories sometimes present in CI/workspaces
if [ -d "$(pwd)/.cache" ]; then
  echo "Removing local .cache directory..."
  rm -rf .cache || true
fi

echo "Clean complete."
