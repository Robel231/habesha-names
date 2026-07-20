"""Tests for translit.variants -- the spelling-variant generator (Task 7).

Every name string here comes from IMPLEMENTATION_PLAN / ARCHITECTURE 4.2
(Tsehay ts<->s<->tz, Gebre sixth-order vowel, Tesfay/Tesfai/Tesfaye,
Kebede/Kebbede, Alemu/Allemu, Bethlehem/Betelhem, the Arabic-origin
groups, the Gebremedhin compound forms) or from the seeded lexicon.
Mechanics tests that need none of those use non-name ASCII vectors --
algorithm behavior pins, not linguistic claims.

The ARCHITECTURE 6 property (every variant matches its source at >= 0.8)
is wired against ``sim`` directly. The original Task 7 carve-out for
slash/dot abbreviation forms ("G/Medhin") was removed in Task 8: the
variant-set overlap term wired into ``sim`` scores them 0.85.
"""

from __future__ import annotations

import pytest

from habesha_names._data import lexicon
from habesha_names.match.token import sim
from habesha_names.translit.variants import variants

# Plan/architecture names used as property-test sources.
PLAN_NAMES = [
    "Tsehay",
    "Tesfaye",
    "Kebede",
    "Alemu",
    "Gebre",
    "Gebremedhin",
    "Hailemariam",
    "Bethlehem",
    "Mohammed",
    "Hussein",
    "Fatuma",
    "ፀሐይ",
    "ገብረመድህን",
    "ተስፋዬ",
]


def all_sources() -> list[str]:
    return sorted(set(PLAN_NAMES) | {entry.canonical for entry in lexicon().given_names})


def test_base_spelling_is_first_and_name_cased() -> None:
    assert variants("Tesfaye")[0] == "Tesfaye"
    assert variants("TESFAYE")[0] == "Tesfaye"
    assert variants("tesfaye")[0] == "Tesfaye"
    assert variants("ተስፋዬ")[0] == "Tesfaye"


def test_terminal_glide_group() -> None:
    # ARCHITECTURE 4.2: terminal -ay|-ai|-aye (Tesfay/Tesfai/Tesfaye).
    group = ("Tesfaye", "Tesfay", "Tesfai")
    for source in group:
        produced = set(variants(source))
        for other in group:
            assert other in produced, f"{source} did not produce {other}"


def test_tsehay_family_and_fidel_identity() -> None:
    # ARCHITECTURE 4.2: ts<->s<->tz on the canonical example.
    produced = variants("ጸሐይ")
    assert {"Tsehay", "Tsehai", "Sehay", "Tzehay"} <= set(produced)
    # Homophone fidel spellings generate the identical variant list.
    assert variants("ፀሐይ") == variants("ጸሀይ") == produced


def test_gemination_doubling_and_collapse() -> None:
    # ARCHITECTURE 4.2: Kebede/Kebbede, Alemu/Allemu -- both directions.
    assert "Kebbede" in variants("Kebede")
    assert "Allemu" in variants("Alemu")
    assert "Kebede" in variants("Kebbede")


def test_sixth_order_vowel_ambiguity() -> None:
    # ARCHITECTURE 4.2: Gäbrä -> Gebre|Gabre. Gebra was retired by the
    # task-16 ending-pair ruling (Robel, 2026-07-20, task-16b): the
    # last-stem-vowel e->a application bridged the final-vowel-class
    # boundary that marks morphologically distinct names
    # (Berhane/Berhana-style endings).
    produced = set(variants("Gebre"))
    assert "Gabre" in produced
    assert "Gebra" not in produced


def test_q_k_alternation() -> None:
    # ARCHITECTURE 4.2: q<->k (ቀ); Bekele/Beqele is the seeded lexicon pair.
    assert "Beqele" in variants("Bekele")
    assert "Bekele" in variants("Beqele")


def test_h_kh_alternation() -> None:
    # ARCHITECTURE 4.2: h<->kh (ኀ). Non-name ASCII vector for the mechanics.
    assert "Bakha" in variants("Bakha")  # identity survives
    assert "Baha" in variants("Bakha")
    assert "Sekhay" in variants("Sehay")


def test_arabic_origin_groups() -> None:
    # ARCHITECTURE 4.2 Arabic-origin table (lives in given_names.json).
    assert {"Mohamed", "Muhammed", "Mohammad", "Mahamed"} <= set(variants("Mohammed"))
    assert {"Husen", "Hussen"} <= set(variants("Hussein"))
    assert "Fatima" in variants("Fatuma")
    # A listed variant maps back to its group.
    assert "Fatuma" in variants("Fatima")


