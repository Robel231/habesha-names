"""Tests for match.token -- in-repo Jaro-Winkler and token similarity (Task 6).

Jaro-Winkler is pinned against the standard published test vectors
(MARTHA/MARHTA, DIXON/DICKSONX, DWAYNE/DUANE), each with its expected value
re-derived from the definition in a comment -- these are algorithm vectors,
not linguistic data. Property tests sample name strings deterministically
from the packaged lexicon (Task 4 seeds) and the plan's Task 6 pin names.
"""

from __future__ import annotations

import pytest

from habesha_names._data import lexicon
from habesha_names.match.phonetic import phonetic_key
from habesha_names.match.token import PHONETIC_WEIGHT, jaro_winkler, sim

# Deterministic sample: first 12 lexicon canonicals (file order is canonical).
SAMPLE_NAMES = [entry.canonical for entry in lexicon().given_names[:12]]

EQUAL_GROUPS = [
    ("Tsehay", "Sehay", "Tsehai"),
    ("Tesfaye", "Tesfay", "Tesfai"),
    ("Mohammed", "Mohamed", "Muhammed"),
    ("Kebede", "Kebbede"),
]


# --- Jaro-Winkler ---------------------------------------------------------


def test_jw_known_value_martha() -> None:
    # len 6/6, window 2, all 6 chars match, TH/HT out of order -> t=1:
    # jaro = (6/6 + 6/6 + 5/6)/3 = 17/18; prefix "MAR" = 3:
    # jw = 17/18 + 3*0.1*(1 - 17/18) = 17.3/18 = 0.96111...
    assert jaro_winkler("MARTHA", "MARHTA") == pytest.approx(17.3 / 18)


def test_jw_known_value_dixon() -> None:
    # len 5/8, window 3, matches d,i,o,n (x at b[7] is out of window), t=0:
    # jaro = (4/5 + 4/8 + 4/4)/3 = 23/30; prefix "DI" = 2:
    # jw = 23/30 + 2*0.1*(7/30) = 24.4/30 = 0.81333...
    assert jaro_winkler("DIXON", "DICKSONX") == pytest.approx(24.4 / 30)


def test_jw_known_value_dwayne() -> None:
    # len 6/5, window 2, matches d,a,n,e, t=0:
    # jaro = (4/6 + 4/5 + 4/4)/3 = 37/45; prefix "D" = 1:
    # jw = 37/45 + 1*0.1*(8/45) = 37.8/45 = 0.84
    assert jaro_winkler("DWAYNE", "DUANE") == pytest.approx(37.8 / 45)


def test_jw_no_prefix_boost_at_or_below_threshold() -> None:
    # jaro("ab","ax") = (1/2 + 1/2 + 1)/3 = 2/3 <= 0.7 -> boost NOT applied
    # despite the shared "a" prefix.
    assert jaro_winkler("ab", "ax") == pytest.approx(2 / 3)


def test_jw_prefix_capped_at_four() -> None:
    # Common prefix "abcde" is length 5; the boost uses at most 4.
    # jaro = (5/8 + 5/8 + 5/5)/3 = 0.75; jw = 0.75 + 4*0.1*0.25 = 0.85.
    assert jaro_winkler("abcdefgh", "abcdexyz") == pytest.approx(0.85)


def test_jw_identity_and_empty() -> None:
    for name in SAMPLE_NAMES:
        assert jaro_winkler(name, name) == 1.0
    assert jaro_winkler("", "") == 1.0
    assert jaro_winkler("Abebe", "") == 0.0
    assert jaro_winkler("", "Abebe") == 0.0


def test_jw_no_common_characters_is_zero() -> None:
    assert jaro_winkler("abc", "xyz") == 0.0


def test_jw_symmetric_and_bounded() -> None:
    for a in SAMPLE_NAMES:
        for b in SAMPLE_NAMES:
            forward = jaro_winkler(a, b)
            assert forward == jaro_winkler(b, a)
            assert 0.0 <= forward <= 1.0


# --- sim -------------------------------------------------------------------


def test_sim_identical_tokens() -> None:
    for name in SAMPLE_NAMES:
        assert sim(name, name) == 1.0


def test_sim_fidel_equals_its_romanization() -> None:
    # Plan-given pair: both normalize to the same Latin token.
    assert sim("ፀሐይ", "Tsehay") == 1.0
    assert sim("ጸሀይ", "Tsehay") == 1.0


def test_sim_case_and_punctuation_insensitive() -> None:
    assert sim("TESFAYE", "tesfaye.") == 1.0


@pytest.mark.parametrize("group", EQUAL_GROUPS, ids=lambda group: group[0])
def test_sim_phonetic_equal_groups_score_at_least_weight(group: tuple[str, ...]) -> None:
    for a in group:
        for b in group:
            assert sim(a, b) >= PHONETIC_WEIGHT


def test_sim_phonetic_backstop_beats_jw() -> None:
    # ARCHITECTURE §4.5 variant pair: JW alone scores ~0.82 (no shared
    # prefix), but the shared HabeshaKey lifts sim to PHONETIC_WEIGHT.
    assert jaro_winkler("tzehay", "sehay") < PHONETIC_WEIGHT
    assert phonetic_key("Tzehay") == phonetic_key("Sehay")
    assert sim("Tzehay", "Sehay") == pytest.approx(PHONETIC_WEIGHT)


def test_sim_alemu_almaz_stays_below_phonetic_weight() -> None:
    # Task 6 inequality pin pair: different people must not reach the
    # phonetic-match score via JW either.
    assert sim("Alemu", "Almaz") < PHONETIC_WEIGHT


def test_sim_empty_or_letterless_side_is_zero() -> None:
    assert sim("", "Abebe") == 0.0
    assert sim("Abebe", "") == 0.0
    assert sim("123", "Abebe") == 0.0
    assert sim("", "") == 0.0


def test_sim_symmetric_and_bounded() -> None:
    tokens = SAMPLE_NAMES + ["ፀሐይ", "ጸሀይ"]
    for a in tokens:
        for b in tokens:
            forward = sim(a, b)
            assert forward == sim(b, a)
            assert 0.0 <= forward <= 1.0


def test_sim_deterministic() -> None:
    assert sim("Tsehay", "Sehay") == sim("Tsehay", "Sehay")


def test_docstring_examples() -> None:
    import doctest

    import habesha_names.match.token as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
