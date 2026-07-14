"""Tests for practical fidel -> Latin transliteration (Task 3).

The Latin expectations for full names come from IMPLEMENTATION_PLAN Task 3
(round-trip sanity seeds) and the task-3b native-speaker review decisions
(cluster epenthesis, "ua" labialized rendering, the Silase/Selassie split).
Every pinned output below is a reviewed decision; changing one is a new
linguistic decision, not a refactor.
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


def test_haile_selassie_table_output_pin() -> None:
    # Decided in task-3b: the table keeps "Silase" (conventional "Selassie"
    # needs unmarked gemination + a per-name "ie", not derivable from a
    # general table). The ሥላሴ lexicon entry carries "Selassie"/"Silase" as
    # variants and the round-trip is asserted at MATCHER level instead:
    # tests/test_match_full.py pins match("ኃይለ ሥላሴ", "Haile Selassie") >= 0.85.
    assert transliterate("ኃይለ") == "Haile"
    assert transliterate("ኃይለ ሥላሴ") == "Haile Silase"


def test_sixth_order_final_cluster_epenthesis() -> None:
    # task-3b cluster rule: in a word-final cluster of 6th-order consonants
    # the epenthetic "i" goes right before the coda; "st" is a permissible
    # final cluster and stays together. All four outputs pinned by Robel.
    assert transliterate("ፍቅር") == "Fikir"
    assert transliterate("ትግስት") == "Tigist"
    assert transliterate("ቅድስት") == "Kidist"
    assert transliterate("ዮሐንስ") == "Yohanis"


def test_labialized_ua_rendering() -> None:
    # task-3b: labialized forms render "ua", not "wa" (ኋላ -> Huala pinned;
    # order-8 column is consonant + "ua"). Plain ዋ stays "wa".
    assert transliterate("ኋላ") == "Huala"
    assert transliterate("ኳ") == "Kua"
    assert transliterate("ጓ") == "Gua"
    assert transliterate("ሏ") == "Lua"
    assert transliterate("ሟ") == "Mua"
    assert transliterate("ዋና") == "Wana"


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
    # Plan-given string (Task 5 list). ወ order 1 -> "we" was CONFIRMED in
    # task-3b ("Weizero" is now also the canonical title spelling; we<->wo
    # is a variant rule). Wordspace ፡ separates, ። is stripped, by normalize().
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
