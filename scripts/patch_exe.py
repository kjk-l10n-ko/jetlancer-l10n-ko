#!/usr/bin/env python3
"""
patch_exe.py — Patch Jet Lancer.exe with Korean UI strings.

Applies IN-PLACE patches for Korean text that fits in the Japanese slot,
and RE-POINTING for ASCII text identical to English/Japanese that overflows.
Writes to WT/out/Jet Lancer.exe (file size unchanged).
"""

import os
import sys
import struct

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP = os.path.join(WT, "backup", "Jet Lancer.exe")
OUT_EXE = os.path.join(WT, "out", "Jet Lancer.exe")
TSV = os.path.join(WT, "contents", "ui_ko.tsv")

TABLE_START = 17707584
FIRST_JAPANESE_OFFSET = 17877417
TABLE_END = 17924981

DATA_FILE_OFF = 0x10d6200
DATA_VA = 0x10d7000
IMAGEBASE = 0x400000

TEXT_FILE_START = 0x400
TEXT_FILE_SIZE = 0xfb2e00
RDATA_FILE_START = 0xfb3200
RDATA_FILE_SIZE = 0x123000

SPARE_OFF = 17877847  # '武器使用' slot (13B), emptied by re-pointing SPECIAL WEAPON to English
LANG_NAME_OFF = 17707638
JP_LANG_BYTES = b"\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"  # 日本語
KO_LANG_BYTES = b"\xed\x95\x9c\xea\xb5\xad\xec\x96\xb4"  # 한국어


JP_CODE_LO, JP_CODE_HI = 5759700, 5829000  # code range that handles the Japanese slot (find_foreign_refs.py)
done_cards_off = {}
CARD_TEXT = [
    ("REINFORCEMENTS mk1", "지원 부대 mk1"), ("REINFORCEMENTS mk2", "지원 부대 mk2"), ("REINFORCEMENTS mk3", "지원 부대 mk3"),
    ("SPREADSHOT mk1", "산탄 mk1"), ("SPREADSHOT mk2", "산탄 mk2"),
    ("MINIGUN SPEED mk1", "기총 연사 mk1"), ("MINIGUN SPEED mk2", "기총 연사 mk2"),
    ("DRONE SPAWN", "드론 생성"), ("EXPLOSIVE PRIMARY", "폭발 기총"),
    ("AFTERBURNER mk1", "애프터번 mk1"), ("AFTERBURNER mk2", "애프터번 mk2"), ("AFTERBURNER mk3", "애프터번 mk3"),
    ("PRIMARY DAMAGE", "기총 대미지"), ("RELOAD mk1", "재장전 mk1"), ("RELOAD mk2", "재장전 mk2"),
    ("PRIMARY CRIT", "기총 크리티컬"), ("SUPER RELOAD mk1", "슈퍼 재장전 mk1"), ("SUPER RELOAD mk2", "슈퍼 재장전 mk2"),
    ("ROCKET SWARM", "로켓 일제 사격"), ("BOMB", "폭탄"), ("LASER", "레이저"), ("DRONES", "드론"), ("EMP", "EMP"),
    ("GUIDED MISSILE", "유도 미사일"), ("PROXY CHARGE", "근접 신관"), ("RAILGUN", "레일건"),
    ("UNGUIDED MISSILE", "비유도 미사일"), ("ROCKET HACK", "로켓 해킹"), ("DASH", "대시"), ("SHIELD", "실드"),
    ("OVERHEAT BLAST", "오버히트 블라스트"), ("BLAST RADIUS mk1", "폭발 반경 mk1"), ("BLAST RADIUS mk2", "폭발 반경 mk2"),
    ("Fire rate", "연사 속도"), ("Skill", "스킬"), ("Amount", "수량"), ("Chance", "확률"), ("Heat decrease", "열 감소"),
    ("Damage", "대미지"), ("Reload speed", "재장전 속도"), ("Radius", "반경"),
]
# (offset of the Latin name in the name table, Latin, Korean)
NAME_TABLE = [
    (17707653, "Ash", "애쉬"), (17707657, "Captain", "함장"), (17707665, "Lem", "렘"),
    (17707669, "Sailor", "선원"), (17707676, "Pierce", "피어스"), (17707683, "Black Knight", "블랙 나이트"),
    (17707696, "Gin", "진"), (17707700, "Peter", "피터"), (17707706, "Steve", "스티브"),
    (17707712, "Hex", "헥스"), (17707716, "Lex", "렉스"), (17707732, "AEGIS", "이지스"),
    (17707738, "Colonel Hardaway", "하다웨이 대령"),
]


