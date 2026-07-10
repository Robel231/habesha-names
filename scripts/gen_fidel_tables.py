"""Generate ``src/habesha_names/fidel/tables.py`` from the ``unicodedata`` module.

Fidel<->codepoint mappings must never be hand-typed (hallucination risk).
This script derives every mapping from ``unicodedata.name()`` over the
Ethiopic (U+1200-U+137F) and Ethiopic Supplement (U+1380-U+139F) blocks,
validates the expected block structure, and emits the tables module. It fails
loudly on any codepoint that does not fit the structure it knows about.

Usage:
    python scripts/gen_fidel_tables.py          # (re)write tables.py
    python scripts/gen_fidel_tables.py --check  # exit 1 if tables.py is stale
"""

from __future__ import annotations

import argparse
import difflib
import sys
import unicodedata
from pathlib import Path
from typing import NoReturn

NAME_PREFIX = "ETHIOPIC SYLLABLE "
SEBATBEIT_PREFIX = "SEBATBEIT "
MAIN_BLOCK = range(0x1200, 0x1380)
SUPPLEMENT_BLOCK = range(0x1380, 0x13A0)

# Unicode-name vowel suffix -> vowel order (1..7 traditional orders; 8 is the
# labialized/eighth column, whose Unicode names end in -WA, -OA or -WAA).
SUFFIX_TO_ORDER = {
    "A": 1,
    "U": 2,
    "I": 3,
    "AA": 4,
    "EE": 5,
    "E": 6,
    "O": 7,
    "WA": 8,
    "OA": 8,
    "WAA": 8,
}

# Supplement-block layout: 4-codepoint groups (base carries a "SEBATBEIT "
# name prefix) with these vowel suffixes per offset, i.e. orders 1, 3, 5, 6.
SUPPLEMENT_SUFFIX_BY_OFFSET = {0: "A", 1: "I", 2: "EE", 3: "E"}

# Consonant labels default to the lowercased Unicode consonant fragment
# (mechanical, no linguistic judgement). Entries below are LINGUISTIC DATA
# pending native-speaker review -- verified: false, listed in the PROGRESS.md
# human review queue.
LABEL_OVERRIDES = {
    # Ejective ts (U+1338 series); label pinned by IMPLEMENTATION_PLAN Task 1.
    "TS": "ts'",
}

OUT_PATH = Path(__file__).resolve().parents[1] / "src" / "habesha_names" / "fidel" / "tables.py"


def _fail(msg: str) -> NoReturn:
    raise SystemExit(f"gen_fidel_tables: unexpected Unicode structure: {msg}")


def collect_syllables() -> dict[int, str]:
    """Map each assigned ETHIOPIC SYLLABLE codepoint to its name minus the prefix."""
    syllables: dict[int, str] = {}
    for cp in [*MAIN_BLOCK, *SUPPLEMENT_BLOCK]:
        try:
            name = unicodedata.name(chr(cp))
        except ValueError:
            continue  # unassigned codepoint
        if name.startswith(NAME_PREFIX):
            syllables[cp] = name[len(NAME_PREFIX) :]
    if not syllables:
        _fail("no ETHIOPIC SYLLABLE codepoints found")
    return syllables


