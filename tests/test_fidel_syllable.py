"""Tests for fidel tables + syllable decomposition.

Every pinned expectation is cross-checked against ``unicodedata.name`` inside
the tests, so a hand-typing mistake in this file fails loudly instead of
silently agreeing with a wrong table.
"""

import unicodedata

import pytest

from habesha_names.fidel.syllable import Syllable, compose, decompose, is_ethiopic
from habesha_names.fidel.tables import (
    CODEPOINT_BY_SYLLABLE,
    CONSONANT_BY_BASE,
    ETHIOPIC_RANGES,
    SYLLABLES,
)

NAME_PREFIX = "ETHIOPIC SYLLABLE "
SUFFIXES_BY_ORDER = {
    1: {"A"},
    2: {"U"},
    3: {"I"},
    4: {"AA"},
    5: {"EE"},
    6: {"E"},
    7: {"O"},
    8: {"WA", "OA", "WAA"},
}

# Pin glyphs from IMPLEMENTATION_PLAN Task 1. The Unicode name column is what
# ties each pin to the character standard rather than to memory.
PINS = [
    (0x1200, "h", 1, "ETHIOPIC SYLLABLE HA"),
    (0x1208, "l", 1, "ETHIOPIC SYLLABLE LA"),
    (0x1264, "b", 5, "ETHIOPIC SYLLABLE BEE"),
    (0x133D, "ts'", 6, "ETHIOPIC SYLLABLE TSE"),
    (0x1299, "ny", 2, "ETHIOPIC SYLLABLE NYU"),
]


@pytest.mark.parametrize(("cp", "consonant", "order", "uname"), PINS)
def test_pinned_glyphs(cp: int, consonant: str, order: int, uname: str) -> None:
    assert unicodedata.name(chr(cp)) == uname
    assert decompose(chr(cp)) == Syllable(consonant, order)
    assert compose(consonant, order) == chr(cp)


def test_decompose_compose_roundtrip_every_syllable() -> None:
    for cp in SYLLABLES:
        syllable = decompose(chr(cp))
        assert compose(*syllable) == chr(cp), f"U+{cp:04X}"


def test_tables_cover_exactly_the_unicode_syllables() -> None:
    """Independent unicodedata scan: SYLLABLES holds every ETHIOPIC SYLLABLE
    in the two source blocks and nothing else (no punctuation/digits/marks)."""
    for cp in range(0x1200, 0x13A0):
        try:
            name = unicodedata.name(chr(cp))
        except ValueError:
            assert cp not in SYLLABLES, f"U+{cp:04X} unassigned but in tables"
            continue
        if name.startswith(NAME_PREFIX):
            assert cp in SYLLABLES, f"U+{cp:04X} {name} missing from tables"
        else:
            assert cp not in SYLLABLES, f"U+{cp:04X} {name} wrongly in tables"


def _name_rest(cp: int) -> str:
    rest = unicodedata.name(chr(cp))[len(NAME_PREFIX) :]
    if rest.startswith("SEBATBEIT "):
        rest = rest[len("SEBATBEIT ") :]
    return rest


def test_orders_and_series_agree_with_unicode_names() -> None:
    """Re-derive series structure from unicodedata, independent of the generator:
    the order-1 member's name minus its trailing 'A' is the consonant fragment;
    every member of the series must be that fragment + the suffix of its order."""
    by_consonant: dict[str, dict[int, int]] = {}
    for cp, (consonant, order) in SYLLABLES.items():
        assert order not in by_consonant.setdefault(consonant, {})
        by_consonant[consonant][order] = cp
    for consonant, members in by_consonant.items():
        assert 1 in members, f"series {consonant!r} has no first-order member"
        first = _name_rest(members[1])
        assert first.endswith("A"), (consonant, first)
        frag = first[:-1].rstrip()
        # Labels are mechanical lowercase fragments except flagged overrides
        # (currently the ejective apostrophe, e.g. TS -> ts').
        assert consonant.replace("'", "") == frag.lower(), (consonant, frag)
        for order, cp in members.items():
            rest = _name_rest(cp)
            assert rest.startswith(frag), (hex(cp), rest, frag)
            suffix = rest[len(frag) :].lstrip()
            assert suffix in SUFFIXES_BY_ORDER[order], (hex(cp), rest, suffix, order)


def test_consonant_bases_are_the_first_order_members() -> None:
    assert set(CONSONANT_BY_BASE.values()) == {c for c, _ in SYLLABLES.values()}
    for base, consonant in CONSONANT_BY_BASE.items():
        assert SYLLABLES[base] == (consonant, 1)


def test_reverse_table_is_a_bijection() -> None:
    assert len(CODEPOINT_BY_SYLLABLE) == len(SYLLABLES)


def test_decompose_rejects_non_syllables() -> None:
    # chr(0x1362) = ETHIOPIC FULL STOP, chr(0x135F) = combining gemination mark:
    # inside the block but not syllables.
    for bad in ("A", "z", " ", chr(0x1362), chr(0x135F), chr(0x2D80), "1"):
        with pytest.raises(ValueError, match="not an Ethiopic syllable"):
            decompose(bad)


def test_decompose_rejects_non_single_characters() -> None:
    for bad in ("", "ሀሀ", "ሀ "):
        with pytest.raises(ValueError, match="single character"):
            decompose(bad)


def test_compose_rejects_unknown_combinations() -> None:
    with pytest.raises(ValueError, match="no fidel syllable"):
        compose("h", 9)
    with pytest.raises(ValueError, match="no fidel syllable"):
        compose("zz", 1)
    with pytest.raises(ValueError, match="no fidel syllable"):
        compose("qw", 2)  # labialized velar series have no second order


def test_is_ethiopic() -> None:
    # Fidel names from the plan documents (ተስፋዬ, ገብረመድህን).
    assert is_ethiopic("ተስፋዬ")
    assert is_ethiopic("ተስፋዬ ገብረመድህን")
    assert is_ethiopic("ሀ" + chr(0x1362))  # Ethiopic punctuation counts as Ethiopic
    assert is_ethiopic(chr(0x2D80))  # Extended block recognized (not decomposable)
    assert not is_ethiopic("Tesfaye")
    assert not is_ethiopic("ተስፋዬ Tesfaye")  # mixed script
    assert not is_ethiopic("")
    assert not is_ethiopic("   ")
    assert not is_ethiopic("ሀ.")  # ASCII period is not Ethiopic


def test_ranges_are_sane() -> None:
    for first, last in ETHIOPIC_RANGES:
        assert first < last
    # Every syllable in the tables falls inside a declared Ethiopic range.
    for cp in SYLLABLES:
        assert any(first <= cp <= last for first, last in ETHIOPIC_RANGES)
