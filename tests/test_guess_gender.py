"""Task 20 — ``guess_gender``: lexicon-backed gender inference, given token only.

Name strings are limited to lexicon spellings and forms already named in
the plan / PROGRESS.md (Yohannis: task-16 corpus list; Maram: task-15
review-queue example of an out-of-lexicon name), per the no-invented-names
rule. Synthetic gender distributions for the conflict/tie paths are built
with ``dataclasses.replace`` on real entries — mechanics, not new
linguistic claims.
"""

from __future__ import annotations

import dataclasses
import doctest

import pytest

import habesha_names.gender
from habesha_names import guess_gender, phonetic_key
from habesha_names._data import GivenName, lexicon
from habesha_names.gender import (
    _CONFIDENCE_EXACT,
    _CONFIDENCE_KEY,
    _CONFIDENCE_VARIANT,
    GenderGuess,
    _decide,
)


def _entry(canonical: str) -> GivenName:
    return next(e for e in lexicon().given_names if e.canonical == canonical)


# --- lookup tiers -----------------------------------------------------------


def test_exact_canonical_hit() -> None:
    guess = guess_gender("Ato Abebe Bikila")
    assert (guess.gender, guess.confidence) == ("m", _CONFIDENCE_EXACT)
    assert any("'Abebe'" in note and "exact spelling" in note for note in guess.notes)


def test_exact_hit_scales_by_distribution() -> None:
    guess = guess_gender("Tsehay")
    assert guess.gender == "f"
    assert guess.confidence == pytest.approx(_CONFIDENCE_EXACT * 0.97)


def test_fidel_exact_and_homophone_identity() -> None:
    conventional = guess_gender("ፀሐይ ገብረመድህን")
    collapsed = guess_gender("ጸሀይ ገብረመድህን")
    assert conventional.gender == collapsed.gender == "f"
    assert conventional.confidence == collapsed.confidence
    assert conventional.confidence == guess_gender("Tsehay").confidence


def test_variant_tier() -> None:
    guess = guess_gender("Tesfai")  # recorded variant of Tesfaye
    assert (guess.gender, guess.confidence) == ("m", _CONFIDENCE_VARIANT)
    assert any("'Tesfaye'" in note and "variant" in note for note in guess.notes)
    assert guess_gender("Fatima").gender == "f"  # recorded variant of Fatuma


def test_key_tier() -> None:
    # Yohannis (task-16 corpus list) is no recorded spelling of any entry...
    for entry in lexicon().given_names:
        assert "yohannis" not in {entry.canonical.lower(), *(v.lower() for v in entry.variants)}
    # ...but shares Yohannes's HabeshaKey, so the weakest tier answers.
    assert phonetic_key("Yohannis") == phonetic_key("Yohannes")
    guess = guess_gender("Yohannis")
    assert (guess.gender, guess.confidence) == ("m", _CONFIDENCE_KEY)
    assert any("'Yohannes'" in note and "phonetic key" in note for note in guess.notes)


def test_tier_confidences_descend() -> None:
    assert _CONFIDENCE_EXACT > _CONFIDENCE_VARIANT > _CONFIDENCE_KEY
    exact = guess_gender("Tesfaye").confidence
    variant = guess_gender("Tesfai").confidence
    key = guess_gender("Yohannis").confidence
    assert exact > variant > key > 0.0


# --- given token only -------------------------------------------------------


def test_patronym_is_not_evidence() -> None:
    guess = guess_gender("Abebe Tsehay")  # patronym is a female-majority entry
    assert (guess.gender, guess.confidence) == ("m", _CONFIDENCE_EXACT)
    assert any("patronym 'Tsehay' ignored" in note for note in guess.notes)


def test_avonym_is_not_evidence() -> None:
    guess = guess_gender("Abebe Girma Tsehay")
    assert guess.gender == "m"
    assert any("avonym 'Tsehay' ignored" in note for note in guess.notes)


def test_parsed_given_is_used() -> None:
    # Abbreviation expansion and comma inversion both run before lookup.
    assert guess_gender("G/Medhin Tesfaye").gender == "m"  # given = Gebremedhin
    inverted = guess_gender("Tsehay, Abebe")  # "patronym, given" -> given = Abebe
    assert (inverted.gender, inverted.confidence) == ("m", _CONFIDENCE_EXACT)


# --- honest misses ----------------------------------------------------------


def test_out_of_lexicon_is_unknown() -> None:
    guess = guess_gender("Maram")  # out-of-lexicon (task-15 review-queue example)
    assert (guess.gender, guess.confidence) == ("unknown", 0.0)
    assert any("no lexicon entry matches 'Maram'" in note for note in guess.notes)


def test_letterless_token_is_unknown() -> None:
    guess = guess_gender("...")  # empty phonetic key, no lookup possible
    assert (guess.gender, guess.confidence) == ("unknown", 0.0)


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError):
        guess_gender("")


# --- conflict and tie handling (synthetic distributions) --------------------


def test_balanced_distribution_is_unknown() -> None:
    balanced = dataclasses.replace(_entry("Tsehay"), gender={"f": 0.5, "m": 0.5})
    notes: list[str] = []
    guess = _decide((balanced,), _CONFIDENCE_EXACT, "exact spelling", notes)
    assert (guess.gender, guess.confidence) == ("unknown", 0.0)
    assert any("balanced or conflicting" in note for note in guess.notes)


def test_conflicting_entries_are_unknown() -> None:
    notes: list[str] = []
    guess = _decide((_entry("Abebe"), _entry("Almaz")), _CONFIDENCE_KEY, "phonetic key", notes)
    assert (guess.gender, guess.confidence) == ("unknown", 0.0)
    assert any("balanced or conflicting" in note for note in guess.notes)


def test_agreeing_entries_use_conservative_probability() -> None:
    notes: list[str] = []
    guess = _decide((_entry("Almaz"), _entry("Tsehay")), _CONFIDENCE_KEY, "phonetic key", notes)
    assert guess.gender == "f"
    assert guess.confidence == pytest.approx(_CONFIDENCE_KEY * 0.97)  # min, not max


# --- contract ---------------------------------------------------------------


def test_every_lexicon_canonical_gets_its_majority_gender() -> None:
    for entry in lexicon().given_names:
        guess = guess_gender(entry.canonical)
        f, m = entry.gender.get("f", 0.0), entry.gender.get("m", 0.0)
        expected = "f" if f > m else "m" if m > f else "unknown"
        assert guess.gender == expected, entry.canonical
        if expected != "unknown":
            assert guess.confidence == pytest.approx(_CONFIDENCE_EXACT * max(f, m))
        assert 0.0 <= guess.confidence <= 1.0


def test_result_is_frozen_and_deterministic() -> None:
    guess = guess_gender("Tsehay")
    with pytest.raises(dataclasses.FrozenInstanceError):
        guess.gender = "m"  # type: ignore[misc]
    assert guess == guess_gender("Tsehay")


def test_first_note_names_the_given_token() -> None:
    assert guess_gender("Ato Abebe Bikila").notes[0] == "evidence: given name 'Abebe' only"


def test_module_doctests() -> None:
    results = doctest.testmod(habesha_names.gender)
    assert results.attempted > 0
    assert results.failed == 0


def test_guess_gender_type() -> None:
    guess = guess_gender("Tsehay")
    assert isinstance(guess, GenderGuess)
    assert isinstance(guess.notes, list)
