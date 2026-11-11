#!/usr/bin/env python3
"""Check that every character used in translated texts exists in both glyphs files."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / 'fonts'
OUT_DIR = ROOT / 'out'
CONTENTS_DIR = ROOT / 'contents'

def read_glyph_chars(path):
    """Return set of character codes (as ints) from a glyphs CSV."""
    chars = set()
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # skip header
        if header is None:
            return chars
        for row in reader:
            if not row:
                continue
            try:
                cp = int(row[0].strip())
                chars.add(cp)
            except (ValueError, IndexError):
                pass
    return chars


def collect_text_chars(texts):
    """Return set of Unicode code points for all non-ASCII chars (ord > 0x7E) across text strings."""
    chars = set()
    for t in texts:
        for ch in t:
            cp = ord(ch)
            if cp > 0x7E:
                chars.add(cp)
    return chars


def read_ui_tsv(path):
    """Read ui_ko.tsv, return list of Korean text strings (column 4, 0-indexed)."""
    texts = []
    try:
        with open(path, encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) >= 5:
                    val = row[4].strip()
                    if val:
                        texts.append(val)
    except FileNotFoundError:
        print(f"[WARN] {path} not found", file=sys.stderr)
    return texts


def read_dialogue_csvs(pattern):
    """Read all matching CSV files, return list of column-9 (0-indexed) text values."""
    texts = []
    files = sorted(ROOT.glob(pattern))
    for fp in files:
        try:
            with open(fp, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) >= 10:
                        val = row[9].strip()
                        if val:
                            texts.append(val)
        except Exception as e:
            print(f"[WARN] skipping {fp}: {e}", file=sys.stderr)
    return texts


def main():
    # ── 1. Read glyphs ──
    glyphs_text_path = FONTS_DIR / 'glyphs_text.csv'
    glyphs_header_path = FONTS_DIR / 'glyphs_header.csv'

    if not glyphs_text_path.exists():
        print(f"ERROR: {glyphs_text_path} not found", file=sys.stderr)
        sys.exit(1)
    if not glyphs_header_path.exists():
        print(f"ERROR: {glyphs_header_path} not found", file=sys.stderr)
        sys.exit(1)

    text_glyphs = read_glyph_chars(glyphs_text_path)
    header_glyphs = read_glyph_chars(glyphs_header_path)

    if not text_glyphs:
        print(f"ERROR: no glyphs found in {glyphs_text_path}", file=sys.stderr)
        sys.exit(1)
    if not header_glyphs:
        print(f"ERROR: no glyphs found in {glyphs_header_path}", file=sys.stderr)
        sys.exit(1)

    # ── 2. Read source texts ──
    ui_texts = read_ui_tsv(CONTENTS_DIR / 'ui_ko.tsv')

    dialogue_texts = read_dialogue_csvs('out/Dialogue/**/*.csv')

    # airshow_pre_mission.csv at root of out/
    airshow_texts = []
    airshow_path = OUT_DIR / 'airshow_pre_mission.csv'
    if airshow_path.exists():
        try:
            with open(airshow_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 10:
                        val = row[9].strip()
                        if val:
                            airshow_texts.append(val)
        except Exception as e:
            print(f"[WARN] {airshow_path}: {e}", file=sys.stderr)

    all_texts = ui_texts + dialogue_texts + airshow_texts
    used_chars = collect_text_chars(all_texts)

    # ── 3. Check ASCII printable range 0x20-0x7E ──
    missing_ascii_text = [cp for cp in range(0x20, 0x7F) if cp not in text_glyphs]
    missing_ascii_header = [cp for cp in range(0x20, 0x7F) if cp not in header_glyphs]

    # ── 4. Check all used non-ASCII chars exist in BOTH glyphs files ──
    missing_text = []
    missing_header = []
    for cp in sorted(used_chars):
        if cp not in text_glyphs:
            missing_text.append(cp)
        if cp not in header_glyphs:
            missing_header.append(cp)

    # ── 5. Report ──
    any_issue = False

    if missing_ascii_text:
        any_issue = True
        print("Missing ASCII chars (0x20-0x7E) in glyphs_text.csv:")
        for cp in missing_ascii_text:
            print(f"  U+{cp:04X} ({chr(cp)})")

    if missing_ascii_header:
        any_issue = True
        print("Missing ASCII chars (0x20-0x7E) in glyphs_header.csv:")
        for cp in missing_ascii_header:
            print(f"  U+{cp:04X} ({chr(cp)})")

    if missing_text:
        any_issue = True
        print(f"Characters used in texts but MISSING from glyphs_text.csv ({len(missing_text)}):")
        for cp in missing_text:
            label = chr(cp) if cp <= 0xFFFF else '?'
            print(f"  U+{cp:04X} ({label})")

    if missing_header:
        any_issue = True
        print(f"Characters used in texts but MISSING from glyphs_header.csv ({len(missing_header)}):")
        for cp in missing_header:
            label = chr(cp) if cp <= 0xFFFF else '?'
            print(f"  U+{cp:04X} ({label})")

    # ── Summary ──
    if any_issue:
        print(f"\nFAIL: {len(missing_text)} missing from glyphs_text, {len(missing_header)} missing from glyphs_header, "
              f"{len(missing_ascii_text)} ASCII missing from text glyphs, {len(missing_ascii_header)} ASCII missing from header glyphs",
              file=sys.stderr)
        sys.exit(1)
    else:
        ascii_ok = sum(1 for cp in range(0x20, 0x7F) if cp in text_glyphs and cp in header_glyphs)
        print(f"All characters covered — {len(used_chars)} non-ASCII + {ascii_ok} ASCII chars verified in both glyphs files.")
        sys.exit(0)


if __name__ == '__main__':
    main()