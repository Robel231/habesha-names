"""Tests for the data layer (Task 4): packaged lexicons + validated lazy loader.

Name expectations here reference only plan/architecture-given items (the
Tsehay contract example from ARCHITECTURE 4.5, the title list and G/-expansion
from IMPLEMENTATION_PLAN Task 4 / ARCHITECTURE 4.3, and the Task 3/5 seed
names). The seeded entries themselves are UNVERIFIED linguistic data flagged
in PROGRESS.md -> Human review queue; these tests check contracts, not
linguistic truth.
"""

import copy
from typing import Any

import pytest

from habesha_names._data import (
    LexiconError,
    _check_cross_references,
    _parse_compounds,
    _parse_given_names,
    _parse_titles,
    lexicon,
)
from habesha_names.fidel.syllable import is_ethiopic
from habesha_names.translit.to_latin import transliterate

# --------------------------------------------------------------------------
# Loading the real packaged data
# --------------------------------------------------------------------------


def test_lexicon_is_a_lazy_cached_singleton() -> None:
    lexicon.cache_clear()
    assert lexicon.cache_info().currsize == 0  # nothing loaded before first call
    first = lexicon()
    assert lexicon() is first
    assert lexicon.cache_info().currsize == 1
    assert lexicon.cache_info().hits >= 1


def test_given_names_seed_size() -> None:
    # Task 4: ~50 highest-frequency names.
    assert len(lexicon().given_names) >= 50


def test_every_given_name_ships_unverified() -> None:
    # HARD REQUIREMENT (plan Task 4): ALL agent-seeded entries are
    # "verified": false until Robel flips them.
    assert all(name.verified is False for name in lexicon().given_names)


def test_architecture_contract_example_tsehay() -> None:
    # ARCHITECTURE 4.5 gives this exact entry as the contract example.
    entries = {name.canonical: name for name in lexicon().given_names}
    tsehay = entries["Tsehay"]
    assert tsehay.fidel == "ፀሐይ"
    assert set(tsehay.variants) >= {"Tsehai", "Sehay", "Tzehay"}
    assert tsehay.gender == {"f": 0.97, "m": 0.03}
    assert tsehay.origin == "amharic"
    assert tsehay.freq_tier == 1


def test_plan_seed_names_are_present() -> None:
    # Names used by plan Tasks 3/5/6 tests must exist in the lexicon.
    canonicals = {name.canonical for name in lexicon().given_names}
    assert {
        "Tesfaye",
        "Gebremedhin",
        "Tsehay",
        "Abebe",
        "Bikila",
        "Wolde",
        "Hailemariam",
        "Desalegn",
        "Girma",
        "Mohammed",
        "Hussein",
        "Fatuma",
        "Kebede",
        "Alemu",
        "Almaz",
        "Tesfahun",
        "Abebech",
    } <= canonicals


def test_titles_cover_plan_list() -> None:
    # IMPLEMENTATION_PLAN Task 4 pins this list.
    canonicals = {title.canonical for title in lexicon().titles}
    assert {
        "Ato",
        "Woizero",
        "Woizerit",
        "Dr",
        "Prof",
        "Eng",
        "Qes",
        "Abba",
        "Abune",
        "Memhir",
        "Sheikh",
        "Haji",
    } <= canonicals
    assert all(title.fidel for title in lexicon().titles)  # "+ fidel forms"


def test_woizero_slash_abbreviations() -> None:
    titles = {title.canonical: title for title in lexicon().titles}
    assert "W/ro" in titles["Woizero"].abbreviations
    assert "W/rt" in titles["Woizerit"].abbreviations


def test_compound_prefixes_match_architecture_list() -> None:
    # ARCHITECTURE 4.3 prefix lexicon.
    latins = {prefix.latin for prefix in lexicon().compound_prefixes}
    assert {
        "Gebre",
        "Wolde",
        "Haile",
        "Tekle",
        "Kidane",
        "Zera",
        "Amde",
        "Fikre",
        "Berhane",
        "Welete",
    } <= latins
    genders = {prefix.latin: prefix.gender for prefix in lexicon().compound_prefixes}
    assert genders["Welete"] == "f"  # "Welete(f)" in ARCHITECTURE 4.3


def test_compound_second_elements_match_architecture_list() -> None:
    latins = {second.latin for second in lexicon().compound_seconds}
    assert {
        "Mariam",
        "Michael",
        "Giorgis",
        "Selassie",
        "Medhin",
        "Iyesus",
        "Kristos",
        "Egziabher",
        "Hiwot",
        "Haymanot",
        "Ab",
        "Tsadik",
    } <= latins