def load_relocs(b):
    """File offsets of every 32-bit HIGHLOW relocation target (PE32)."""
    pe = struct.unpack("<I", b[0x3C:0x40])[0]
    ns = struct.unpack("<H", b[pe + 6 : pe + 8])[0]
    sec = pe + 0x18 + struct.unpack("<H", b[pe + 0x14 : pe + 0x16])[0]
    secs = [struct.unpack("<IIII", b[sec + i * 40 + 8 : sec + i * 40 + 24]) for i in range(ns)]
    rva, size = struct.unpack("<II", b[pe + 0x18 + 0x60 + 5 * 8 : pe + 0x18 + 0x60 + 5 * 8 + 8])

    def r2o(r):
        for vs, v, rs, ro in secs:
            if v <= r < v + rs:
                return ro + r - v

    out, o = set(), r2o(rva)
    end = o + size
    while o < end:
        pg, sz = struct.unpack("<II", b[o : o + 8])
        for k in range(8, sz, 2):
            e = struct.unpack("<H", b[o + k : o + k + 2])[0]
            if e >> 12 == 3:
                out.add(r2o(pg + (e & 0xFFF)))
        o += sz
    return out


def file_off_to_va(file_off):
    return file_off - DATA_FILE_OFF + DATA_VA + IMAGEBASE


