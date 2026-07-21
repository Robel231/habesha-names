"""Golden-corpus gate (Task 8): ARCHITECTURE §6 thresholds over pairs.json.

The corpus is written by scripts/gen_golden_pairs.py from two sources:
mechanically-derived pairs (from the seed lexicon -- flagged ``needs_human``
for Robel) and, since Task 22, Robel's hand-authored pairs in
tests/golden/curated.json (``source`` starts ``"curated: "``, and they carry
``needs_human: false`` because they ARE the human baseline). Pairs marked
``known_fail`` are honest records of current engine limits: a separate test
asserts they KEEP failing, so an engine improvement forces a conscious
corpus regeneration instead of silently changing the gate.

The curated-source MECHANISM (loading, validation, precedence) is tested in
tests/test_golden_curated.py; this file gates the corpus as shipped.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from habesha_names.match.full import match

_ROOT = Path(__file__).resolve().parents[1]
_CORPUS = Path(__file__).parent / "golden" / "pairs.json"
_DATA = json.loads(_CORPUS.read_text(encoding="utf-8"))
_PAIRS: list[dict[str, object]] = _DATA["pairs"]

SAME_MIN: float = _DATA["thresholds"]["same_min"]
DIFFERENT_MAX: float = _DATA["thresholds"]["different_max"]

_ACTIVE = [entry for entry in _PAIRS if not entry.get("known_fail")]
_KNOWN_FAIL = [entry for entry in _PAIRS if entry.get("known_fail")]


def _meets_expectation(entry: dict[str, object]) -> tuple[bool, float]:
    score = float(match(str(entry["a"]), str(entry["b"])))
    if entry["expected"] == "same":
        return score >= SAME_MIN, score
    if entry["expected"] == "different":
        return score <= DIFFERENT_MAX, score
    # "review" (task-3b): sibling-style pairs belong strictly BETWEEN the
    # gates -- the analyst review zone is intended behavior, not a failure.
    return DIFFERENT_MAX < score < SAME_MIN, score


def _pair_id(entry: dict[str, object]) -> str:
    return f"{entry['expected']}:{entry['a']}|{entry['b']}"


# --- corpus shape -------------------------------------------------------------


def test_corpus_size_meets_plan_minimum() -> None:
    assert len(_PAIRS) >= 150


def test_thresholds_match_architecture() -> None:
    # ARCHITECTURE §6: same-person >= 0.85, different-person <= 0.6.
    assert SAME_MIN == 0.85
    assert DIFFERENT_MAX == 0.60


def _is_curated(entry: dict[str, object]) -> bool:
    return str(entry["source"]).startswith("curated: ")


def test_needs_human_matches_pair_provenance() -> None:
    # Generated pairs are agent-derived and await Robel; curated pairs are
    # his own authorship, so there is nobody left to route them to.
    for entry in _PAIRS:
        assert entry.get("needs_human") is (not _is_curated(entry)), entry


def test_curated_metadata_matches_the_pairs() -> None:
    meta = _DATA["curated_source"]
    assert meta["path"] == "tests/golden/curated.json"
    assert meta["pairs"] == sum(1 for entry in _PAIRS if _is_curated(entry))
    assert meta["superseded_generated"] <= meta["pairs"]


def test_no_duplicate_pairs() -> None:
    keys = [frozenset((str(entry["a"]), str(entry["b"]))) for entry in _PAIRS]
    assert len(keys) == len(set(keys))


def test_schema_of_every_entry() -> None:
    for entry in _PAIRS:
        assert isinstance(entry["a"], str) and entry["a"]
        assert isinstance(entry["b"], str) and entry["b"]
        assert entry["expected"] in ("same", "different", "review")
        assert isinstance(entry["source"], str) and entry["source"]
        assert isinstance(entry["score_at_generation"], float)


def test_corpus_has_all_outcomes_and_scripts() -> None:
    expectations = {entry["expected"] for entry in _PAIRS}
    assert expectations == {"same", "different", "review"}
    assert any(not str(entry["a"]).isascii() for entry in _PAIRS)  # fidel present


def test_corpus_file_is_current() -> None:
    # Regenerating must reproduce the committed file byte-for-byte, so the
    # corpus cannot drift from the generator (or be hand-edited unnoticed).
    result = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "gen_golden_pairs.py"), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- the actual gate ------------------------------------------------------------


@pytest.mark.parametrize("entry", _ACTIVE, ids=_pair_id)
def test_golden_pair(entry: dict[str, object]) -> None:
    ok, score = _meets_expectation(entry)
    bounds = {
        "same": f">= {SAME_MIN}",
        "different": f"<= {DIFFERENT_MAX}",
        "review": f"in ({DIFFERENT_MAX}, {SAME_MIN})",
    }
    bound = bounds[str(entry["expected"])]
    assert ok, f"match({entry['a']!r}, {entry['b']!r}) = {score:.4f}, expected {bound}"


@pytest.mark.parametrize("entry", _KNOWN_FAIL, ids=_pair_id)
def test_known_fail_pair_still_fails(entry: dict[str, object]) -> None:
    # Strict-xfail semantics: if one of these starts passing, regenerate the
    # corpus (which will drop its known_fail marker) rather than letting the
    # gate drift silently.
    ok, score = _meets_expectation(entry)
    assert not ok, (
        f"match({entry['a']!r}, {entry['b']!r}) = {score:.4f} now meets its "
        "threshold -- regenerate tests/golden/pairs.json"
    )
