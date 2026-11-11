#!/bin/bash
set -e

WT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Step 1: Build fonts ==="
python3 "$WT/scripts/build_fonts.py"

echo "=== Step 2: Apply fonts to data.win ==="
export DOTNET_ROOT=$HOME/dotnet
/tmp/utmt/UndertaleModCli load "$WT/backup/data.win" -s "$WT/scripts/apply_fonts.csx" -o "$WT/out/data.win" --overwrite

echo "=== Step 3: Patch exe ==="
python3 "$WT/scripts/patch_exe.py"

echo "=== Done ==="
echo "Output:"
echo "  $WT/out/data.win"
echo "  $WT/out/Jet Lancer.exe"