def test_we_wo_alternation() -> None:
    # task-3b MANDATORY rule: both spellings occur in the wild.
    assert "Wolde" in variants("Welde")
    assert "Welde" in variants("Wolde")
    assert "Woizero" in variants("Weizero")


def test_wa_ua_alternation() -> None:
    # task-3b: labialized rendering is "ua" (ኋላ -> Huala), but "wa"
    # spellings occur in the wild -- both directions rewrite.
    assert "Hwala" in variants("ኋላ")
    assert "Huala" in variants("Hwala")


def test_gn_ny_alternation() -> None:
    # task-3b: ኘ -> gn confirmed, with gn<->ny as a variant rule
    # (Tigrigna/Tigrinya-style alternation).
    assert "Agenyehu" in variants("Agegnehu")
    assert "Agegnehu" in variants("Agenyehu")


def test_bethlehem_pair() -> None:
    # ARCHITECTURE 4.2: é<->ie<->e family (Bethlehem/Betelhem).
    assert {"Betelhem", "Betlehem"} <= set(variants("Bethlehem"))


def test_epenthetic_vowel_insertion() -> None:
    # task-16 (plan Task 16 rule candidates): epenthetic i/e insertion in
    # consonant clusters -- the Latin-side mirror of 6th-order epenthesis.
    assert "Ahimed" in variants("Ahmed")
    assert {"Mekides", "Mekedes"} <= set(variants("Mekdes"))
    assert "Alimaz" in variants("Almaz")
    assert "Gebremedihin" in variants("Gebremedhin")
    assert "Tewoderos" in variants("Tewodros")


def test_epenthesis_never_splits_one_sound_digraphs() -> None:
    # gn is one sound (task-3b gn<->ny rule); ts likewise -- epenthesis
    # must not insert a vowel inside them.
    produced = set(variants("Agegnehu"))
    assert "Ageginehu" not in produced
    assert "Agegenehu" not in produced
    produced = set(variants("Tsehay"))
    assert "Tisehay" not in produced
    assert "Tesehay" not in produced


def test_interior_vowel_deletion() -> None:
    # task-16: guarded interior-vowel deletion (plan: Tewodros <-> Tewdros).
    assert "Tewdros" in variants("Tewodros")
    # A word-final vowel is never deleted (ending-pair constraint).
    assert "Kebed" not in variants("Kebede")
    assert "Hail" not in variants("Haile")


def test_e_i_wobble() -> None:
    # task-16: e<->i between consonants (plan: Yohannes <-> Yohannis).
    assert "Yohannis" in variants("Yohannes")
    assert "Yohannes" in variants("Yohannis")
    # Word-final vowels are out of scope (ending-pair constraint).
    assert "Abebi" not in variants("Abebe")


def test_ei_ie_transposition() -> None:
    # task-16: ei<->ie transposition (plan: Hussein <-> Hussien), both
    # directions; composes with undoubling (mechanics: Husien).
    assert {"Hussien", "Husien"} <= set(variants("Hussein"))
    assert "Hussein" in variants("Hussien")
    # Never at word-final position: final -ie is an ending-pair form.
    assert "Kassei" not in variants("Kassie")


def test_first_vowel_o_e_wobble() -> None:
    # task-16: 1st-vs-4th-order fidel vowel confusion on the first vowel
    # (plan: Mohammed <-> Mehammed). Key-breaking: applies alone and only
    # to the first vowel.
    assert "Mehammed" in variants("Mohammed")
    assert "Tewodres" not in variants("Tewodros")


def test_min_weight_floor_admits_attested_chains() -> None:
    # task-16: _MIN_WEIGHT 0.02 -> 0.01 so a wobble x epenthesis chain
    # (0.15 x 0.12 = 0.018) survives -- engine mechanics on a lexicon name.
    assert "Birehanu" in variants("Berhanu")


def test_bethlehem_family_rule_treatment() -> None:
    # plan Task 16 Bethlehem-family decision: RULE treatment -- th->t
    # composed with epenthetic e reaches the highest-frequency attested
    # form. The deeper family members (Betelihem, Bethelhem) need
    # three-rewrite chains that rank outside the top-25 window; they are
    # review-queued as lexicon-variant candidates for Robel (PROGRESS.md).
    assert "Betelehem" in variants("Bethlehem")


