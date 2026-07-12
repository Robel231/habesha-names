"""Tests for match.phonetic -- the HabeshaKey phonetic algorithm (Task 6).

Equality/inequality pins come verbatim from IMPLEMENTATION_PLAN Task 6;
other name strings come from the plan round-trips (ፀሐይ/ጸሀይ, Haile Mariam /
Hailemariam) or ARCHITECTURE §4.2's variant pairs (Bethlehem/Betelhem).
Digraph-mechanics tests use non-name ASCII vectors -- algorithm behavior
pins, not linguistic claims.
"""

from __future__ import annotations

import re

import pytest

from habesha_names.match.phonetic import phonetic_key

# IMPLEMENTATION_PLAN Task 6: keys within a group MUST be equal.
EQUAL_GROUPS = [
    ("Tsehay", "Sehay", "Tsehai"),
    ("Tesfaye", "Tesfay", "Tesfai"),
    ("Mohammed", "Mohamed", "Muhammed"),
    ("Kebede", "Kebbede"),
]

# IMPLEMENTATION_PLAN Task 6: keys MUST differ (similar but different names).
UNEQUAL_PAIRS = [
    ("Alemu", "Almaz"),
    ("Tesfaye", "Tesfahun"),
    ("Abebe", "Abebech"),
]

ALL_PIN_NAMES = sorted({name for group in EQUAL_GROUPS for name in group}
                       | {name for pair in UNEQUAL_PAIRS for name in pair})


@pytest.mark.parametrize("group", EQUAL_GROUPS, ids=lambda group: group[0])
def test_plan_equality_pins(group: tuple[str, ...]) -> None:
    keys = {phonetic_key(name) for name in group}
    assert len(keys) == 1, f"{group} produced distinct keys {keys}"
    assert "" not in keys


@pytest.mark.parametrize(("a", "b"), UNEQUAL_PAIRS)
def test_plan_inequality_pins(a: str, b: str) -> None:
    assert phonetic_key(a) != phonetic_key(b)


def test_fidel_input_keys_like_its_romanization() -> None:
    # Plan-given glyphs: homophone spellings ፀሐይ and ጸሀይ both key as Tsehay.
    assert phonetic_key("ፀሐይ") == phonetic_key("ጸሀይ") == phonetic_key("Tsehay")


def test_case_insensitive() -> None:
    for name in ALL_PIN_NAMES:
        assert phonetic_key(name.upper()) == phonetic_key(name.lower()) == phonetic_key(name)


def test_punctuation_and_whitespace_ignored() -> None:
    assert phonetic_key(" Tesfaye. ") == phonetic_key("Tesfaye")
    assert phonetic_key("Gebre-Medhin") == phonetic_key("GebreMedhin")


def test_multi_token_input_keys_like_joined_form() -> None:
    # Spaces carry no signal: the spaced compound keys like the joined one.
    assert phonetic_key("Haile Mariam") == phonetic_key("Hailemariam")


def test_architecture_variant_pair_bethlehem() -> None:
    # ARCHITECTURE §4.2 lists Bethlehem/Betelhem as a variant pair (th -> t).
    assert phonetic_key("Bethlehem") == phonetic_key("Betelhem")


def test_digraph_fold_mechanics() -> None:
    # Non-name ASCII vectors pinning each fold from the §4.4 sketch.
    assert phonetic_key("akh") == phonetic_key("ah")
    assert phonetic_key("agh") == phonetic_key("ah")
    assert phonetic_key("aph") == phonetic_key("af")
    assert phonetic_key("ath") == phonetic_key("at")
    assert phonetic_key("atsa") == phonetic_key("asa") == phonetic_key("atza")
    # sh and ch stay distinct from plain s/c-less forms.
    assert phonetic_key("asha") != phonetic_key("asa")
    assert phonetic_key("acha") != phonetic_key("aha")


def test_letterless_input_yields_empty_key() -> None:
    assert phonetic_key("") == ""
    assert phonetic_key("   ") == ""
    assert phonetic_key("123 !? ።") == ""


def test_key_format_is_stable_ascii() -> None:
    # Skeleton (may include the terminal "A" marker), colon, optional vowel class.
    pattern = re.compile(r"^[A-Z]*:[aeo]?$")
    for name in ALL_PIN_NAMES:
        assert pattern.fullmatch(phonetic_key(name)), phonetic_key(name)


def test_deterministic() -> None:
    for name in ALL_PIN_NAMES:
        assert phonetic_key(name) == phonetic_key(name)


def test_docstring_examples() -> None:
    import doctest

    import habesha_names.match.phonetic as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