def main():
    if not os.path.exists(BACKUP):
        print(f"ERROR: Backup not found at {BACKUP}")
        sys.exit(1)

    with open(BACKUP, "rb") as f:
        data = bytearray(f.read())
    original_size = len(data)

    # Read TSV
    rows = []
    with open(TSV, encoding="utf-8") as f:
        header = f.readline()  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 5 and parts[3]:
                rows.append(
                    (
                        int(parts[0]),  # jp_offset
                        parts[1],  # english
                        parts[2],  # japanese_original
                        parts[3],  # korean
                        int(parts[4]),  # max_bytes
                    )
                )

    rows.sort(key=lambda x: x[0])

    # Compute actual slot sizes (distance to next string)
    for i in range(len(rows)):
        off = rows[i][0]
        next_off = rows[i + 1][0] if i + 1 < len(rows) else TABLE_END
        rows[i] = rows[i] + (next_off - off,)  # append slot_size

    in_place_count = 0
    re_pointed_count = 0
    error_count = 0

    for jp_offset, english, jp_orig, korean, max_bytes, slot_size in rows:
        ko_bytes = korean.encode("utf-8")
        ko_len = len(ko_bytes)
        jp_orig_bytes = jp_orig.encode("utf-8")

        # --- Determine strategy ---
        if (
            korean.isascii()
            and (korean.strip() == english.strip() or korean == jp_orig)
            and ko_len > max_bytes
        ):
            # ---- RE-POINTING ----
            eng_block = data[TABLE_START:FIRST_JAPANESE_OFFSET]
            eng_stripped = english.strip()
            eng_search = eng_stripped.encode("utf-8")

            eng_off = None
            # Try <NUL><text><NUL>
            idx = eng_block.find(b"\x00" + eng_search + b"\x00")
            if idx != -1:
                eng_off = TABLE_START + idx + 1
            else:
                # Try <text><NUL> (first string at block start)
                idx = eng_block.find(eng_search + b"\x00")
                if idx != -1:
                    eng_off = TABLE_START + idx
                else:
                    # Try raw TSV english (as-is, no strip)
                    eng_raw = english.encode("utf-8")
                    idx = eng_block.find(b"\x00" + eng_raw + b"\x00")
                    if idx != -1:
                        eng_off = TABLE_START + idx + 1
                    else:
                        idx = eng_block.find(eng_raw + b"\x00")
                        if idx != -1:
                            eng_off = TABLE_START + idx

            if eng_off is None:
                print(
                    f"  ERROR: offset {jp_offset} - English text "
                    f"{eng_stripped!r} not found in English block"
                )
                error_count += 1
                continue

            jp_va = file_off_to_va(jp_offset)
            eng_va = file_off_to_va(eng_off)
            jp_bytes_le = struct.pack("<I", jp_va)
            eng_bytes_le = struct.pack("<I", eng_va)

            # Replace VA refs in .text and .rdata
            replacements = 0
            for seg_start, seg_size in [
                (TEXT_FILE_START, TEXT_FILE_SIZE),
                (RDATA_FILE_START, RDATA_FILE_SIZE),
            ]:
                pos = seg_start
                seg_end = seg_start + seg_size
                while True:
                    pos = data.find(jp_bytes_le, pos, seg_end)
                    if pos == -1:
                        break
                    data[pos : pos + 4] = eng_bytes_le
                    replacements += 1
                    pos += 4

            if replacements == 0:
                print(
                    f"  ERROR: offset {jp_offset} - no VA references found "
                    f"for jp_va=0x{jp_va:08X}"
                )
                error_count += 1
                continue

            # NUL out the Japanese slot
            data[jp_offset : jp_offset + slot_size] = b"\x00" * slot_size
            re_pointed_count += 1
            print(
                f"  RE-POINT: {korean!r} (off {jp_offset}) -> eng "
                f"0x{eng_va:08X} ({replacements} refs)"
            )

        elif ko_len <= max_bytes:
            # ---- IN-PLACE ----
            # Assert original bytes match Japanese text
            actual_raw = bytes(data[jp_offset : jp_offset + len(jp_orig_bytes)])
            if actual_raw != jp_orig_bytes:
                print(
                    f"  ERROR: offset {jp_offset} - expected "
                    f"{jp_orig_bytes!r} but found {actual_raw!r}"
                )
                error_count += 1
                continue

            # Verify Korean fits in slot
            if ko_len + 1 > slot_size:
                print(
                    f"  ERROR: offset {jp_offset} - Korean {ko_len}B + NUL "
                    f"does not fit in {slot_size}B slot"
                )
                error_count += 1
                continue

            # Write Korean bytes + NUL padding to fill slot
            padded = ko_bytes + b"\x00" * (slot_size - ko_len)
            data[jp_offset : jp_offset + slot_size] = padded
            in_place_count += 1

        else:
            print(
                f"  ERROR: offset {jp_offset} - Korean too long: "
                f"{ko_len} > {max_bytes} for {korean!r}"
            )
            error_count += 1

    # --- JP code branch reuses Chinese/other strings the JP table lacks ---
    # (find_foreign_refs.py lists them). Without this the Korean font has no
    # glyph for them and the label renders blank (e.g. the E-key row).
    # (code location of the 32-bit immediate, Chinese text, English-block text | None, Korean text)
    foreign = [
        (5765554, "武器 3", "WEAPON 3", None),
        (5765657, "武器 4", "WEAPON 4", None),
        (5813060, "特殊武器", "SPECIAL WEAPON", None),
        (5814667, "高", "HIGH", None),
        (5815133, "高", "HIGH", None),
        (5814755, "最高", "HIGHEST", None),
        (5815076, "低", "LOW", None),
        (5828480, "加速", None, "가속"),
    ]
    eng_block = bytes(data[TABLE_START:FIRST_JAPANESE_OFFSET])
    spare = SPARE_OFF  # NUL-filled slack (old 武器使用 slot) holding extra Korean strings
    for loc, zh, eng, ko in foreign:
        old_va = struct.unpack("<I", data[loc : loc + 4])[0]
        old_off = old_va - IMAGEBASE - DATA_VA + DATA_FILE_OFF
        if bytes(data[old_off : old_off + len(zh.encode())]) != zh.encode():
            print(f"  ERROR: foreign ref @{loc} does not point at {zh!r}")
            error_count += 1
            continue
        if eng is not None:
            i = eng_block.find(b"\x00" + eng.encode() + b"\x00")
            new_off = TABLE_START + i + 1
        else:
            assert not any(data[spare : spare + 13]), "spare slot not empty"
            data[spare : spare + len(ko.encode())] = ko.encode()
            new_off, spare = spare, spare + len(ko.encode()) + 1
        data[loc : loc + 4] = struct.pack("<I", file_off_to_va(new_off))
        print(f"  FOREIGN: {zh!r} @{loc} -> {eng or ko!r}")

    # --- Speaker name tags: language-neutral table at 17707648 (Ash, Captain, ...) ---
    # Hangul names are longer than the Latin ones, so each name is written into free
    # NUL tail space of a long Korean slot and every relocated 32-bit pointer to the old
    # name is re-pointed (same technique as the foreign refs above).
    relocs = load_relocs(bytes(data))
    free = []  # [start, end) NUL tails after each row's text
    for jp_offset, _e, _j, _k, _m, slot_size in rows:
        end = jp_offset + slot_size
        s = jp_offset + data[jp_offset:end].index(b"\x00") + 1
        if end - s > 0 and not any(data[s:end]):
            free.append([s, end])
    free.sort(key=lambda r: r[0] - r[1])  # largest first
    for name_off, latin, ko in NAME_TABLE:
        old = latin.encode()
        if bytes(data[name_off : name_off + len(old) + 1]) != old + b"\x00":
            print(f"  ERROR: name table @{name_off} is not {latin!r}")
            error_count += 1
            continue
        new = ko.encode() + b"\x00"
        if len(new) <= len(old) + 1:  # fits in place
            data[name_off : name_off + len(old) + 1] = new + b"\x00" * (len(old) + 1 - len(new))
            print(f"  NAME in place: {latin} -> {ko}")
            continue
        region = next((r for r in free if r[1] - r[0] >= len(new)), None)
        if region is None:
            print(f"  ERROR: no free space for name {ko!r}")
            error_count += 1
            continue
        new_off = region[0]
        region[0] += len(new)
        data[new_off : new_off + len(new)] = new
        old_va, new_va = file_off_to_va(name_off), file_off_to_va(new_off)
        n = 0
        for loc in relocs:
            if struct.unpack("<I", data[loc : loc + 4])[0] == old_va:
                data[loc : loc + 4] = struct.pack("<I", new_va)
                n += 1
        data[name_off : name_off + len(old) + 1] = b"\x00" * (len(old) + 1)
        print(f"  NAME re-point: {latin} -> {ko} ({n} refs)")
        if n == 0:
            error_count += 1

    # --- Upgrade-card titles / stat labels: English-only strings referenced by the JP code branch ---
    # Only reloc'd pointers inside the JP branch (JP_CODE_LO..HI) are re-pointed, so other languages keep English.
    card = dict(CARD_TEXT)
    done_cards = set()
    for loc in sorted(relocs):
        if not (JP_CODE_LO <= loc <= JP_CODE_HI):
            continue
        va_ = struct.unpack("<I", data[loc : loc + 4])[0]
        off = va_ - IMAGEBASE - DATA_VA + DATA_FILE_OFF
        if not (TABLE_START <= off < FIRST_JAPANESE_OFFSET):
            continue
        end = data.index(b"\x00", off)
        txt = bytes(data[off:end]).decode("utf-8", "replace")
        if txt not in card:
            continue
        new = card[txt].encode() + b"\x00"
        if txt in done_cards:  # same string already written: reuse its new address
            new_off = done_cards_off[txt]
        else:
            region = next((r for r in free if r[1] - r[0] >= len(new)), None)
            if region is None:
                print(f"  ERROR: no free space for card text {card[txt]!r}")
                error_count += 1
                continue
            new_off = region[0]
            region[0] += len(new)
            data[new_off : new_off + len(new)] = new
            done_cards.add(txt)
            done_cards_off[txt] = new_off
        data[loc : loc + 4] = struct.pack("<I", file_off_to_va(new_off))
    missing = set(card) - done_cards
    print(f"  CARD text: {len(done_cards)} re-pointed" + (f", MISSING {sorted(missing)}" if missing else ""))
    if missing:
        error_count += 1

    # --- Language name patch: 日本語 -> 한국어 ---
    lang_actual = bytes(data[LANG_NAME_OFF : LANG_NAME_OFF + 9])
    if lang_actual == JP_LANG_BYTES:
        data[LANG_NAME_OFF : LANG_NAME_OFF + 9] = KO_LANG_BYTES
        print("  Language name: 日本語 -> 한국어")
    else:
        print(
            f"  WARNING: Language name mismatch at offset {LANG_NAME_OFF}: "
            f"expected {JP_LANG_BYTES.hex()} but found {lang_actual.hex()}"
        )

    if len(data) != original_size:
        print(f"  WARNING: File size changed! {len(data)} vs {original_size}")

    os.makedirs(os.path.dirname(OUT_EXE), exist_ok=True)
    with open(OUT_EXE, "wb") as f:
        f.write(data)

    summary = f"In-place: {in_place_count}, Re-pointed: {re_pointed_count}, Errors: {error_count}"
    print(f"\n{summary}")
    print(f"Written: {OUT_EXE}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()