"""Task 5 parser tests (IMPLEMENTATION_PLAN Task 5, ARCHITECTURE 4.3).

Every example name comes from the plan's required Task 5 list or from the
agent-seeded (review-queued) lexicon; no new names are invented here. Fidel
expectations are computed via ``normalize()`` instead of being hand-typed a
second time, so there is exactly one source of truth for collapsed spellings.
"""

from __future__ import annotations

import pytest

from habesha_names.fidel.normalize import normalize
from habesha_names.parse.parser import ParsedName, parse

# --- plan-required cases ---------------------------------------------------


def test_three_token_latin_roles() -> None:
    parsed = parse("Abebe Bikila Wolde")
    assert isinstance(parsed, ParsedName)
    assert parsed.given == "Abebe"
    assert parsed.patronym == "Bikila"
    assert parsed.avonym == "Wolde"
    assert parsed.title is None
    assert parsed.script == "latin"
    assert parsed.has_surname == "no"
    assert parsed.given_is_compound is False
    assert parsed.compound_confidence == 1.0
    assert parsed.raw == "Abebe Bikila Wolde"


def test_title_stripped_and_recorded() -> None:
    parsed = parse("Ato Abebe Bikila")
    assert parsed.title == "Ato"
    assert parsed.given == "Abebe"
    assert parsed.patronym == "Bikila"
    assert parsed.avonym is None


def test_joined_compound_given() -> None:
    parsed = parse("Hailemariam Desalegn")
    assert parsed.given == "Hailemariam"
    assert parsed.patronym == "Desalegn"
    assert parsed.given_is_compound is True
    assert parsed.compound_confidence == 1.0


def test_spaced_compound_is_joined_but_flagged_ambiguous() -> None:
    parsed = parse("Haile Mariam Desalegn")
    assert parsed.given == "Hailemariam"
    assert parsed.patronym == "Desalegn"
    assert parsed.avonym is None
    assert parsed.given_is_compound is True
    assert 0.0 < parsed.compound_confidence < 1.0
    assert any("compound" in note for note in parsed.notes)


def test_abbreviation_expansion_slash() -> None:
    parsed = parse("G/Medhin Tesfaye")
    assert parsed.given == "Gebremedhin"
    assert parsed.patronym == "Tesfaye"
    assert parsed.given_is_compound is True
    assert 0.0 < parsed.compound_confidence < 1.0
    note = next(note for note in parsed.notes if "abbreviation" in note)
    assert "Gebre" in note
    assert "Girma" in note  # every candidate is auditable in the note


def test_comma_inversion() -> None:
    parsed = parse("Bikila, Abebe")
    assert parsed.given == "Abebe"
    assert parsed.patronym == "Bikila"
    assert any("comma" in note for note in parsed.notes)


def test_initial_kept_and_noted() -> None:
    parsed = parse("Abebe B.")
    assert parsed.given == "Abebe"
    assert parsed.patronym == "B."
    assert any("initial" in note for note in parsed.notes)


def test_fidel_full_name_with_title() -> None:
    parsed = parse("ወይዘሮ ጸሐይ ገብረመድህን")
    assert parsed.title == "Weizero"  # canonical decided in task-3b (ወ order 1 = "we")
    assert parsed.given == normalize("ጸሐይ")
    assert parsed.patronym == normalize("ገብረመድህን")
    assert parsed.avonym is None
    assert parsed.script == "ethiopic"
    # the patronym is a known compound; the parser notes it without splitting
    assert any("Gebre" in note and "Medhin" in note for note in parsed.notes)


def test_diaspora_mode_flags_surname_unknown() -> None:
    default = parse("Abebe Bikila")
    diaspora = parse("Abebe Bikila", assume_diaspora=True)
    assert default.has_surname == "no"
    assert diaspora.has_surname == "unknown"
    assert any("diaspora" in note for note in diaspora.notes)
    assert (diaspora.given, diaspora.patronym) == (default.given, default.patronym)


# --- behavior pins around the required cases --------------------------------


def test_two_token_name_has_no_avonym() -> None:
    parsed = parse("Abebe Bikila")
    assert parsed.patronym == "Bikila"
    assert parsed.avonym is None


def test_title_matching_case_insensitive_and_abbreviated() -> None:
    assert parse("ato Abebe Bikila").title == "Ato"
    assert parse("W/ro Tsehay Tesfaye").title == "Weizero"
    # the pre-task-3b conventional spelling stays recognized as an input form
    assert parse("Woizero Tsehay Tesfaye").title == "Weizero"
    assert parse("Dr. Tsehay Tesfaye").title == "Dr"


def test_spaced_compound_confidence_rises_when_unjoined_reading_overflows() -> None:
    ambiguous = parse("Haile Mariam Desalegn")
    overflow = parse("Haile Mariam Tesfaye Abebe")
    assert overflow.given == "Hailemariam"
    assert overflow.patronym == "Tesfaye"
    assert overflow.avonym == "Abebe"
    assert 0.0 < overflow.compound_confidence < 1.0
    assert overflow.compound_confidence > ambiguous.compound_confidence


def test_two_token_spaced_compound_joins_to_given_only() -> None:
    # Agent-chosen default (review queue): prefix+second with nothing after
    # is still read as one compound given name, low confidence.
    parsed = parse("Haile Mariam")
    assert parsed.given == "Hailemariam"
    assert parsed.patronym is None
    assert parsed.given_is_compound is True
    assert 0.0 < parsed.compound_confidence < 1.0


def test_abbreviation_expansion_dot_form() -> None:
    assert parse("G.Medhin Tesfaye").given == "Gebremedhin"