def test_g_abbreviation_expands_to_gebre_over_girma() -> None:
    # ARCHITECTURE 4.3: G/Medhin -> candidates Gebre-, Girma- weighted by
    # corpus frequency (Gebre first).
    expansions = {a.abbrev: a for a in lexicon().abbreviations}
    candidates = dict(expansions["G"].candidates)
    assert set(candidates) == {"Gebre", "Girma"}
    assert candidates["Gebre"] > candidates["Girma"]


def test_abbreviation_candidates_resolve_and_are_ranked() -> None:
    lex = lexicon()
    known = {p.latin for p in lex.compound_prefixes} | {n.canonical for n in lex.given_names}
    for expansion in lex.abbreviations:
        weights = [weight for _, weight in expansion.candidates]
        assert abs(sum(weights) - 1.0) < 1e-6, expansion.abbrev
        assert weights == sorted(weights, reverse=True), expansion.abbrev
        assert all(candidate in known for candidate, _ in expansion.candidates), expansion.abbrev


def test_all_fidel_fields_are_ethiopic() -> None:
    lex = lexicon()
    for name in lex.given_names:
        assert is_ethiopic(name.fidel), name.canonical
    for prefix in lex.compound_prefixes:
        assert is_ethiopic(prefix.fidel), prefix.latin
    for second in lex.compound_seconds:
        assert is_ethiopic(second.fidel), second.latin
    for title in lex.titles:
        for form in title.fidel:
            assert is_ethiopic(form.replace("/", "")), title.canonical


def test_gender_distributions_sum_to_one() -> None:
    for name in lexicon().given_names:
        assert abs(sum(name.gender.values()) - 1.0) < 1e-6, name.canonical
        assert set(name.gender) <= {"f", "m"}, name.canonical


def test_no_duplicate_canonicals_or_fidel() -> None:
    names = lexicon().given_names
    assert len({n.canonical.lower() for n in names}) == len(names)
    assert len({n.fidel for n in names}) == len(names)


def test_variants_never_repeat_canonical() -> None:
    for name in lexicon().given_names:
        assert name.canonical.lower() not in {v.lower() for v in name.variants}, name.canonical


def test_plan_given_fidel_transliterates_to_canonical() -> None:
    # Ties the lexicon to the Task 3 engine for the plan-pinned seeds only
    # (agent-seeded entries beyond the plan are checked in the review queue,
    # not asserted here — several are known mismatches pending Robel).
    entries = {name.canonical: name for name in lexicon().given_names}
    for canonical in ("Tesfaye", "Gebremedhin", "Tsehay"):
        assert transliterate(entries[canonical].fidel) == canonical


# --------------------------------------------------------------------------
# Validation: malformed payloads must raise LexiconError
# --------------------------------------------------------------------------

VALID_GIVEN_ENTRY: dict[str, Any] = {
    "fidel": "ፀሐይ",
    "canonical": "Tsehay",
    "variants": ["Tsehai"],
    "gender": {"f": 0.97, "m": 0.03},
    "origin": "amharic",
    "freq_tier": 1,
    "verified": False,
}


def _given_payload(**overrides: Any) -> dict[str, Any]:
    entry = copy.deepcopy(VALID_GIVEN_ENTRY)
    entry.update(overrides)
    return {"schema": 1, "entries": [entry]}


def test_valid_given_entry_parses() -> None:
    (name,) = _parse_given_names(_given_payload())
    assert name.canonical == "Tsehay"
    assert name.variants == ("Tsehai",)


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("not an object", [1, 2]),
        ("wrong schema version", {"schema": 2, "entries": [VALID_GIVEN_ENTRY]}),
        ("missing entries key", {"schema": 1}),
        ("entries not a list", {"schema": 1, "entries": {}}),
        ("entries empty", {"schema": 1, "entries": []}),
        ("entry not an object", {"schema": 1, "entries": ["Tsehay"]}),
        (
            "missing key",
            {
                "schema": 1,
                "entries": [{k: v for k, v in VALID_GIVEN_ENTRY.items() if k != "origin"}],
            },
        ),
        ("unexpected key", _given_payload(extra="boom")),
        ("empty canonical", _given_payload(canonical="")),
        ("non-ascii canonical", _given_payload(canonical="Tséhay")),
        ("latin fidel", _given_payload(fidel="Tsehay")),
        ("variant repeats canonical", _given_payload(variants=["tsehay"])),
        ("duplicate variants", _given_payload(variants=["Tsehai", "tsehai"])),
        ("gender sum below one", _given_payload(gender={"f": 0.5})),
        ("gender unknown key", _given_payload(gender={"x": 1.0})),
        ("gender weight not a number", _given_payload(gender={"f": "high"})),
        ("unknown origin", _given_payload(origin="klingon")),
        ("freq tier out of range", _given_payload(freq_tier=0)),
        ("freq tier boolean", _given_payload(freq_tier=True)),
        ("verified not boolean", _given_payload(verified="false")),
        (
            "duplicate canonical entries",
            {"schema": 1, "entries": [VALID_GIVEN_ENTRY, VALID_GIVEN_ENTRY]},
        ),
    ],
)
def test_malformed_given_names_raise(label: str, payload: Any) -> None:
    with pytest.raises(LexiconError):
        _parse_given_names(payload)


