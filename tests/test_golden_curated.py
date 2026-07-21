"""The curated-pairs source (Task 22 part A): loading, validation, precedence.

``tests/golden/curated.json`` is Robel's authoring channel into the golden
corpus. The agent authors NO pair in it -- every pair below is a synthetic
FIXTURE built in-test and written only under ``tmp_path``; nothing here
reaches the shipped file, which this module also pins as empty.

What is gated here:

* the shipped source is a valid, EMPTY no-op (the generated corpus is
  unchanged by it);
* a curated pair enters the corpus with ``needs_human: false`` and a
  ``"curated: "`` source, so provenance stays auditable in pairs.json;
* a curated pair that collides with a generated one WINS, expectation
  included, and is counted as superseding it;
* a curated pair the engine currently fails becomes a ``known_fail``
  RECORD, never a dropped pair (Task 18 discipline, unchanged);
* a missing or malformed source is a clean, explicit failure -- never a
  silent skip that would make the authoring look integrated when it isn't.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "gen_golden_pairs.py"

_spec = importlib.util.spec_from_file_location("gen_golden_pairs", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gen = importlib.util.module_from_spec(_spec)
# Register before exec: @dataclass resolves annotations via sys.modules.
sys.modules[_spec.name] = gen
_spec.loader.exec_module(gen)

#: A pair the generator produces on its own (plan-pinned confusable), used to
#: exercise collision precedence. The expectations the fixtures give it are
#: arbitrary TEST values chosen to differ from the generated one -- they are
#: not a linguistic claim, and they never leave this file.
COLLIDING = ("Alemu", "Almaz")


def _write_curated(path: Path, pairs: list[dict[str, Any]], **extra: Any) -> Path:
    doc: dict[str, Any] = {"schema": 1, "pairs": pairs}
    doc.update(extra)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _key(entry: dict[str, object]) -> frozenset[str]:
    return frozenset((str(entry["a"]), str(entry["b"])))


# --- the shipped source -------------------------------------------------------


def test_shipped_source_is_valid_and_empty() -> None:
    # The agent never authors curated pairs; Robel fills this file.
    assert gen.CURATED_PATH.is_file()
    assert gen.load_curated() == []


def test_empty_source_is_a_documented_no_op() -> None:
    shipped = json.loads((_ROOT / "tests" / "golden" / "pairs.json").read_text(encoding="utf-8"))
    corpus = gen.build_corpus([])
    assert corpus.curated == 0
    assert corpus.superseded == 0
    assert corpus.pairs == shipped["pairs"]


# --- curated pairs in the corpus ----------------------------------------------


def test_curated_pair_is_the_human_baseline() -> None:
    pair = gen.CuratedPair(a="Fixture Alpha", b="Fixture Beta", expected="different", note="fixture")
    corpus = gen.build_corpus([pair])
    baseline = gen.build_corpus([])
    assert corpus.curated == 1
    assert corpus.superseded == 0
    assert len(corpus.pairs) == len(baseline.pairs) + 1

    entry = corpus.pairs[0]  # curated pairs are added first
    assert (entry["a"], entry["b"]) == ("Fixture Alpha", "Fixture Beta")
    assert entry["expected"] == "different"
    assert entry["needs_human"] is False
    assert entry["source"] == "curated: fixture"
    assert isinstance(entry["score_at_generation"], float)


def test_curated_pair_without_a_note_still_names_its_source() -> None:
    corpus = gen.build_corpus([gen.CuratedPair(a="Fixture Alpha", b="Fixture Beta", expected="same")])
    assert corpus.pairs[0]["source"] == "curated: human-authored confusable pair"


def test_curated_pair_supersedes_a_colliding_generated_pair() -> None:
    a, b = COLLIDING
    baseline = gen.build_corpus([])
    generated = [entry for entry in baseline.pairs if _key(entry) == frozenset((a, b))]
    assert len(generated) == 1, "fixture assumption: this pair is generated"
    assert generated[0]["expected"] == "different"
    assert generated[0]["needs_human"] is True

    corpus = gen.build_corpus([gen.CuratedPair(a=a, b=b, expected="review", note="fixture ruling")])
    winners = [entry for entry in corpus.pairs if _key(entry) == frozenset((a, b))]
    assert len(winners) == 1, "the collision must not duplicate the pair"
    assert winners[0]["expected"] == "review"  # the human expectation wins
    assert winners[0]["needs_human"] is False
    assert winners[0]["source"] == "curated: fixture ruling"
    # The generated pair is replaced, not added to: population size holds.
    assert len(corpus.pairs) == len(baseline.pairs)
    assert corpus.superseded == 1


def test_failing_curated_expectation_is_recorded_not_dropped() -> None:
    # Alemu/Almaz is a plan-pinned DIFFERENT pair; asserting "same" is a
    # fixture expectation the engine cannot meet.
    a, b = COLLIDING
    corpus = gen.build_corpus([gen.CuratedPair(a=a, b=b, expected="same", note="fixture")])
    entry = corpus.pairs[0]
    assert entry["known_fail"] is True
    assert float(entry["score_at_generation"]) < gen.SAME_MIN
    assert sum(1 for e in corpus.pairs if _key(e) == frozenset((a, b))) == 1


def test_curated_pairs_are_rendered_into_the_payload() -> None:
    pair = gen.CuratedPair(a="Fixture Alpha", b="Fixture Beta", expected="different")
    text, corpus = gen.render_corpus([pair])
    payload = json.loads(text)
    assert payload["curated_source"] == {
        "path": "tests/golden/curated.json",
        "pairs": 1,
        "superseded_generated": 0,
    }
    assert payload["pairs"][0]["needs_human"] is False
    assert len(payload["pairs"]) == len(corpus.pairs)


# --- failure paths ------------------------------------------------------------


def test_missing_source_is_an_explicit_failure(tmp_path: Path) -> None:
    missing = tmp_path / "curated.json"
    with pytest.raises(gen.CuratedSourceError) as excinfo:
        gen.load_curated(missing)
    assert str(missing) in str(excinfo.value)


MALFORMED: list[tuple[str, str]] = [
    ("not json at all", "invalid JSON"),
    ('["a", "b"]', "top-level JSON object"),
    ('{"pairs": []}', 'expected "schema": 1'),
    ('{"schema": 2, "pairs": []}', 'expected "schema": 1'),
    ('{"schema": 1}', 'expected a "pairs" list'),
    ('{"schema": 1, "pairs": {}}', 'expected a "pairs" list'),
    ('{"schema": 1, "pairs": [], "notes": 1}', "unknown top-level key(s): notes"),
    ('{"schema": 1, "pairs": ["x"]}', "expected a JSON object"),
    ('{"schema": 1, "pairs": [{"a": "X"}]}', "missing key(s): b, expected"),
    (
        '{"schema": 1, "pairs": [{"a": "X", "b": "Y", "expected": "same", "why": 1}]}',
        "unknown key(s): why",
    ),
    ('{"schema": 1, "pairs": [{"a": "", "b": "Y", "expected": "same"}]}', "'a' must be a non-empty"),
    ('{"schema": 1, "pairs": [{"a": "X", "b": 7, "expected": "same"}]}', "'b' must be a non-empty"),
    (
        '{"schema": 1, "pairs": [{"a": "X", "b": "Y", "expected": "maybe"}]}',
        "'expected' must be one of",
    ),
    (
        '{"schema": 1, "pairs": [{"a": "X", "b": "Y", "expected": "same", "note": 3}]}',
        "'note' must be a string",
    ),
    ('{"schema": 1, "pairs": [{"a": "X", "b": "X", "expected": "same"}]}', "the same string"),
    (
        '{"schema": 1, "pairs": [{"a": "X", "b": "Y", "expected": "same"},'
        ' {"a": "Y", "b": "X", "expected": "different"}]}',
        "duplicate pair",
    ),
]


@pytest.mark.parametrize(("text", "expected_message"), MALFORMED, ids=range(len(MALFORMED)))
def test_malformed_source_is_an_explicit_failure(
    tmp_path: Path, text: str, expected_message: str
) -> None:
    path = tmp_path / "curated.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(gen.CuratedSourceError) as excinfo:
        gen.load_curated(path)
    message = str(excinfo.value)
    assert str(path) in message
    assert expected_message in message


def test_underscore_documentation_keys_are_allowed(tmp_path: Path) -> None:
    path = _write_curated(tmp_path / "curated.json", [], _purpose=["docs for the author"])
    assert gen.load_curated(path) == []


def test_cli_fails_loudly_on_a_broken_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "curated.json"
    broken.write_text("{oops", encoding="utf-8")
    monkeypatch.setattr(gen, "CURATED_PATH", broken)
    corpus_before = gen.CORPUS_PATH.read_bytes()

    assert gen.main(["--check"]) == 1
    captured = capsys.readouterr()
    assert "CURATED SOURCE ERROR" in captured.err
    assert str(broken) in captured.err
    # A broken source must not touch the committed corpus.
    assert gen.CORPUS_PATH.read_bytes() == corpus_before