def test_abbreviation_in_patronym_position() -> None:
    parsed = parse("Tesfaye G/Medhin")
    assert parsed.given == "Tesfaye"
    assert parsed.patronym == "Gebremedhin"
    assert parsed.given_is_compound is False
    assert 0.0 < parsed.compound_confidence < 1.0


def test_fidel_homophone_spellings_parse_identically() -> None:
    a = parse("ፀሐይ ገብረመድህን")
    b = parse("ጸሀይ ገብረመድህን")
    assert (a.given, a.patronym) == (b.given, b.patronym)


def test_fidel_spaced_compound_joins() -> None:
    # fidel forms taken verbatim from the seeded lexicon (review-queued data)
    parsed = parse("ኃይለ ማርያም ደሳለኝ")
    assert parsed.given == normalize("ኃይለማርያም")
    assert parsed.patronym == normalize("ደሳለኝ")
    assert parsed.given_is_compound is True
    assert 0.0 < parsed.compound_confidence < 1.0


# --- Task 15: phonetic-key compound fallback ---------------------------------
# "Gebrie" / "Hailie" are the rewritten element spellings named by the v0.2
# plan (Gebrie corpus-attested per the mining report); "Hailu" is the plan's
# morphological-sibling trap case. No new names invented here.


def test_rewritten_spaced_compound_joins_input_preserving() -> None:
    parsed = parse("Gebrie Medhin")
    assert parsed.given == "Gebriemedhin"  # input spelling, not canonical
    assert parsed.patronym is None
    assert parsed.given_is_compound is True
    # key-level evidence sits below the exact spaced-join confidence
    assert 0.0 < parsed.compound_confidence < parse("Haile Mariam").compound_confidence
    note = parsed.notes[0]
    assert "phonetic-key" in note
    assert "Gebre" in note and "Medhin" in note  # matched elements auditable


def test_rewritten_spaced_compound_confidence_rises_on_overflow() -> None:
    ambiguous = parse("Hailie Mariam Desalegn")
    overflow = parse("Hailie Mariam Tesfaye Abebe")
    assert ambiguous.given == "Hailiemariam"
    assert overflow.given == "Hailiemariam"
    assert overflow.compound_confidence > ambiguous.compound_confidence
    # ... and each fuzzy constant sits below its exact counterpart.
    assert overflow.compound_confidence < parse("Haile Mariam Tesfaye Abebe").compound_confidence
    assert ambiguous.compound_confidence < parse("Haile Mariam Desalegn").compound_confidence


def test_sibling_element_does_not_fuzzy_join() -> None:
    # Hailu keys HL:ao, Haile keys HL:ae -- the v2 final-vowel slot is what
    # makes the fallback safe against distinct related names.
    parsed = parse("Hailu Mariam")
    assert parsed.given == "Hailu"
    assert parsed.patronym == "Mariam"
    assert parsed.given_is_compound is False
    assert parsed.compound_confidence == 1.0


def test_fuzzy_join_structural_roles_reparse_stable() -> None:
    # The full _SAMPLES stability property includes given_is_compound, which
    # an input-preserving fuzzy join deliberately does not survive (the
    # rewritten joined spelling is not in the lexicon -- documented in
    # parse.parser); the structural roles must still be stable.
    parsed = parse("Gebrie Medhin Desalegn")
    again = parse(str(parsed))
    assert (again.given, again.patronym, again.avonym) == (
        parsed.given,
        parsed.patronym,
        parsed.avonym,
    )


def test_mixed_script_detected() -> None:
    assert parse("Abebe ጸሐይ").script == "mixed"


def test_empty_input_raises() -> None:
    for bad in ("", "   ", "።"):
        with pytest.raises(ValueError):
            parse(bad)


def test_single_token_title_treated_as_name_with_note() -> None:
    parsed = parse("Ato")
    assert parsed.given == "Ato"
    assert parsed.title is None
    assert any("title" in note for note in parsed.notes)


def test_raw_is_preserved_verbatim() -> None:
    raw = "  Ato   Abebe Bikila "
    assert parse(raw).raw == raw


def test_extra_tokens_are_noted_not_dropped_silently() -> None:
    parsed = parse("Abebe Bikila Wolde Tesfaye")
    assert parsed.avonym == "Wolde"
    assert any("Tesfaye" in note for note in parsed.notes)


# --- properties --------------------------------------------------------------

_SAMPLES = (
    "Ato Abebe Bikila",
    "Abebe Bikila Wolde",
    "Hailemariam Desalegn",
    "Haile Mariam Desalegn",
    "G/Medhin Tesfaye",
    "Bikila, Abebe",
    "Abebe B.",
    "ወይዘሮ ጸሐይ ገብረመድህን",
)


def test_str_and_reparse_stability() -> None:
    # ARCHITECTURE 6: parse(str(parsed)) is stable on the structural fields.
    for sample in _SAMPLES:
        parsed = parse(sample)
        again = parse(str(parsed))
        assert again.title == parsed.title
        assert again.given == parsed.given
        assert again.patronym == parsed.patronym
        assert again.avonym == parsed.avonym
        assert again.script == parsed.script
        assert again.given_is_compound == parsed.given_is_compound


def test_deterministic() -> None:
    for sample in _SAMPLES:
        assert parse(sample) == parse(sample)


def test_docstring_examples() -> None:
    import doctest

    # `habesha_names.parse` the attribute is the parse() function since Task 9;
    # the submodules remain importable via `from ... import`.
    from habesha_names.parse import compounds, parser, titles

    for mod in (titles, compounds, parser):
        results = doctest.testmod(mod)
        assert results.attempted > 0
        assert results.failed == 0
