"""Tests for match.full -- the full-name matcher (Task 8).

Every name string comes from IMPLEMENTATION_PLAN / ARCHITECTURE test cases
(Abebe Bikila Wolde, G/Medhin Tesfaye, Haile Mariam Desalegn, ኃይለ ሥላሴ, the
Task 6 confusable pins) or from the seeded lexicon. Expected scores are
derived from the documented formula (weighted mean over aligned roles,
multiplicative swap/truncation penalties), re-computed in comments.
"""

from __future__ import annotations

import dataclasses

import pytest

from habesha_names._data import lexicon
from habesha_names.match.full import DEFAULT_WEIGHTS, MatchWeights, match

# Deterministic sample of full names built from lexicon canonicals.
_CANONICALS = [entry.canonical for entry in lexicon().given_names[:8]]
SAMPLE_NAMES = [
    f"{given} {_CANONICALS[(i + 3) % len(_CANONICALS)]}" for i, given in enumerate(_CANONICALS)
]


# --- identity, normalization, parsing integration ---------------------------


def test_identical_full_names_score_one() -> None:
    result = match("Abebe Bikila Wolde", "Abebe Bikila Wolde")
    assert result.score == 1.0
    assert not result.swapped
    assert [pair.method for pair in result.pairs] == ["exact", "exact", "exact"]


def test_case_insensitive() -> None:
    assert match("Abebe Bikila", "ABEBE BIKILA").score == 1.0


def test_fidel_matches_its_romanization() -> None:
    # Plan name: ወይዘሮ ጸሐይ ገብረመድህን -- title stripped, fidel tokens
    # transliterate to the exact Latin spellings.
    assert match("ወይዘሮ ጸሐይ ገብረመድህን", "Tsehay Gebremedhin").score == 1.0


def test_title_stripped_before_matching() -> None:
    assert match("Ato Abebe Bikila", "Abebe Bikila").score == 1.0


def test_comma_inversion_is_not_a_swap() -> None:
    # The parser restores "patronym, given" order, so roles align in order.
    result = match("Bikila, Abebe", "Abebe Bikila")
    assert result.score == 1.0
    assert not result.swapped


def test_abbreviation_expanded_before_matching() -> None:
    # ARCHITECTURE §4.4 step 1; this is what lets G/Medhin score exactly.
    result = match("G/Medhin Tesfaye", "Gebremedhin Tesfaye")
    assert result.score == 1.0
    assert any("abbreviation" in note for note in result.notes)


def test_spaced_and_joined_compound_align() -> None:
    # Plan case: both parses join to given "Hailemariam".
    assert match("Hailemariam Desalegn", "Haile Mariam Desalegn").score == 1.0


def test_selassie_matcher_level_roundtrip() -> None:
    # task-3b decision: the table keeps "Silase" (the old Task 3 xfail was
    # retired) and the plan round-trip is asserted HERE instead. The
    # HabeshaKey folds Silase/Selassie together, and the ሥላሴ compound
    # entry carries Selassie/Silase as lexicon variants.
    assert match("ኃይለ ሥላሴ", "Haile Selassie") >= 0.85


# --- swap and truncation tolerance ------------------------------------------


def test_swap_tolerance() -> None:
    # Both tokens exact but crossed: 1.0 * swap_penalty.
    result = match("Abebe Bikila", "Bikila Abebe")
    assert result.swapped
    assert result.score == pytest.approx(DEFAULT_WEIGHTS.swap_penalty)
    assert any("swap" in note for note in result.notes)


def test_swapped_scores_below_in_order() -> None:
    assert match("Abebe Bikila", "Bikila Abebe").score < match("Abebe Bikila", "Abebe Bikila").score


def test_truncation_tolerance() -> None:
    # Plan case: 3 tokens vs 2, given+patronym exact. Unmatched avonym costs
    # the factor (1 - 0.20 * 0.5) = 0.9, not the role's full weight.
    result = match("Abebe Bikila Wolde", "Abebe Bikila")
    assert result.score == pytest.approx(0.9)
    assert not result.swapped
    assert "avonym missing in b" in result.notes


def test_truncation_note_names_the_shorter_side() -> None:
    assert "avonym missing in a" in match("Abebe Bikila", "Abebe Bikila Wolde").notes


# --- pairs and explanation ---------------------------------------------------