def test_no_ending_pair_rules() -> None:
    # task-16 HARD CONSTRAINT (plan trap list): final -u/-e/-ie/-a endings
    # mark morphologically related but DISTINCT names; no RULE may bridge
    # them. RULED by Robel 2026-07-20: the final e<->ie rewrite is
    # CONFIRMED (key-preserving, cannot cross the -u/-e/-a splits) and the
    # last-stem-vowel e->a rewrite is RETIRED (task-16b) -- no rule
    # exceptions remain. Task 18 (wave 1): Robel's authored Kassa entry
    # RECORDS Kassu and Kassie as variants (ending-pair ruling 3, 2026-07-20:
    # Kassa ships as-is) -- recorded lexicon data is his call and may bridge;
    # the constraint here is on generated output, so a sibling recorded on
    # the base's own entry is carved out per direction rather than asserted
    # absent. Every other pair must stay unbridged in both directions.
    from habesha_names._data import lexicon

    recorded = {
        entry.canonical: {v.lower() for v in entry.variants}
        for entry in lexicon().given_names
    }
    sibling_pairs = [
        ("Haile", "Hailu"),
        ("Berhanu", "Berihun"),
        ("Berhanu", "Berhane"),
        ("Berhanu", "Birhan"),
        ("Alemu", "Alem"),
        ("Zewde", "Zewdu"),
        ("Kassa", "Kassu"),
        ("Kassa", "Kassie"),
        ("Worku", "Workie"),
        ("Girma", "Girmay"),
    ]
    bridged_by_robels_data = []
    for base, sibling in sibling_pairs:
        if sibling.lower() in recorded.get(base, set()):
            bridged_by_robels_data.append((base, sibling))
            continue
        assert sibling not in variants(base), f"{sibling} generated from {base}"
        if base.lower() not in recorded.get(sibling, set()):
            assert base not in variants(sibling), f"{base} generated from {sibling}"
    # the carve-out is exactly the two ruling-3 recordings, nothing more
    assert bridged_by_robels_data == [("Kassa", "Kassu"), ("Kassa", "Kassie")]


def test_compound_splits_joins_abbreviations() -> None:
    # ARCHITECTURE 4.2: Gebremedhin <-> Gebre Medhin <-> Gebre-Medhin
    # <-> G/Medhin <-> G.Medhin.
    produced = set(variants("Gebremedhin"))
    assert {"Gebre Medhin", "Gebre-Medhin", "G/Medhin", "G.Medhin"} <= produced
    assert "Gebremedhin" in variants("Gebre Medhin")
    assert "Gebremedhin" in variants("Gebre-Medhin")
    assert "Gebremedhin" in variants("G/Medhin")
    assert "Gebremedhin" in variants("G.Medhin")


def test_abbreviation_expansion_covers_all_candidates() -> None:
    # G/ has two lexicon candidates: Gebre- (compound) and Girma (given).
    produced = set(variants("G/Medhin"))
    assert "Gebremedhin" in produced
    assert "Girma Medhin" in produced


def test_multi_token_names() -> None:
    produced = set(variants("Tsehay Gebremedhin"))
    assert "Tsehay Gebre Medhin" in produced
    assert "Sehay Gebremedhin" in produced
    # Fidel full name from the plan parses through the same path.
    assert "Tsehay Gebremedhin" in variants("ጸሐይ ገብረመድህን")


def test_top_n_and_validation() -> None:
    assert variants("Kebede", n=1) == ["Kebede"]
    assert len(variants("Kebede", n=5)) == 5
    assert len(variants("Kebede")) <= 25
    with pytest.raises(ValueError):
        variants("Kebede", n=0)


def test_n_is_a_prefix_slice_of_the_ranking() -> None:
    full = variants("Gebremedhin", n=25)
    assert variants("Gebremedhin", n=5) == full[:5]
    assert variants("Gebremedhin", n=10) == full[:10]


def test_no_duplicates_and_deterministic() -> None:
    for source in all_sources():
        produced = variants(source)
        assert len(produced) == len(set(produced)), f"duplicates for {source}"
        assert produced == variants(source), f"nondeterministic for {source}"


def test_empty_and_letterless_input() -> None:
    assert variants("") == []
    assert variants("   ") == []
    assert variants("።") == []


def test_property_every_variant_matches_its_source() -> None:
    # ARCHITECTURE 6 / plan Task 7 property, wired against sim. No
    # carve-outs: since Task 8 wired variant-set overlap into sim, even
    # slash/dot abbreviation forms ("G/Medhin") score VARIANT_WEIGHT.
    for source in all_sources():
        for variant in variants(source):
            score = sim(source, variant)
            assert score >= 0.8, f"sim({source!r}, {variant!r}) = {score:.3f}"


def test_docstring_examples() -> None:
    import doctest

    import habesha_names.translit.variants as mod

    results = doctest.testmod(mod)
    assert results.attempted > 0
    assert results.failed == 0
