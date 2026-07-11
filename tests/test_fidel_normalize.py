"""Tests for fidel normalization (Task 2).

Pinned expectations are cross-checked against ``unicodedata.name`` inside the
tests (same discipline as test_fidel_syllable.py) so hand-typed fidel in this
file cannot silently agree with a wrong implementation.
"""

import unicodedata

import pytest

from habesha_names.fidel.normalize import (
    ETHIOPIC_PUNCTUATION,
    ETHIOPIC_WORDSPACE,
    HOMOPHONE_SERIES,
    normalize,
)
from habesha_names.fidel.syllable import decompose
from habesha_names.fidel.tables import CODEPOINT_BY_SYLLABLE, ETHIOPIC_RANGES, SYLLABLES

# The four collapses pinned by IMPLEMENTATION_PLAN Task 2 (ሀ/ሐ/ኀ→ሀ, ሠ→ሰ,
# ፀ→ጸ, ዐ→አ), each tied to the standard via the Unicode name column.
PINNED_COLLAPSES = [
    ("ሀ", "ETHIOPIC SYLLABLE HA", "ሀ", "ETHIOPIC SYLLABLE HA"),
    ("ሐ", "ETHIOPIC SYLLABLE HHA", "ሀ", "ETHIOPIC SYLLABLE HA"),
    ("ኀ", "ETHIOPIC SYLLABLE XA", "ሀ", "ETHIOPIC SYLLABLE HA"),
    ("ሠ", "ETHIOPIC SYLLABLE SZA", "ሰ", "ETHIOPIC SYLLABLE SA"),
    ("ፀ", "ETHIOPIC SYLLABLE TZA", "ጸ", "ETHIOPIC SYLLABLE TSA"),
    ("ዐ", "ETHIOPIC SYLLABLE PHARYNGEAL A", "አ", "ETHIOPIC SYLLABLE GLOTTAL A"),
]


@pytest.mark.parametrize(("src", "src_name", "dst", "dst_name"), PINNED_COLLAPSES)
def test_pinned_homophone_collapses(src: str, src_name: str, dst: str, dst_name: str) -> None:
    assert unicodedata.name(src) == src_name
    assert unicodedata.name(dst) == dst_name
    assert normalize(src) == dst


def test_collapse_preserves_vowel_order_across_whole_table() -> None:
    """Every syllable of a collapsed series maps to the same order in the
    target series; every other syllable is left byte-identical."""
    for cp, (consonant, order) in SYLLABLES.items():
        out = normalize(chr(cp))
        target = HOMOPHONE_SERIES.get(consonant)
        if target is None:
            assert out == chr(cp), f"U+{cp:04X} changed unexpectedly"
        else:
            assert len(out) == 1, f"U+{cp:04X} did not map to one character"
            assert decompose(out) == (target, order), f"U+{cp:04X}"


def test_collapsed_output_contains_no_homophone_sources() -> None:
    everything = "".join(chr(cp) for cp in SYLLABLES)
    for ch in normalize(everything):
        if ch == " ":
            continue
        assert decompose(ch).consonant not in HOMOPHONE_SERIES


def test_punctuation_set_matches_independent_unicodedata_scan() -> None:
    rederived = set()
    for first, last in ETHIOPIC_RANGES:
        for cp in range(first, last + 1):
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                continue
            if unicodedata.category(chr(cp)).startswith("P"):
                rederived.add(chr(cp))
    assert set(ETHIOPIC_PUNCTUATION) == rederived
    assert unicodedata.name(ETHIOPIC_WORDSPACE) == "ETHIOPIC WORDSPACE"
    assert ETHIOPIC_WORDSPACE in ETHIOPIC_PUNCTUATION