def test_pairs_report_tokens_roles_sims_methods() -> None:
    result = match("Tzehay Gebremedhin", "Sehay Gebremedhin")
    assert len(result.pairs) == 2
    given = result.pairs[0]
    assert (given.token_a, given.token_b) == ("Tzehay", "Sehay")
    assert (given.role_a, given.role_b) == ("given", "given")
    assert given.sim == pytest.approx(0.9)
    assert given.method == "phonetic"
    assert result.pairs[1].method == "exact"


def test_variant_overlap_method() -> None:
    # Bekele/Beqele: HabeshaKeys differ (q/k not folded), JW is damped, the
    # variant-set overlap term wins. Score = (0.45*0.85 + 0.35*1.0) / 0.80.
    result = match("Bekele Girma", "Beqele Girma")
    assert result.pairs[0].method == "variant"
    assert result.pairs[0].sim == pytest.approx(0.85)
    assert result.score == pytest.approx((0.45 * 0.85 + 0.35) / 0.80)


def test_parse_notes_carried_with_side_prefix() -> None:
    result = match("Bikila, Abebe", "G/Medhin Tesfaye")
    assert any(note.startswith("a: comma-inverted") for note in result.notes)
    assert any(note.startswith("b: abbreviation") for note in result.notes)


# --- different-person pairs stay low -----------------------------------------


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Alemu", "Almaz"),
        ("Tesfaye", "Tesfahun"),
        ("Tesfaye", "Tesfa"),
        ("Abebe", "Abebech"),
        # Task 14 (HabeshaKey v2): first+last vowel slots separate the
        # full-skeleton collision that scored 0.90 in 0.1.0.
        ("Bekele", "Bikila"),
    ],
)
def test_plan_confusables_stay_below_different_threshold(a: str, b: str) -> None:
    # ARCHITECTURE §6: different people with similar names -> <= 0.6.
    assert match(a, b) <= 0.6


def test_unrelated_full_names_score_low() -> None:
    assert match("Abebe Bikila", "Almaz Tesfahun") <= 0.6


# --- result ergonomics --------------------------------------------------------


def test_float_and_comparisons() -> None:
    result = match("Abebe Bikila", "Abebe Bikila")
    assert float(result) == 1.0
    assert result > 0.9
    assert result >= 1.0
    assert result <= 1.0
    assert not result < 0.5
    assert 0.9 < result  # reflected comparison works too


def test_result_is_frozen() -> None:
    result = match("Abebe", "Abebe")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.score = 0.0  # type: ignore[misc]


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError):
        match("", "Abebe")
    with pytest.raises(ValueError):
        match("Abebe", "።")


# --- weights config ------------------------------------------------------------


def test_weights_override_changes_score() -> None:
    # Equal role weights make the truncation penalty use 1.0 * 0.5.
    flat = MatchWeights(given=1.0, patronym=1.0, avonym=1.0)
    result = match("Abebe Bikila Wolde", "Abebe Bikila", weights=flat)
    assert result.score == pytest.approx(0.5)


def test_no_swap_penalty_when_disabled() -> None:
    tolerant = MatchWeights(swap_penalty=1.0)
    assert match("Abebe Bikila", "Bikila Abebe", weights=tolerant).score == 1.0


def test_weights_validation() -> None:
    with pytest.raises(ValueError):
        MatchWeights(given=0.0)
    with pytest.raises(ValueError):
        MatchWeights(patronym=-0.1)
    with pytest.raises(ValueError):
        MatchWeights(swap_penalty=1.5)
    with pytest.raises(ValueError):
        MatchWeights(missing_scale=-0.2)


# --- properties -----------------------------------------------------------------


def test_score_symmetric_bounded_deterministic() -> None:
    names = SAMPLE_NAMES + ["Abebe Bikila Wolde", "ጸሐይ ገብረመድህን", "G/Medhin Tesfaye"]
    for a in names:
        for b in names:
            forward = match(a, b).score
            assert forward == match(b, a).score, (a, b)
            assert 0.0 <= forward <= 1.0
            assert forward == match(a, b).score


def test_self_match_is_always_one() -> None:
    for name in SAMPLE_NAMES:
        assert match(name, name).score == 1.0


def test_docstring_examples() -> None:
    import doctest

    # `habesha_names.match` the attribute is the match() function since Task 9;
    # the submodule remains importable via `from ... import`.
    from habesha_names.match import full as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
