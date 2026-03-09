#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

backup_file="pyproject.toml.py2app-backup"
build_log="dist/py2app-build.log"
dmg_log="dist/dmg-build.log"

cleanup() {
  if [[ -f "$backup_file" ]]; then
    mv "$backup_file" pyproject.toml
  fi
}

trap cleanup EXIT INT TERM

mv pyproject.toml "$backup_file"
mkdir -p dist

if ! uv run python setup.py py2app >"$build_log" 2>&1; then
  cat "$build_log"
  exit 1
fi

if ! hdiutil create dist/tmp.dmg -ov -volname "KanbanView" -fs HFS+ -srcfolder "dist" >"$dmg_log" 2>&1; then
  cat "$dmg_log"
  exit 1
fi

if ! hdiutil convert dist/tmp.dmg -format UDZO -o dist/KanbanView.dmg >>"$dmg_log" 2>&1; then
  cat "$dmg_log"
  exit 1
fi

rm dist/tmp.dmg
echo "py2app build completed. Full logs: $build_log, $dmg_log"
echo "Artifacts:"
echo "  dist/KanbanView.app"
echo "  dist/KanbanView.dmg"
open dist
