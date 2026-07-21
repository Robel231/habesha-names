"""Generate ``tests/golden/pairs.json`` -- the Task 8 golden match corpus.

The corpus has TWO sources, and the ``source`` field on every pair says
which one it came from:

1. **Generated** (the original Task 8 population). MECHANICALLY derived from
   the seeded lexicon (Task 4) and the plan/architecture name lists; no pair
   is a claim about real people, and the agent that wrote this is not a
   native speaker. Generated pairs therefore ship ``"needs_human": true``
   for Robel to review, prune, and extend.
2. **Curated** (Task 22): ``tests/golden/curated.json``, authored by Robel --
   real-world confusable pairs with his expected outcome. Curated pairs ship
   ``"needs_human": false`` and ``"source": "curated: ..."``: they ARE the
   human baseline, so there is nobody left to route them to. The agent
   authors NO curated pairs, ever -- same firewall as lexicon entries
   (DATA_PROVENANCE.md, AGENT_KICKOFF linguistic-data rules).

**Precedence**: curated pairs are added FIRST, so a curated pair that
collides with a generated one (same unordered {a, b}) WINS -- the human
baseline replaces the mechanical guess, including its ``expected`` value.
Consequence to know: the mechanical near-miss block is a fixed RANK window
(the top ``NEAR_MISS_COUNT`` scoring distinct canonicals), not a fixed
count, so a curated collision inside that window shrinks it by one rather
than pulling the next-ranked pair in. That keeps the generated population a
deterministic function of the lexicon alone.

Expected outcomes follow ARCHITECTURE §6: same-person pairs must score
>= SAME_MIN, different-person pairs <= DIFFERENT_MAX, and (task-3b policy)
``"review"`` pairs -- sibling-style records that an AML analyst should see
-- must land strictly BETWEEN the two thresholds. Pairs whose score at
generation time violates their band are kept and marked
``"known_fail": true`` instead of being dropped -- they are honest records
of current engine limits, and the golden test asserts they KEEP failing so
any improvement forces a conscious corpus regeneration. This applies to
curated pairs unchanged: a curated pair the engine currently fails becomes
a ``known_fail`` RECORD, never a dropped pair.

A missing or malformed ``curated.json`` is a hard, explicit failure (exit
1 with the reason) -- never a silent skip, which would make Robel's
authoring look integrated when it isn't. An empty ``"pairs": []`` is the
documented no-op: the generated corpus, byte-identical.

Usage:
    python scripts/gen_golden_pairs.py          # (re)write the corpus
    python scripts/gen_golden_pairs.py --check  # exit 1 if the file is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from habesha_names._data import lexicon
from habesha_names.match.full import match
from habesha_names.translit.variants import variants

CORPUS_PATH = Path(__file__).resolve().parents[1] / "tests" / "golden" / "pairs.json"

#: Robel's hand-authored confusable pairs (Task 22). Ships empty; the agent
#: never writes a pair into it.
CURATED_PATH = Path(__file__).resolve().parents[1] / "tests" / "golden" / "curated.json"

#: How the curated source is named inside pairs.json (stable, POSIX form).
CURATED_REL = "tests/golden/curated.json"

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

#: Single-token different-person confusables pinned by the plan (§6, Task 6;
#: Bekele/Bikila added by Task 14 -- the HabeshaKey v2 first+last vowel slots
#: separate them, retiring the 0.1.0 known_fail, and this pin keeps it so).
CONFUSABLE_DIFFERENT = (
    ("Alemu", "Almaz"),
    ("Tesfaye", "Tesfahun"),
    ("Tesfaye", "Tesfa"),
    ("Abebe", "Abebech"),
    ("Bekele", "Bikila"),
)

#: Full-name different-person pairs (distinct lexicon names).
FULL_NAME_DIFFERENT = (
    ("Abebe Bikila", "Kebede Alemu", "unrelated names, both tokens differ"),
    ("Tsehay Gebremedhin", "Almaz Tesfahun", "unrelated names, both tokens differ"),
    ("Girma Wolde", "Bekele Haile", "unrelated names, both tokens differ"),
)

#: Sibling-style records: different person, but a shared patronym (and
#: avonym) SHOULD land in the analyst review zone between DIFFERENT_MAX and
#: SAME_MIN -- decided task-3b (E1): this is intended AML behavior, not an
#: engine limit, so these are "review" expectations rather than known_fail
#: different-pairs.
FULL_NAME_REVIEW = (
    ("Tesfaye Girma", "Tesfahun Girma", "sibling-style: different given, shared patronym"),
    ("Abebe Bikila Wolde", "Abebech Bikila Wolde", "sibling-style: shared patronym and avonym"),
)

#: How many mechanically-found near-miss different pairs to keep.
NEAR_MISS_COUNT = 25

#: The three outcomes a pair may expect (ARCHITECTURE §6 + task-3b "review").
EXPECTATIONS = ("same", "different", "review")

#: Keys a curated pair may carry. Anything else is an authoring mistake and
#: is reported rather than ignored.
_CURATED_REQUIRED = ("a", "b", "expected")
_CURATED_OPTIONAL = ("note",)


class CuratedSourceError(Exception):
    """The curated-pairs file is missing or malformed.

    Always fatal: a silent skip would make Robel's authoring look integrated
    when it isn't.
    """


@dataclass(frozen=True)
class CuratedPair:
    """One human-authored pair: Robel's spellings and his expected outcome."""

    a: str
    b: str
    expected: str
    note: str = ""

    @property
    def source(self) -> str:
        """Provenance string written into pairs.json (curated vs generated)."""
        detail = self.note.strip() or "human-authored confusable pair"
        return f"curated: {detail}"


