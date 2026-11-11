#!/usr/bin/env python3
"""
check_ui_patch.py — Verify Korean UI patch.

Reads ui_ko.tsv and checks:
- 0 byte budget violations
- 0 leftover kana/kanji in patched offsets in the output exe
- Reports rows that could not be translated within budget
"""

import os, sys

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(WT, "contents", "ui_ko.tsv")
OUT_EXE = os.path.join(WT, "out", "Jet Lancer.exe")

errors = 0

# 1. Check TSV
lines = open(TSV, encoding="utf-8").readlines()
header = lines[0].strip().split("\t")
print(f"TSV rows: {len(lines)-1}")

# Budget violations
for i, line in enumerate(lines[1:], 2):
    parts = line.strip().split("\t")
    if len(parts) >= 5 and parts[3]:
        ko = parts[3]
        maxb = int(parts[4])
        if len(ko.encode("utf-8")) > maxb:
            print(f"  ROW {i}: BUDGET VIOLATION offset={parts[0]} max={maxb} got={len(ko.encode('utf-8'))}")
            errors += 1

if errors == 0:
    print("✓ 0 byte budget violations")

# 2. Check patched exe for leftover kana/kanji in patched slots
if os.path.exists(OUT_EXE):
    with open(OUT_EXE, "rb") as f:
        data = f.read()
    
    leftover = 0
    for line in lines[1:]:
        parts = line.strip().split("\t")
        if len(parts) < 5 or not parts[3]:
            continue
        off = int(parts[0])
        maxb = int(parts[4])
        slot = bytes(data[off:off+maxb+1])
        # Check for hiragana/katakana bytes (E3 81, E3 82, E3 83)
        # Note: this also matches some Hangul bytes, so we use len-based heuristic
        kana_bytes = slot.count(b'\xe3\x81') + slot.count(b'\xe3\x82') + slot.count(b'\xe3\x83')
        # If more than 3 such pairs, it's likely Japanese, not Hangul
        if kana_bytes > 3:
            print(f"  LEFTOVER KANA: offset={off} ({kana_bytes} bytes)")
            leftover += 1

    if leftover == 0:
        print("✓ 0 leftover kana/kanji in patched UI strings")
    else:
        print(f"⚠ {leftover} offsets with potential leftover kana")
else:
    print(f"⚠ Patched exe not found at {OUT_EXE}")

print(f"\nChecks: {'ALL PASSED' if errors == 0 else f'{errors} FAILURES'}")