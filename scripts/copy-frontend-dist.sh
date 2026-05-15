#!/usr/bin/env bash
# Copy frontend/dist/ into the backend's _web/static/ so the FastAPI app
# can serve the built React app at "/".
#
# Run after every `npm run build`. Idempotent.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/frontend/dist"
dst="$repo_root/backend/src/ra3_inventory/_web/static"

if [ ! -d "$src" ]; then
    echo "ERROR: $src not found — run 'cd frontend && npm run build' first" >&2
    exit 1
fi

rm -rf "$dst"
mkdir -p "$dst"
cp -R "$src"/* "$dst"/
# Preserve a .gitkeep-style marker so the dir is committed even when empty
# (the .gitignore excludes the actual built artifacts).
touch "$dst/.gitkeep"

echo "Copied frontend dist -> $dst"
echo "  $(find "$dst" -type f | wc -l | tr -d ' ') files, $(du -sh "$dst" | cut -f1) total"