def _curated_error(path: Path, where: str, problem: str) -> CuratedSourceError:
    return CuratedSourceError(f"{path}: {where}: {problem}")


def load_curated(path: Path | None = None) -> list[CuratedPair]:
    """Read Robel's curated pairs; raise ``CuratedSourceError`` on any problem.

    An empty ``pairs`` list is valid and means "generated corpus only" --
    the documented no-op, not an error. ``path`` defaults to
    ``CURATED_PATH``, resolved at call time.
    """
    path = CURATED_PATH if path is None else path
    if not path.is_file():
        raise CuratedSourceError(
            f"{path}: curated-pairs source missing. It is tracked in the repo and "
            'must exist (ship it with "pairs": [] if there is nothing to curate yet).'
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _curated_error(path, "file", f"invalid JSON: {error}") from error
    if not isinstance(raw, dict):
        raise _curated_error(path, "file", "expected a top-level JSON object")
    if raw.get("schema") != 1:
        raise _curated_error(path, "file", 'expected "schema": 1')
    # Underscore keys are documentation for the author and are ignored here.
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in ("schema", "pairs"))
    if unknown:
        raise _curated_error(path, "file", f"unknown top-level key(s): {', '.join(unknown)}")
    items = raw.get("pairs")
    if not isinstance(items, list):
        raise _curated_error(path, "file", 'expected a "pairs" list')

    pairs: list[CuratedPair] = []
    seen: set[frozenset[str]] = set()
    for index, item in enumerate(items):
        where = f"pairs[{index}]"
        if not isinstance(item, dict):
            raise _curated_error(path, where, "expected a JSON object")
        missing = [key for key in _CURATED_REQUIRED if key not in item]
        if missing:
            raise _curated_error(path, where, f"missing key(s): {', '.join(missing)}")
        extra = sorted(set(item) - set(_CURATED_REQUIRED) - set(_CURATED_OPTIONAL))
        if extra:
            raise _curated_error(path, where, f"unknown key(s): {', '.join(extra)}")
        for key in ("a", "b"):
            value = item[key]
            if not isinstance(value, str) or not value.strip():
                raise _curated_error(path, where, f"{key!r} must be a non-empty string")
        note = item.get("note", "")
        if not isinstance(note, str):
            raise _curated_error(path, where, "'note' must be a string")
        if item["expected"] not in EXPECTATIONS:
            raise _curated_error(
                path, where, f"'expected' must be one of {', '.join(EXPECTATIONS)}"
            )
        a, b = item["a"], item["b"]
        if a == b:
            raise _curated_error(path, where, "'a' and 'b' are the same string")
        pair_key = frozenset((a, b))
        if pair_key in seen:
            raise _curated_error(path, where, f"duplicate pair ({a!r}, {b!r})")
        seen.add(pair_key)
        pairs.append(CuratedPair(a=a, b=b, expected=item["expected"], note=note))
    return pairs


def _entry(
    a: str, b: str, expected: str, source: str, *, needs_human: bool = True
) -> dict[str, object]:
    """Build one corpus entry, scoring it and marking threshold violations."""
    score = round(float(match(a, b)), 4)
    entry: dict[str, object] = {
        "a": a,
        "b": b,
        "expected": expected,
        "source": source,
        "needs_human": needs_human,
        "score_at_generation": score,
    }
    if expected == "same":
        passes = score >= SAME_MIN
    elif expected == "different":
        passes = score <= DIFFERENT_MAX
    else:  # "review": the analyst zone strictly between the two gates
        passes = DIFFERENT_MAX < score < SAME_MIN
    if not passes:
        entry["known_fail"] = True
    return entry


@lru_cache(maxsize=1)
def _near_miss_ranked() -> tuple[tuple[str, str], ...]:
    """The top-``NEAR_MISS_COUNT`` scoring pairs of DISTINCT lexicon canonicals.

    Distinct entries are different names by construction (the loader rejects
    any spelling shared between two entries). A fixed RANK window, computed
    from the lexicon alone -- curated collisions inside it do not pull the
    next-ranked pair in.
    """
    canonicals = [entry.canonical for entry in lexicon().given_names]
    scored = sorted(
        (
            (round(float(match(a, b)), 4), a, b)
            for i, a in enumerate(canonicals)
            for b in canonicals[i + 1 :]
        ),
        key=lambda item: (-item[0], item[1], item[2]),
    )
    return tuple((a, b) for _score, a, b in scored[:NEAR_MISS_COUNT])


