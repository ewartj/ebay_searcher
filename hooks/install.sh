#!/usr/bin/env bash
# Installs the pre-commit hook into .git/hooks/
set -e
REPO_ROOT=$(git rev-parse --show-toplevel)
ln -sf "$REPO_ROOT/hooks/pre-commit" "$REPO_ROOT/.git/hooks/pre-commit"
chmod +x "$REPO_ROOT/hooks/pre-commit"
echo "pre-commit hook installed"