def parse_structure(
    syllables: dict[int, str],
) -> tuple[dict[int, str], dict[int, tuple[int, int]]]:
    """Derive series and per-syllable orders from Unicode names.

    Returns (series base codepoint -> consonant name fragment,
             syllable codepoint -> (series base codepoint, vowel order)).
    """
    series: dict[int, str] = {}
    entries: dict[int, tuple[int, int]] = {}

    # Main block: 8-aligned rows; row base is the first-order form and its name
    # minus the trailing "A" is the consonant fragment. Offset within the row
    # must agree with the vowel suffix (offset 7 is the order-8 column).
    for cp in sorted(c for c in syllables if c in MAIN_BLOCK):
        rest = syllables[cp]
        row = 0x1200 + ((cp - 0x1200) // 8) * 8
        offset = cp - row
        if row in syllables:
            base_rest = syllables[row]
            if not base_rest.endswith("A"):
                _fail(f"row base U+{row:04X} {base_rest!r} does not end with 'A'")
            frag = base_rest[:-1].rstrip()
            if rest.startswith(frag):
                suffix = rest[len(frag) :].lstrip()
                if suffix not in SUFFIX_TO_ORDER:
                    _fail(f"U+{cp:04X} {rest!r}: unknown vowel suffix {suffix!r}")
                order = SUFFIX_TO_ORDER[suffix]
                expected = 8 if offset == 7 else offset + 1
                if order != expected:
                    _fail(f"U+{cp:04X} {rest!r}: order {order} but row offset {offset}")
                series.setdefault(row, frag)
                entries[cp] = (row, order)
                continue
        # Standalone first-order syllable that does not fit its 8-aligned row
        # (observed: U+1359 MYA, U+135A FYA inside the RYA row).
        if not rest.endswith("A") or len(rest) < 2:
            _fail(f"U+{cp:04X} {rest!r}: neither row member nor standalone *A form")
        series[cp] = rest[:-1].rstrip()
        entries[cp] = (cp, 1)

    # Supplement block: 4-aligned groups of labialized forms.
    for group in range(SUPPLEMENT_BLOCK.start, SUPPLEMENT_BLOCK.stop, 4):
        members = [c for c in range(group, group + 4) if c in syllables]
        if not members:
            continue
        if group not in syllables:
            _fail(f"supplement group base U+{group:04X} unassigned but members exist")
        base_rest = syllables[group]
        if not base_rest.startswith(SEBATBEIT_PREFIX) or not base_rest.endswith("A"):
            _fail(f"supplement base U+{group:04X} {base_rest!r} not 'SEBATBEIT *A'")
        frag = base_rest[len(SEBATBEIT_PREFIX) : -1].rstrip()
        for cp in members:
            rest = syllables[cp]
            if rest.startswith(SEBATBEIT_PREFIX):
                rest = rest[len(SEBATBEIT_PREFIX) :]
            suffix = SUPPLEMENT_SUFFIX_BY_OFFSET[cp - group]
            if rest != frag + suffix:
                _fail(f"U+{cp:04X} {rest!r}: expected {frag + suffix!r}")
            entries[cp] = (group, SUFFIX_TO_ORDER[suffix])
        series[group] = frag

    return series, entries


def build_labels(series: dict[int, str]) -> dict[int, str]:
    """Assign a unique lowercase consonant label to every series base."""
    labels = {base: LABEL_OVERRIDES.get(frag, frag.lower()) for base, frag in series.items()}
    if len(set(labels.values())) != len(labels):
        _fail("consonant label collision across series")
    return labels


def render(
    syllables: dict[int, str],
    series: dict[int, str],
    entries: dict[int, tuple[int, int]],
    labels: dict[int, str],
) -> str:
    """Render the full text of tables.py."""
    table = {cp: (labels[base], order) for cp, (base, order) in sorted(entries.items())}
    reverse = {v: k for k, v in table.items()}
    if len(reverse) != len(table):
        _fail("(consonant, order) -> codepoint is not a bijection")

    overrides = ", ".join(f"{k!r} -> {v!r}" for k, v in sorted(LABEL_OVERRIDES.items()))
    lines = [
        "# GENERATED by scripts/gen_fidel_tables.py -- do not edit by hand.",
        "# Regenerate:      python scripts/gen_fidel_tables.py",
        "# Check freshness: python scripts/gen_fidel_tables.py --check",
        '"""Ethiopic Unicode tables (generated -- do not edit).',
        "",
        "Every fidel<->codepoint mapping here is derived programmatically from",
        "``unicodedata.name()`` over the Ethiopic (U+1200-U+137F) and Ethiopic",
        "Supplement (U+1380-U+139F) blocks; nothing is hand-typed.",
        "",
        "Vowel orders follow the traditional analysis (ARCHITECTURE 4.1):",
        "1=ä, 2=u, 3=i, 4=a, 5=é, 6=ə/bare, 7=o; order 8 is the labialized/",
        "eighth column (Unicode -WA/-OA/-WAA forms).",
        "",
        "Consonant labels are the lowercased Unicode consonant name fragments",
        f"except for these overrides: {overrides}. The overrides are unreviewed",
        'linguistic data ("verified": false) -- see the PROGRESS.md human review',
        "queue.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "#: Blocks treated as Ethiopic script, as (first, last) inclusive codepoint",
        "#: pairs. The Extended block is recognized by ``is_ethiopic()`` but has no",
        "#: syllable table in v0.1.",
        "ETHIOPIC_RANGES: tuple[tuple[int, int], ...] = (",
        "    (0x1200, 0x137F),  # Ethiopic",
        "    (0x1380, 0x139F),  # Ethiopic Supplement",
        "    (0x2D80, 0x2DDF),  # Ethiopic Extended",
        ")",
        "",
        "#: Vowel order assigned to the labialized/eighth column.",
        "LABIALIZED_ORDER = 8",
        "",
        "#: Series base codepoint -> consonant label.",
        "CONSONANT_BY_BASE: dict[int, str] = {",
    ]
    for base in sorted(labels):
        lines.append(f"    0x{base:04X}: {labels[base]!r},  # {chr(base)} {series[base]}")
    lines += [
        "}",
        "",
        "#: Syllable codepoint -> (consonant label, vowel order).",
        "SYLLABLES: dict[int, tuple[str, int]] = {",
    ]
    for cp, (label, order) in table.items():
        lines.append(f"    0x{cp:04X}: ({label!r}, {order}),  # {chr(cp)} {syllables[cp]}")
    lines += [
        "}",
        "",
        "#: (consonant label, vowel order) -> syllable codepoint. A bijection;",
        "#: verified by the generator.",
        "CODEPOINT_BY_SYLLABLE: dict[tuple[str, int], int] = {",
        "    syllable: cp for cp, syllable in SYLLABLES.items()",
        "}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed tables.py matches regenerated output",
    )
    args = parser.parse_args()

    syllables = collect_syllables()
    series, entries = parse_structure(syllables)
    labels = build_labels(series)
    text = render(syllables, series, entries, labels)

    if args.check:
        if not OUT_PATH.exists():
            print(f"MISSING: {OUT_PATH}", file=sys.stderr)
            return 1
        current = OUT_PATH.read_text(encoding="utf-8")
        if current != text:
            print(f"STALE: {OUT_PATH} differs from regenerated output:", file=sys.stderr)
            diff = difflib.unified_diff(
                current.splitlines(), text.splitlines(), "committed", "regenerated", lineterm=""
            )
            for i, line in enumerate(diff):
                if i >= 20:
                    print("  ...", file=sys.stderr)
                    break
                print(f"  {line}".encode("ascii", "backslashreplace").decode(), file=sys.stderr)
            return 1
        print(f"OK: {OUT_PATH.name} is current ({len(entries)} syllables, {len(series)} series)")
        return 0

    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT_PATH} ({len(entries)} syllables, {len(series)} series)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