def test_punctuation_is_stripped_and_wordspace_becomes_space() -> None:
    # ። full stop and ፣ comma are named in ARCHITECTURE 4.1; ወይዘሮ ጸሐይ is a
    # plan-given string (IMPLEMENTATION_PLAN Task 5).
    assert normalize("ወይዘሮ ጸሐይ።") == "ወይዘሮ ጸሀይ"
    assert normalize("ጸሐይ፣ ወይዘሮ") == "ጸሀይ ወይዘሮ"
    assert normalize("ወይዘሮ፡ጸሐይ") == "ወይዘሮ ጸሀይ"  # wordspace separates, not merges
    for punct in ETHIOPIC_PUNCTUATION:
        expected = "ሀ ለ" if punct == ETHIOPIC_WORDSPACE else "ሀለ"
        assert normalize(f"ሀ{punct}ለ") == expected, f"U+{ord(punct):04X}"


def _collapse_via_tables(text: str) -> str:
    """Re-derive the expected collapse from the tables, independent of
    normalize(): swap the series label through HOMOPHONE_SERIES, keep order."""
    out = []
    for ch in text:
        if ch.isspace():
            out.append(ch)
            continue
        consonant, order = decompose(ch)
        target = HOMOPHONE_SERIES.get(consonant, consonant)
        out.append(chr(CODEPOINT_BY_SYLLABLE[(target, order)]))
    return "".join(out)


def test_plan_name_strings() -> None:
    # ኃይለ ሥላሴ appears in IMPLEMENTATION_PLAN Task 3: ኃ (x, order 4) → ሃ and
    # ሥ (sz, order 6) → ስ; the expectation is re-derived from the tables, not
    # only hand-typed. ፀሐይ is the ARCHITECTURE 4.5 lexicon example.
    for src, pinned in [("ኃይለ ሥላሴ", "ሃይለ ስላሴ"), ("ፀሐይ", "ጸሀይ")]:
        assert normalize(src) == _collapse_via_tables(src) == pinned


def test_nfc_applied() -> None:
    assert normalize("Tesfayé") == "Tesfayé"  # e + combining acute → é


def test_whitespace_normalized() -> None:
    assert normalize("  ተስፋዬ \t ገብረመድህን \n") == "ተስፋዬ ገብረመድህን"
    assert normalize("Tesfaye   Gebremedhin") == "Tesfaye Gebremedhin"
    assert normalize("") == ""
    assert normalize(" \t\n ") == ""
    assert normalize("።") == ""  # punctuation-only input


def test_latin_and_mixed_text_pass_through() -> None:
    assert normalize("Tesfaye Gebremedhin") == "Tesfaye Gebremedhin"
    assert normalize("ተስፋዬ (Tesfaye)") == "ተስፋዬ (Tesfaye)"  # ASCII punctuation kept


def test_non_syllable_ethiopic_passes_through() -> None:
    # Digits, tonal marks, combining marks, Extended block: out of Task 2
    # scope, must pass through unchanged (documented in the module docstring).
    for cp in (0x1369, 0x137B, 0x1390, 0x135F, 0x2D80):
        assert normalize("ሀ" + chr(cp)) == "ሀ" + chr(cp), f"U+{cp:04X}"


def test_idempotent_over_every_ethiopic_character() -> None:
    for first, last in ETHIOPIC_RANGES:
        for cp in range(first, last + 1):
            try:
                unicodedata.name(chr(cp))
            except ValueError:
                continue
            once = normalize(chr(cp))
            assert normalize(once) == once, f"U+{cp:04X}"


@pytest.mark.parametrize(
    "text",
    [
        "ኃይለ ሥላሴ",
        "ወይዘሮ፡ጸሐይ ገብረመድህን።",
        "ፀሐይ",
        "Tesfayé  G/Medhin ።",
        "".join(chr(cp) for cp in SYLLABLES),
        " \t ",
        "",
    ],
)
def test_idempotent_on_strings(text: str) -> None:
    once = normalize(text)
    assert normalize(once) == once


def test_docstring_examples() -> None:
    import doctest

    import habesha_names.fidel.normalize as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