VALID_TITLE_ENTRY: dict[str, Any] = {
    "canonical": "Ato",
    "abbreviations": [],
    "fidel": ["አቶ"],
    "gender": "m",
    "category": "civil",
    "verified": False,
}


def _title_payload(**overrides: Any) -> dict[str, Any]:
    entry = copy.deepcopy(VALID_TITLE_ENTRY)
    entry.update(overrides)
    return {"schema": 1, "entries": [entry]}


def test_valid_title_entry_parses() -> None:
    (title,) = _parse_titles(_title_payload())
    assert title.canonical == "Ato"
    assert title.gender == "m"


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("unknown category", _title_payload(category="royal")),
        ("bad gender", _title_payload(gender="x")),
        ("no fidel forms", _title_payload(fidel=[])),
        ("non-ethiopic fidel", _title_payload(fidel=["Ato"])),
        ("bad abbreviation character", _title_payload(abbreviations=["W\\ro"])),
        ("unexpected key", _title_payload(notes="hi")),
    ],
)
def test_malformed_titles_raise(label: str, payload: Any) -> None:
    with pytest.raises(LexiconError):
        _parse_titles(payload)


def _compound_payload(abbrev_candidates: "list[dict[str, Any]]") -> dict[str, Any]:
    return {
        "schema": 1,
        "prefixes": [{"latin": "Gebre", "fidel": "ገብረ", "gender": "m", "verified": False}],
        "second_elements": [{"latin": "Medhin", "fidel": "መድህን", "verified": False}],
        "abbreviation_expansions": [
            {"abbrev": "G", "candidates": abbrev_candidates, "verified": False}
        ],
    }


def test_valid_compound_payload_parses() -> None:
    prefixes, seconds, abbreviations = _parse_compounds(
        _compound_payload([{"expansion": "Gebre", "weight": 1.0}])
    )
    assert prefixes[0].latin == "Gebre"
    assert seconds[0].latin == "Medhin"
    assert abbreviations[0].candidates == (("Gebre", 1.0),)


@pytest.mark.parametrize(
    ("label", "candidates"),
    [
        ("weights do not sum to one", [{"expansion": "Gebre", "weight": 0.5}]),
        (
            "weights increasing",
            [{"expansion": "Gebre", "weight": 0.2}, {"expansion": "Girma", "weight": 0.8}],
        ),
        ("zero weight", [{"expansion": "Gebre", "weight": 0.0}]),
        ("empty candidates", []),
        ("candidate missing weight", [{"expansion": "Gebre"}]),
        (
            "duplicate expansions",
            [{"expansion": "Gebre", "weight": 0.5}, {"expansion": "Gebre", "weight": 0.5}],
        ),
    ],
)
def test_malformed_compounds_raise(label: str, candidates: "list[dict[str, Any]]") -> None:
    with pytest.raises(LexiconError):
        _parse_compounds(_compound_payload(candidates))


def test_unresolvable_abbreviation_expansion_raises() -> None:
    prefixes, _, abbreviations = _parse_compounds(
        _compound_payload([{"expansion": "Gebre", "weight": 1.0}])
    )
    given_names = lexicon().given_names
    _check_cross_references(prefixes, given_names, abbreviations)  # resolvable: fine
    _, _, dangling = _parse_compounds(_compound_payload([{"expansion": "Nobody", "weight": 1.0}]))
    with pytest.raises(LexiconError, match="Nobody"):
        _check_cross_references(prefixes, given_names, dangling)


def test_docstring_examples() -> None:
    import doctest

    import habesha_names._data as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
