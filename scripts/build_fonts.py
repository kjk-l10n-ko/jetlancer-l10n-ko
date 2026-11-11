#!/usr/bin/env python3
"""Build Korean font textures for Jet Lancer with proper Hangul coverage.

Generates two font variants:
  - text   (cell_h=79, advance_w=53)  from tex129_raw.png + glyphs_fo_text_jap.csv
  - header (cell_h=119, advance_w=80) from tex130_raw.png + glyphs_fo_header_jap.csv

New Hangul/punctuation glyphs are rendered with Noto Sans KR at a fixed baseline,
then packed into a texture ≤ 8192 px tall.  Latin glyphs are copied unchanged.
"""

import csv
import glob as glob_mod
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / 'fonts'
TTF_PATH = ROOT.parent / 'tools-l10n-ko' / 'tools' / 'font' / 'assets' / '구글' / 'Noto Sans KR' / 'static_NotoSansKR-Regular.ttf'

# ── Character ranges ──

# ASCII printable + common Latin‑1
LATIN_CODES = (
    list(range(0x0020, 0x007F))
    + [0x00A0, 0x00A1, 0x00A2, 0x00A3, 0x00A5, 0x00A6, 0x00A7,
       0x00A9, 0x00AB, 0x00AC, 0x00AE, 0x00B0, 0x00B1, 0x00B5,
       0x00B6, 0x00B7, 0x00BB, 0x00BF]
)
LATIN_SET = frozenset(LATIN_CODES)

# Hangul Compatibility Jamo (U+3131..U+318E)
JAMO_CODES = list(range(0x3131, 0x318F))  # 94 chars

# Additional punctuation rendered with Hangul font
PUNCTUATION_CODES = [
    0x2026, 0x2014, 0x2013, 0x2015, 0x00B7, 0x2018, 0x2019,
    0x201C, 0x201D, 0x3001, 0x3002, 0x300C, 0x300D, 0x301C, 0xFF5E,
]

ROW_GAP = 2  # pixel gap between texture rows

# ── Hangul frequency ordering (most common first) ──
# CV syllables first (final = 0), then by final consonant frequency
_HANGUL_ORDERED = []
for i in range(19):
    for m in range(21):
        _HANGUL_ORDERED.append(0xAC00 + i * 588 + m * 28 + 0)
_FINALS_BY_FREQ = [4, 8, 16, 17, 1, 21, 12, 19, 22, 23, 24, 25, 26,
                   9, 18, 2, 3, 5, 6, 7, 10, 11, 13, 14, 15, 20, 27]
for f in _FINALS_BY_FREQ:
    for i in range(19):
        for m in range(21):
            cp = 0xAC00 + i * 588 + m * 28 + f
            if cp < 0xD7A4:
                _HANGUL_ORDERED.append(cp)

# Set of all 2350 cp949-encodable Hangul syllables (KS X 1001)
CP949_HANGUL = {0xAC00 + i for i in range(2350)}


# ── Helpers ──

def load_glyphs(csv_path):
    with open(csv_path, newline='') as f:
        return {int(r['char']): r for r in csv.DictReader(f, delimiter=';')}


def extract_glyph(tex_arr, g):
    x = int(g['srcX'])
    y = int(g['srcY'])
    w = int(g['srcW'])
    h = int(g['srcH'])
    return tex_arr[y:y + h, x:x + w, :4].copy()


