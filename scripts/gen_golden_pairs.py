"""Generate ``tests/golden/pairs.json`` -- the Task 8 golden match corpus.

Every pair is MECHANICALLY derived from the seeded lexicon (Task 4, itself
``verified: false``) and the plan/architecture name lists; no pair is a
claim about real people, and the agent that wrote this is not a native
speaker. All pairs therefore ship ``"needs_human": true`` for Robel to
review, prune, and extend with real-world confusables.

Expected outcomes follow ARCHITECTURE §6: same-person pairs must score
>= SAME_MIN, different-person pairs <= DIFFERENT_MAX. Pairs whose score at
generation time violates their threshold are kept and marked
``"known_fail": true`` instead of being dropped -- they are honest records
of current engine limits, and the golden test asserts they KEEP failing so
any improvement forces a conscious corpus regeneration.

Usage:
    python scripts/gen_golden_pairs.py          # (re)write the corpus
    python scripts/gen_golden_pairs.py --check  # exit 1 if the file is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from habesha_names._data import lexicon
from habesha_names.match.full import match
from habesha_names.translit.variants import variants

CORPUS_PATH = Path(__file__).resolve().parents[1] / "tests" / "golden" / "pairs.json"

#: ARCHITECTURE §6 gates: same-person >= 0.85, different-person <= 0.6.
SAME_MIN = 0.85
DIFFERENT_MAX = 0.60

#: Names whose rule-engine variants seed same-person pairs. All come from
#: IMPLEMENTATION_PLAN / ARCHITECTURE §4.2 or the seeded lexicon canonicals.
RULE_VARIANT_ANCHORS = (
    "Tsehay",
    "Tesfaye",
    "Kebede",
    "Alemu",
    "Bekele",
    "Getachew",
    "Gebre",
    "Gebremedhin",
    "Hailemariam",
    "Mohammed",
    "Bethlehem",
    "Desalegn",
)

#: Full-name same-person pairs exercising one matcher feature each.
#: Name material is limited to plan/architecture strings + lexicon seeds.
FULL_NAME_SAME = (
    ("Abebe Bikila Wolde", "Abebe Bikila", "truncation tolerance: avonym absent on one side"),
    ("Abebe Bikila", "Bikila Abebe", "swap tolerance: given/patronym order swapped"),
    ("Bikila, Abebe", "Abebe Bikila", "comma inversion ('patronym, given')"),
    ("Ato Abebe Bikila", "Abebe Bikila", "leading title stripped before matching"),
    ("ወይዘሮ ጸሐይ ገብረመድህን", "Tsehay Gebremedhin", "fidel input + title vs Latin"),
    ("ፀሐይ ገብረመድህን", "ጸሀይ ገብረመድህን", "fidel homophone spellings"),
    ("Hailemariam Desalegn", "Haile Mariam Desalegn", "spaced vs joined compound given name"),
    ("Gebremedhin Tesfaye", "G/Medhin Tesfaye", "slash abbreviation expanded"),
    ("Gebremedhin Tesfaye", "G.Medhin Tesfaye", "dot abbreviation expanded"),
    ("Gebremedhin Tesfaye", "Gebre Medhin Tesfaye", "spaced compound joined"),
    ("Gebremedhin Tesfaye", "Gebre-Medhin Tesfaye", "hyphenated compound form"),
    ("Tsehay Gebremedhin", "Tsehai G/Medhin", "spelling variant + abbreviation combined"),
    ("Mohammed Hussein", "Mahamed Husen", "Arabic-origin spelling group, both tokens"),
    ("Tesfaye Kebede Alemu", "Tesfay Kebbede Allemu", "three tokens, one rewrite each"),
    ("ኃይለ ሥላሴ", "Haile Selassie", "phonetic key bridges the Task 3 Selassie xfail"),
)

#: Single-token different-person confusables pinned by the plan (§6, Task 6).
CONFUSABLE_DIFFERENT = (
    ("Alemu", "Almaz"),
    ("Tesfaye", "Tesfahun"),
    ("Tesfaye", "Tesfa"),
    ("Abebe", "Abebech"),
)

#: Full-name different-person pairs (distinct lexicon names). The last two
#: share a patronym/avonym (sibling-style records) and are expected to land
#: in the review zone above DIFFERENT_MAX -- kept as known_fail records.
FULL_NAME_DIFFERENT = (
    ("Abebe Bikila", "Kebede Alemu", "unrelated names, both tokens differ"),
    ("Tsehay Gebremedhin", "Almaz Tesfahun", "unrelated names, both tokens differ"),
    ("Girma Wolde", "Bekele Haile", "unrelated names, both tokens differ"),
    ("Tesfaye Girma", "Tesfahun Girma", "sibling-style: different given, shared patronym"),
    ("Abebe Bikila Wolde", "Abebech Bikila Wolde", "sibling-style: shared patronym and avonym"),
)

#: How many mechanically-found near-miss different pairs to keep.
NEAR_MISS_COUNT = 25


def _entry(a: str, b: str, expected: str, source: str) -> dict[str, object]:
    """Build one corpus entry, scoring it and marking threshold violations."""
    score = round(float(match(a, b)), 4)
    entry: dict[str, object] = {
        "a": a,
        "b": b,
        "expected": expected,
        "source": source,
        "needs_human": True,
        "score_at_generation": score,
    }
    passes = score >= SAME_MIN if expected == "same" else score <= DIFFERENT_MAX
    if not passes:
        entry["known_fail"] = True
    return entry


def build_pairs() -> list[dict[str, object]]:
    """Derive the full corpus, deduplicated, in deterministic order."""
    entries: list[dict[str, object]] = []
    seen: set[frozenset[str]] = set()

    def add(a: str, b: str, expected: str, source: str) -> None:
        key = frozenset((a, b))
        if a == b or key in seen:
            return
        seen.add(key)
        entries.append(_entry(a, b, expected, source))

    names = lexicon().given_names
    for entry in names:
        add(entry.fidel, entry.canonical, "same", "lexicon: fidel spelling vs canonical Latin")
    for entry in names:
        for variant in entry.variants:
            add(entry.canonical, variant, "same", "lexicon: canonical vs seeded variant")
    for anchor in RULE_VARIANT_ANCHORS:
        for variant in variants(anchor)[1:7]:
            add(anchor, variant, "same", "rule engine: top variants() output")
    for a, b, feature in FULL_NAME_SAME:
        add(a, b, "same", f"matcher feature: {feature}")
    for a, b in CONFUSABLE_DIFFERENT:
        add(a, b, "different", "plan-pinned confusable (similar but different names)")
    for a, b, why in FULL_NAME_DIFFERENT:
        add(a, b, "different", f"full-name negatives: {why}")

    # Mechanical near-misses: the highest-scoring pairs of DISTINCT lexicon
    # canonicals (distinct entries = different names by construction; the
    # loader rejects any spelling shared between two entries).
    canonicals = [entry.canonical for entry in names]
    scored = sorted(
        (
            (round(float(match(a, b)), 4), a, b)
            for i, a in enumerate(canonicals)
            for b in canonicals[i + 1 :]
        ),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    for _score, a, b in scored[:NEAR_MISS_COUNT]:
        add(a, b, "different", "mechanical near-miss: highest-scoring distinct canonicals")
    return entries


def render() -> str:
    pairs = build_pairs()
    payload = {
        "schema": 1,
        "note": (
            "GENERATED by scripts/gen_golden_pairs.py -- do not hand-edit; "
            "regenerate instead. Every pair is agent-derived from the "
            "unverified seed lexicon and flagged needs_human for Robel, who "
            "extends this corpus with real-world confusables (flip "
            "needs_human on reviewed pairs THROUGH the generator or replace "
            "it once human curation starts). known_fail marks current "
            "engine limits: the golden test asserts these keep failing."
        ),
        "thresholds": {"same_min": SAME_MIN, "different_max": DIFFERENT_MAX},
        "pairs": pairs,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed corpus matches regeneration; exit 1 if stale",
    )
    args = parser.parse_args(argv)
    rendered = render()
    count = rendered.count('"a":')
    if args.check:
        if not CORPUS_PATH.exists():
            print(f"MISSING: {CORPUS_PATH}", file=sys.stderr)
            return 1
        if CORPUS_PATH.read_text(encoding="utf-8") != rendered:
            print(f"STALE: {CORPUS_PATH} does not match regeneration", file=sys.stderr)
            return 1
        print(f"OK: pairs.json is current ({count} pairs)")
        return 0
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(rendered, encoding="utf-8")
    print(f"WROTE: {CORPUS_PATH} ({count} pairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