@dataclass(frozen=True)
class Corpus:
    """The rendered pair population plus the curated-source audit counts."""

    pairs: list[dict[str, object]]
    curated: int
    superseded: int


def build_corpus(curated: Sequence[CuratedPair] | None = None) -> Corpus:
    """Merge curated (human) and generated (mechanical) pairs, deterministically.

    Curated pairs go in FIRST, so a curated pair beats a colliding generated
    one; ``superseded`` counts those wins for the audit line in pairs.json.
    ``curated=None`` reads the shipped source (and fails loudly if it is
    missing or malformed).
    """
    if curated is None:
        curated = load_curated()

    entries: list[dict[str, object]] = []
    seen: set[frozenset[str]] = set()
    curated_keys: set[frozenset[str]] = set()
    displaced: set[frozenset[str]] = set()

    def add(a: str, b: str, expected: str, source: str, *, needs_human: bool = True) -> None:
        key = frozenset((a, b))
        if a == b:
            return
        if key in seen:
            # Generated pairs also dedup against each other; only a collision
            # with a CURATED key is a human baseline superseding a guess.
            if needs_human and key in curated_keys:
                displaced.add(key)
            return
        seen.add(key)
        if not needs_human:
            curated_keys.add(key)
        entries.append(_entry(a, b, expected, source, needs_human=needs_human))

    for pair in curated:
        # Curated pairs drop needs_human: they ARE the human baseline.
        add(pair.a, pair.b, pair.expected, pair.source, needs_human=False)

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
    for a, b, why in FULL_NAME_REVIEW:
        add(a, b, "review", f"expected review-zone pair: {why}")

    for a, b in _near_miss_ranked():
        add(a, b, "different", "mechanical near-miss: highest-scoring distinct canonicals")
    return Corpus(pairs=entries, curated=len(curated), superseded=len(displaced))


def build_pairs(curated: Sequence[CuratedPair] | None = None) -> list[dict[str, object]]:
    """Derive the full corpus, deduplicated, in deterministic order."""
    return build_corpus(curated).pairs


def render(curated: Sequence[CuratedPair] | None = None) -> str:
    """The exact text of pairs.json for the given (or shipped) curated source."""
    return render_corpus(curated)[0]


def render_corpus(curated: Sequence[CuratedPair] | None = None) -> tuple[str, Corpus]:
    """``render()`` plus the corpus it was rendered from (for the CLI summary)."""
    corpus = build_corpus(curated)
    payload: dict[str, Any] = {
        "schema": 1,
        "note": (
            "GENERATED by scripts/gen_golden_pairs.py -- do not hand-edit; "
            "regenerate instead. Pairs whose source is NOT 'curated:' are "
            "agent-derived from the seed lexicon (native-speaker reviewed in "
            "task-3b) and flagged needs_human for Robel. Pairs whose source "
            "starts 'curated:' come from tests/golden/curated.json, authored "
            "by Robel: they are the human baseline, carry needs_human false, "
            "and supersede any generated pair with the same two spellings. "
            "expected 'review' pairs must score strictly between the two "
            "thresholds (analyst review zone). known_fail marks current "
            "engine limits -- curated pairs included: the golden test asserts "
            "these keep failing until the engine or the data changes."
        ),
        "curated_source": {
            "path": CURATED_REL,
            "pairs": corpus.curated,
            "superseded_generated": corpus.superseded,
        },
        "thresholds": {"same_min": SAME_MIN, "different_max": DIFFERENT_MAX},
        "pairs": corpus.pairs,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n", corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed corpus matches regeneration; exit 1 if stale",
    )
    args = parser.parse_args(argv)
    try:
        rendered, corpus = render_corpus()
    except CuratedSourceError as error:
        # Explicit and fatal: never a silent skip of Robel's authoring.
        print(f"CURATED SOURCE ERROR: {error}", file=sys.stderr)
        return 1
    count = len(corpus.pairs)
    summary = (
        f"{count} pairs; curated {corpus.curated} "
        f"(superseding {corpus.superseded} generated), "
        f"generated {count - corpus.curated}"
    )
    if args.check:
        if not CORPUS_PATH.exists():
            print(f"MISSING: {CORPUS_PATH}", file=sys.stderr)
            return 1
        if CORPUS_PATH.read_text(encoding="utf-8") != rendered:
            print(f"STALE: {CORPUS_PATH} does not match regeneration", file=sys.stderr)
            return 1
        print(f"OK: pairs.json is current ({summary})")
        return 0
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(rendered, encoding="utf-8")
    print(f"WROTE: {CORPUS_PATH} ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