def get_used_chars():
    """Return set of Unicode code points actually used in translated content.

    This is the set for pruning: characters that will be kept when the
    header texture is too tall.  It does NOT include all cp949 Hangul —
    those are the full candidate set that is pruned *down to* this set.

    Collects from:
    - Hangul syllables found in ui_ko.tsv (col 4)
    - Hangul syllables found in Dialogue CSVs (col 9)
    - Hangul syllables found in airshow_pre_mission.csv (col 9)
    - Extrapunctuation codes
    - Jamo codes
    """
    used = set()

    # ui_ko.tsv column 4 (0‑indexed: 3)
    ui_path = ROOT / 'contents' / 'ui_ko.tsv'
    if ui_path.exists():
        with open(ui_path, encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    for ch in parts[3]:
                        cp = ord(ch)
                        if 0xAC00 <= cp <= 0xD7A3:
                            used.add(cp)

    # Dialogue CSV files (recursive) column 9
    for csv_path in sorted(glob_mod.glob(
            str(ROOT / 'out' / 'Dialogue' / '**' / '*.csv'), recursive=True)):
        try:
            with open(csv_path, encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 10:
                        for ch in row[9]:
                            cp = ord(ch)
                            if 0xAC00 <= cp <= 0xD7A3:
                                used.add(cp)
        except Exception:
            pass  # skip unreadable files

    # airshow_pre_mission.csv column 9
    air_path = ROOT / 'out' / 'airshow_pre_mission.csv'
    if air_path.exists():
        try:
            with open(air_path, encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 10:
                        for ch in row[9]:
                            cp = ord(ch)
                            if 0xAC00 <= cp <= 0xD7A3:
                                used.add(cp)
        except Exception:
            pass

    used.update(PUNCTUATION_CODES)
    used.update(JAMO_CODES)
    return used


def measure_baseline(orig_arr, glyph_e):
    """Return baseline y‑offset within a cell by inspecting Latin 'E'.

    The bottommost non‑transparent pixel row of the capital E marks the
    baseline; the returned value is one row below it (the 'ls' anchor point).
    """
    pix = extract_glyph(orig_arr, glyph_e)
    alpha = pix[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    if rows.any():
        return int(np.where(rows)[0][-1]) + 1
    return int(glyph_e['srcH']) - 2  # fallback


def render_korean(font, char_code, cell_h, baseline_y):
    """Render *char_code* on a *cell_h*‑tall canvas, anchored at baseline_y.

    Returns (RGBA array, cropped_width, cell_h, advance) — only horizontal
    cropping is applied; the full cell height is preserved.
    """
    ch = chr(char_code)
    advance = round(font.getlength(ch))
    canvas_w = advance + 20  # generous left/right margin

    temp = Image.new('RGBA', (canvas_w, cell_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp)
    draw.text((5, baseline_y), ch, fill=(255, 255, 255, 255),
              font=font, anchor='ls')
    arr = np.array(temp)

    alpha = arr[:, :, 3]
    cols = np.any(alpha > 0, axis=0)
    if not cols.any():
        # Completely empty glyph (e.g. space) — return zero‑width slab
        return None, 0, cell_h, advance

    x_min, x_max = np.where(cols)[0][[0, -1]]
    cropped = arr[:, x_min:x_max + 1, :4].copy()
    return cropped, x_max - x_min + 1, cell_h, advance


# ── Font builder ──

def build_font(texture_name, cell_h, advance_w, orig_tex_file, orig_csv_file,
               max_tex_h=8192, used_set=None):
    """Build one combined texture (Latin + Jamo + Punctuation + Hangul).

    Parameters
    ----------
    texture_name : str   —  'text' or 'header'
    cell_h       : int   —  height of every glyph cell in the new texture
    advance_w    : int   —  fallback advance for Latin
    orig_tex_file, orig_csv_file : original Japanese texture + CSV
    max_tex_h    : int   —  maximum texture height (default 8192)
    used_set     : set   —  Unicode code points that are actually needed;
                            used for pruning when the header variant is too tall.
    """
    print(f"\n── {texture_name} "
          f"(cell_h={cell_h}, advance={advance_w}, max_h={max_tex_h}) ──")

    # ── Load originals ────────────────────────────────────────────────
    orig_tex = Image.open(FONTS_DIR / orig_tex_file).convert('RGBA')
    orig_arr = np.array(orig_tex)
    orig_glyphs = load_glyphs(FONTS_DIR / orig_csv_file)

    # ── Baseline ──────────────────────────────────────────────────────
    e_glyph = orig_glyphs[69]
    baseline_y = measure_baseline(orig_arr, e_glyph)
    print(f"  Baseline from E: y={baseline_y} within {cell_h} px cell")

    # ── Font size ─────────────────────────────────────────────────────
    font_sz = max(30, cell_h - 30)
    font = ImageFont.truetype(str(TTF_PATH), font_sz)

    # test render
    _, tw, th, ta = render_korean(font, 0xAC00, cell_h, baseline_y)
    hangul_shift = ta  # uniform shift for all Hangul = advance of '가'
    print(f"  Font size {font_sz}: '가' = {tw}×{th}, advance={hangul_shift}")

    # ── Build glyph-info lists ────────────────────────────────────────

    # 1. Latin — copied unchanged from original texture
    latin_infos = []  # (code, pix_array, rw, rh, shift, offset)
    for code in LATIN_CODES:
        if code in orig_glyphs:
            g = orig_glyphs[code]
            pix = extract_glyph(orig_arr, g)
            latin_infos.append((code, pix,
                                int(g['srcW']), int(g['srcH']),
                                int(g['shift']), int(g['offset'])))
    print(f"  Latin: {len(latin_infos)} chars (from original)")

    # 2. Jamo — rendered
    jamo_infos = []  # (code, pix_array, rw, rh, advance)
    for code in JAMO_CODES:
        pix, rw, rh, adv = render_korean(font, code, cell_h, baseline_y)
        jamo_infos.append((code, pix, rw, rh, adv))
    print(f"  Jamo:  {len(jamo_infos)} chars")

    # 3. Punctuation — rendered (skip codes already covered by Latin)
    punct_infos = []  # (code, pix_array, rw, rh, advance)
    for code in PUNCTUATION_CODES:
        if code in LATIN_SET:
            continue  # already copied from original
        pix, rw, rh, adv = render_korean(font, code, cell_h, baseline_y)
        punct_infos.append((code, pix, rw, rh, adv))
    print(f"  Punct: {len(punct_infos)} chars")

    # 4. Hangul syllables — cp949 set (frequency ordered) + extras from text beyond cp949
    hangul_codes = [cp for cp in _HANGUL_ORDERED if cp in CP949_HANGUL]
    if used_set:
        extra = sorted(c for c in used_set
                       if 0xAC00 <= c <= 0xD7A3 and c not in CP949_HANGUL
                       and c not in hangul_codes)
        hangul_codes.extend(extra)
        if extra:
            print(f"  Extra Hangul beyond cp949: {len(extra)} chars")
    hangul_infos = []  # (code, pix_array, rw, rh, advance)
    for code in hangul_codes:
        pix, rw, rh, adv = render_korean(font, code, cell_h, baseline_y)
        hangul_infos.append((code, pix, rw, rh, adv))
    print(f"  Hangul: {len(hangul_infos)} chars pre-rendered")

    # ── Texture packing ───────────────────────────────────────────────
    TEX_W = 4096
    row_h = cell_h + ROW_GAP

    tex = Image.new('RGBA', (TEX_W, max_tex_h), (0, 0, 0, 0))
    tex_arr = np.array(tex)
    glyph_map = {}

    x = ROW_GAP
    y = ROW_GAP

    def pack_glyph(code, pix_arr, rw, _rh, shift_val, offset_val):
        """Place one glyph at (x, y), advancing position.  Returns True."""
        nonlocal x, y

        if pix_arr is None or rw == 0:
            # Empty glyph — minimal placeholder
            if y + row_h > max_tex_h:
                return False
            glyph_map[code] = (x, y, 1, cell_h, max(shift_val or 1, 1), offset_val or 0)
            x += 2
            return True

        slot_w = rw + 2

        # Wrap to next row?
        if x + slot_w > TEX_W:
            x = ROW_GAP
            y += row_h
            if y + row_h > max_tex_h:
                return False

        # Paste pixel data (assumed ≤ cell_h tall and fits slot_w wide)
        ph = pix_arr.shape[0]
        pw = pix_arr.shape[1]
        if ph > 0 and pw > 0:
            tex_arr[y:y + ph, x:x + pw, :] = pix_arr[:, :, :]

        glyph_map[code] = (x, y, rw, cell_h, shift_val, offset_val)
        x += slot_w
        return True

    def run_pack(stage_order):
        """Pack from *stage_order* lists in sequence; return True if all fit."""
        nonlocal x, y
        x, y = ROW_GAP, ROW_GAP
        glyph_map.clear()
        for stage in stage_order:
            for item in stage:
                if not pack_glyph(*item):
                    return False
        return True

    # Pack order: Latin, Jamo, Punctuation, Hangul
    latin_items = [(c, p, r, h, s, o) for (c, p, r, h, s, o) in latin_infos]
    jamo_items = [(c, p, r, h, hangul_shift, 0) for (c, p, r, h, _) in jamo_infos]
    punct_items = [(c, p, r, h, hangul_shift, 0) for (c, p, r, h, _) in punct_infos]
    hangul_items = [(c, p, r, h, hangul_shift, 0) for (c, p, r, h, _) in hangul_infos]

    stages = [latin_items, jamo_items, punct_items, hangul_items]
    fitted = run_pack(stages)

    if not fitted and used_set is not None:
        # Header variant: drop Hangul syllables not in the used set
        kept = [(c, p, r, h, hangul_shift, 0)
                for (c, p, r, h, _, _) in hangul_items if c in used_set]
        dropped = len(hangul_items) - len(kept)
        print(f"  Header too tall: dropping {dropped} unused syllables, "
              f"keeping {len(kept)} needed ones …")
        hangul_items[:] = kept
        fitted = run_pack(stages)

    if not fitted:
        # Last resort: pack until full
        print("  Still doesn't fit — packing until full …")
        x, y = ROW_GAP, ROW_GAP
        glyph_map.clear()
        for stage in stages:
            for item in stage:
                if not pack_glyph(*item):
                    break

    # ── Trim, save, report ────────────────────────────────────────────
    actual_h = y + row_h
    actual_h = min(actual_h, max_tex_h)

    assert actual_h <= max_tex_h, \
        f"Texture height {actual_h} > {max_tex_h}"

    tex_arr = tex_arr[:actual_h, :, :]
    out_png = FONTS_DIR / f'tex_{texture_name}.png'
    Image.fromarray(tex_arr, 'RGBA').save(out_png)
    print(f"  Texture: {TEX_W}×{actual_h}  → {out_png.name}")

    csv_out = FONTS_DIR / f'glyphs_{texture_name}.csv'
    with open(csv_out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['char', 'srcX', 'srcY', 'srcW', 'srcH', 'shift', 'offset'])
        for code, (sx, sy, sw, sh, sft, off) in sorted(glyph_map.items()):
            w.writerow([code, sx, sy, sw, sh, sft, off])
    print(f"  Glyph map: {len(glyph_map)} entries  → {csv_out.name}")

    # Stats
    rows_used = (actual_h - ROW_GAP) // row_h
    han_count = sum(1 for c in glyph_map if 0xAC00 <= c <= 0xD7A3)
    jam_count = sum(1 for c in glyph_map if 0x3131 <= c <= 0x318E)
    lat_count = sum(1 for c in glyph_map if c not in CP949_HANGUL and c not in JAMO_CODES
                     and c not in PUNCTUATION_CODES)
    pct = sum(sw * sh for _, _, sw, sh, _, _ in glyph_map.values()) / (TEX_W * actual_h) * 100
    print(f"  Rows: {rows_used}  |  Latin: {lat_count}  Jamo: {jam_count}  "
          f"Hangul: {han_count}  Total: {len(glyph_map)}")
    print(f"  Height: {actual_h} px  |  Util: {pct:.1f}%")

    return glyph_map


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    if not TTF_PATH.exists():
        print(f"FATAL: TTF not found at {TTF_PATH}", file=sys.stderr)
        sys.exit(1)

    used = get_used_chars()
    han_used = sum(1 for c in used if 0xAC00 <= c <= 0xD7A3)
    print(f"Used chars: {len(used)} unique code points "
          f"({han_used} Hangul syllables)")

    build_font('text', cell_h=79, advance_w=53,
               orig_tex_file='tex129_raw.png',
               orig_csv_file='glyphs_fo_text_jap.csv',
               max_tex_h=8192, used_set=used)

    build_font('header', cell_h=119, advance_w=80,
               orig_tex_file='tex130_raw.png',
               orig_csv_file='glyphs_fo_header_jap.csv',
               max_tex_h=8192, used_set=used)

    print("\n✓ Done.")