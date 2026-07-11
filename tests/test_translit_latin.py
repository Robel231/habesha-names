"""Tests for practical fidel -> Latin transliteration (Task 3).

The Latin expectations for full names come from IMPLEMENTATION_PLAN Task 3
(round-trip sanity seeds). Everything else is either a full-table property
test or a behavior pin over an UNVERIFIED agent default (all defaults are in
the PROGRESS.md human review queue; pins exist so a later table change is a
conscious one, not to claim linguistic correctness).
"""

import unicodedata

import pytest

from habesha_names.fidel.normalize import HOMOPHONE_SERIES, normalize
from habesha_names.fidel.tables import CODEPOINT_BY_SYLLABLE, SYLLABLES
from habesha_names.translit.schemes import PRACTICAL, SCHEMES
from habesha_names.translit.to_latin import transliterate

# Plan-given round-trip seeds (IMPLEMENTATION_PLAN Task 3).
PLAN_ROUNDTRIPS = [
    ("ተስፋዬ", "Tesfaye"),
    ("ገብረመድህን", "Gebremedhin"),
    ("ጸሐይ", "Tsehay"),
]


def test_pinned_invariant_homophones_transliterate_identically() -> None:
    """HARD REQUIREMENT: ፀሐይ and ጸሀይ are homophone spellings of one name."""
    assert [unicodedata.name(c) for c in "ፀሐይ"] == [
        "ETHIOPIC SYLLABLE TZA",
        "ETHIOPIC SYLLABLE HHA",
        "ETHIOPIC SYLLABLE YE",
    ]
    assert [unicodedata.name(c) for c in "ጸሀይ"] == [
        "ETHIOPIC SYLLABLE TSA",
        "ETHIOPIC SYLLABLE HA",
        "ETHIOPIC SYLLABLE YE",
    ]
    assert transliterate("ፀሐይ") == transliterate("ጸሀይ") == "Tsehay"


@pytest.mark.parametrize(("fidel", "latin"), PLAN_ROUNDTRIPS)
def test_plan_roundtrips(fidel: str, latin: str) -> None:
    assert transliterate(fidel) == latin


@pytest.mark.xfail(
    strict=True,
    reason="Conventional 'Selassie' is not derivable from a general table: the "
    "geminated 'ss' is unmarked in fidel and 'ie' for the order-5 vowel is a "
    "per-name convention. Default table yields 'Haile Silase'. Logged in "
    "PROGRESS.md (review queue + session 4 deviations); Robel decides.",
)
def test_plan_roundtrip_haile_selassie() -> None:
    assert transliterate("ኃይለ ሥላሴ") == "Haile Selassie"


def test_haile_selassie_current_behavior_pin() -> None:
    # Behavior pin of the UNVERIFIED default (see xfail above), so any table
    # change is deliberate. The 'Haile' half is the plan-expected form.
    assert transliterate("ኃይለ") == "Haile"
    assert transliterate("ኃይለ ሥላሴ") == "Haile Silase"


def test_transliterate_normalizes_first() -> None:
    # transliterate(x) must equal transliterate(normalize(x)) for any input.
    for text in ["ኃይለ ሥላሴ", "ወይዘሮ፡ጸሐይ ገብረመድህን።", "ፀሐይ", "Tesfayé  G/Medhin ።"]:
        assert transliterate(text) == transliterate(normalize(text))


def test_every_homophone_source_transliterates_like_its_target() -> None:
    """Full-table extension of the pinned invariant: every syllable of a
    collapsed series transliterates exactly like its same-order target."""
    checked = 0
    for cp, (consonant, order) in SYLLABLES.items():
        target = HOMOPHONE_SERIES.get(consonant)
        if target is None:
            continue
        target_cp = CODEPOINT_BY_SYLLABLE[(target, order)]
        assert transliterate(chr(cp)) == transliterate(chr(target_cp)), f"U+{cp:04X}"
        checked += 1
    assert checked > 0


def test_practical_has_no_rows_for_collapsed_series() -> None:
    # HARD REQUIREMENT: normalize() runs first, so ሐ/ኀ/ሠ/ፀ/ዐ series cells
    # must not exist (they could only hide dead, unreviewable data).
    assert not [key for key in PRACTICAL if key[0] in HOMOPHONE_SERIES]


def test_practical_covers_every_post_collapse_syllable() -> None:
    expected = {
        (consonant, order)
        for consonant, order in SYLLABLES.values()
        if consonant not in HOMOPHONE_SERIES
    }
    assert set(PRACTICAL) == expected


def test_practical_values_are_plain_ascii_lowercase() -> None:
    # Practical scheme contract: no diacritics, no apostrophes, no uppercase.
    for key, value in PRACTICAL.items():
        assert all("a" <= ch <= "z" for ch in value), (key, value)


def test_sixth_order_word_initial_gets_epenthetic_vowel() -> None:
    # ስላሴ is the normalized second token of the plan-given ኃይለ ሥላሴ. Word-
    # initial 6th order gets "i"; medial-after-vowel stays bare (Tesfaye, not
    # Tesifaye — covered by the round-trip tests). UNVERIFIED default.
    assert transliterate("ስላሴ") == "Silase"


def test_latin_and_mixed_input_passes_through() -> None:
    assert transliterate("Tesfaye Gebremedhin") == "Tesfaye Gebremedhin"
    assert transliterate("ተስፋዬ (Tesfaye)") == "Tesfaye (Tesfaye)"
    # Latin words are NOT re-cased; only fidel-initial words are capitalized.
    assert transliterate("ተስፋዬ tesfaye") == "Tesfaye tesfaye"


def test_plan_full_string_with_title_and_punctuation() -> None:
    # Plan-given string (Task 5 list). "Weizero" is an UNVERIFIED default
    # (w-series order 1 -> "we"; "Woizero" is the conventional title form —
    # review queue). Wordspace ፡ separates, ። is stripped, all by normalize().
    assert transliterate("ወይዘሮ፡ጸሐይ ገብረመድህን።") == "Weizero Tsehay Gebremedhin"


def test_non_syllable_ethiopic_passes_through() -> None:
    # Ethiopic digit ፩ (U+1369), tonal mark (U+1390), combining mark
    # (U+135F), Extended block (U+2D80): no table entry, pass through.
    for cp in (0x1369, 0x1390, 0x135F, 0x2D80):
        assert transliterate("ሀ" + chr(cp)) == "Ha" + chr(cp), f"U+{cp:04X}"


def test_unknown_scheme_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown scheme"):
        transliterate("ተስፋዬ", scheme="bgn_pcgn")  # v0.2, not registered yet
    assert "practical" in SCHEMES


def test_explicit_practical_scheme() -> None:
    assert transliterate("ተስፋዬ", scheme="practical") == "Tesfaye"


def test_empty_and_whitespace_input() -> None:
    assert transliterate("") == ""
    assert transliterate(" \t\n ") == ""
    assert transliterate("።") == ""


def test_output_is_stable_under_retransliteration() -> None:
    # Latin output passes back through unchanged (normalize + passthrough).
    for fidel, _ in PLAN_ROUNDTRIPS:
        once = transliterate(fidel)
        assert transliterate(once) == once


def test_deterministic() -> None:
    for fidel, _ in PLAN_ROUNDTRIPS:
        assert transliterate(fidel) == transliterate(fidel)


def test_docstring_examples() -> None:
    import doctest

    import habesha_names.translit.to_latin as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
