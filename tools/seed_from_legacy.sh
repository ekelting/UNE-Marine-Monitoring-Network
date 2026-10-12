#!/usr/bin/env bash
# One-time import: if a buoy has no data in this repo yet, copy the full data history from its old
# stand-alone repository (public, listed as legacy_repo in buoys.json). Safe to run every time.
set -euo pipefail
slug="$1"; legacy="$2"
dest="buoys/$slug/data"
if [ -f "$dest/state.json" ]; then echo "📦 $slug already has data — no import needed"; exit 0; fi
if [ -z "$legacy" ] || [ "$legacy" = "null" ]; then echo "📦 $slug is new — starting fresh"; exit 0; fi
echo "📦 importing $slug history from ekelting/$legacy ..."
tmp="$(mktemp -d)"
git clone -q --depth 1 "https://github.com/ekelting/$legacy" "$tmp"
mkdir -p "$dest"
cp -a "$tmp/data/." "$dest/"
rm -f "$dest/.gitkeep"
rm -rf "$tmp"
echo "📦 imported $(find "$dest" -type f | wc -l) files"
