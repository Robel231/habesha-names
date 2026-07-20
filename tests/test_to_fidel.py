"""Task 21 — `to_fidel` reverse transliteration: lexicon path, rule path, properties.

Name strings are limited to lexicon spellings (fetched from `lexicon()` at
runtime, never hand-typed fidel) plus forms already named in the plan /
PROGRESS.md (Fikir, Tigist, Kidist, Yohanis, Yohannis, Tigst, Tzehay,
Kebede/Kebbede) and engine-generated spellings reproduced from `variants()`.
"""

from __future__ import annotations

import doctest
import re

import pytest

import habesha_names.translit.to_fidel as to_fidel_module
from habesha_names import (
    is_ethiopic,
    normalize,
    phonetic_key,
    to_fidel,
    transliterate,
    variants,
)
from habesha_names._data import lexicon
from habesha_names.translit.to_fidel import _fold_run, _invert_run, _lexicon_fidel


def _letter_runs(text: str) -> list[str]:
    return [run.lower() for run in re.findall(r"[A-Za-z]+", text)]


# --- lexicon path -----------------------------------------------------------


def test_every_given_canonical_returns_its_stored_fidel() -> None:
    for entry in lexicon().given_names:
        assert to_fidel(entry.canonical) == entry.fidel, entry.canonical


def test_every_recorded_spelling_returns_a_stored_fidel() -> None:
    # A variant spelling may be recorded on more than one entry; the output
    # must be the stored conventional fidel of an entry that records it.
    for entry in lexicon().given_names:
        for spelling in (entry.canonical, *entry.variants):
            out = to_fidel(spelling)
            owners = [
                other.fidel
                for other in lexicon().given_names
                if spelling.lower() in {s.lower() for s in (other.canonical, *other.variants)}
            ]
            assert out in owners, spelling


def test_compound_element_spellings_return_stored_fidel() -> None:
    lex = lexicon()
    # Same precedence as the implementation documents: given names win a
    # spelling, then prefixes, then second elements.
    seen = {
        spelling.lower()
        for entry in lex.given_names
        for spelling in (entry.canonical, *entry.variants)
    }
    for element in (*lex.compound_prefixes, *lex.compound_seconds):
        for spelling in (element.latin, *element.variants):
            if spelling.lower() in seen:
                continue
            seen.add(spelling.lower())
            assert to_fidel(spelling) == element.fidel, spelling


def test_lexicon_lookup_is_case_insensitive() -> None:
    entry = next(e for e in lexicon().given_names if e.canonical == "Tsehay")
    assert to_fidel("Tsehay") == to_fidel("tsehay") == to_fidel("TSEHAY") == entry.fidel


def test_multi_token_input_converts_per_token() -> None:
    lex = lexicon()
    tsehay = next(e for e in lex.given_names if e.canonical == "Tsehay")
    gebremedhin = next(e for e in lex.given_names if e.canonical == "Gebremedhin")
    assert to_fidel("Tsehay Gebremedhin") == f"{tsehay.fidel} {gebremedhin.fidel}"


def test_non_letter_characters_pass_through() -> None:
    # Task 18 (wave 1): "Gebre" is now also a given-name entry, and given
    # names win a spelling before prefixes (documented precedence, asserted
    # in test_compound_element_spellings_return_stored_fidel above) — so the
    # hyphen-joined tokens resolve to the given-name fidel, not the prefix's.
    lex = lexicon()
    gebre = next(e for e in lex.given_names if e.canonical == "Gebre")
    medhin = next(s for s in lex.compound_seconds if s.latin == "Medhin")
    assert to_fidel("Gebre-Medhin") == f"{gebre.fidel}-{medhin.fidel}"


def test_ethiopic_input_passes_through_verbatim() -> None:
    entry = next(e for e in lexicon().given_names if e.canonical == "Tsehay")
    assert to_fidel(entry.fidel) == entry.fidel


# --- rule path: mandated properties ----------------------------------------


#: Canonicals whose OWN key the rule path cannot reproduce, pinned exactly
#: (Task 18 wave 1 introduced the first one). "yoseph": the phonetic key
#: folds the "ph" digraph to F, but "ph" is not among the practical inverse
#: table's input folds (tz/th/kh/gh), so the rule path reads p + h as two
#: consonants and the recomposed key keeps them split (YSPH vs YSF). Same
#: digraph-fusing root cause as the ckh/skh exception classes below;
#: review-queued in PROGRESS.md (a ph fold is an engine change, Robel's call).
CANONICAL_KEY_EXCEPTIONS = frozenset({"yoseph"})


def test_rule_path_canonicals_keep_key_and_are_normalize_stable() -> None:
    # phonetic_key(transliterate(to_fidel(x))) == phonetic_key(x) over the
    # lexicon canonicals, via the rule path directly (the public function
    # would serve these from the lexicon). Key failures must equal the
    # pinned exception set; normalize-stability has no exceptions.
    key_failures: set[str] = set()
    for entry in lexicon().given_names:
        for run in _letter_runs(entry.canonical):
            out = _invert_run(run, "practical")
            if phonetic_key(transliterate(out)) != phonetic_key(run):
                key_failures.add(run)
            assert normalize(out) == out, run
            assert is_ethiopic(out), run
    assert key_failures == CANONICAL_KEY_EXCEPTIONS


#: Engine-generated spellings whose OWN HabeshaKey the rule path provably
#: cannot reproduce, pinned exactly (same discipline as the golden corpus's
#: known_fail markers: retiring one requires consciously editing this set).
#: Regenerated from this test's own output at Task 18 (wave 1): the 150 new
#: entries grew the swept variant population, 13 -> 60 (all 13 stayed, 47
#: joined, none left). Three classes, all review-queued in PROGRESS.md:
#: - the variant engine's h->kh rewrite landing right after "c", "s", or
#:   "p" (Abebech -> Abebeckh, Eshetu -> Eskhetu, Ephrem -> Epkherem, plus
#:   wave-1 Belachew/Getachew/Michael/Mengesha/Negash/Shiferaw/Teshome
#:   families): the key reads c/s/p + kh as two consonants, but every
#:   possible letter reading of the folded string fuses ch/sh/ph into one;
#: - a deletion variant ending in a non-permissible consonant cluster
#:   (Abebech -> Ababch): forward epenthesis re-inserts "i" before the
#:   final consonant, which becomes a new last stem vowel of a different
#:   class than the input's; and
#: - plain "ph" in wave-1 Yoseph's vowel-wobble variants (yeseph/yosiph/
#:   yossiph): the key folds ph -> F but "ph" is not an inverse-table input
#:   fold, so the rule path keeps p + h split (see CANONICAL_KEY_EXCEPTIONS).
KNOWN_KEY_EXCEPTIONS = frozenset(
    {
        "ababch",
        "ababeckh",
        "abbebeckh",
        "abebbeckh",
        "abebckh",
        "abebeckh",
        "abebickh",
        "abibeckh",
        "askhanafi",
        "askhenaffi",
        "askhenafi",
        "askhenfi",
        "askhennafi",
        "askhinafi",
        "askhnafi",
        "belackhew",
        "belackhiw",
        "belckhew",
        "bellackhew",
        "bilackhew",
        "epkherem",
        "epkhirem",
        "epkhrem",
        "epkhrim",
        "eskhatu",
        "eskhettu",
        "eskhetu",
        "eskhitu",
        "eskhtu",
        "getackhew",
        "getackhiw",
        "getckhew",
        "gettackhew",
        "gitackhew",
        "meckhael",
        "menegeskha",
        "mengaskha",
        "mengeskha",
        "mengiskha",
        "mengskha",
        "menigeskha",
        "mickhael",
        "mingeskha",
        "negaskh",
        "neggaskh",
        "nigaskh",
        "skheferaw",
        "skhifaraw",
        "skhiferaw",
        "skhiferraw",
        "skhifferaw",
        "skhifiraw",
        "teskhme",
        "teskhome",
        "teskhomie",
        "teskhomme",
        "tiskhome",
        "yeseph",
        "yosiph",
        "yossiph",
    }
)


def test_rule_path_generated_variants_keep_key_and_are_normalize_stable() -> None:
    # The property sweep over engine-generated variants, scoped to runs the
    # lexicon does not recognize (recognized spellings are served verbatim
    # from the lexicon by the public function and never reach the rules).
    # Slash/dot abbreviation forms are carved out, as in the Task 7 variants
    # property test. Key failures must equal the pinned exception set.
    failures: set[str] = set()
    checked: set[str] = set()
    for entry in lexicon().given_names:
        for variant in variants(entry.canonical):
            if "/" in variant or "." in variant:
                continue
            for run in _letter_runs(variant):
                if run in _lexicon_fidel() or run in checked:
                    continue
                checked.add(run)
                out = _invert_run(run, "practical")
                assert normalize(out) == out, run
                assert is_ethiopic(out), run
                if phonetic_key(transliterate(out)) != phonetic_key(run):
                    failures.add(run)
    assert len(checked) > 500  # the sweep really ran
    assert failures == KNOWN_KEY_EXCEPTIONS


def test_rule_path_round_trips_task3b_epenthesis_seeds() -> None:
    # Plan/decisions-log spellings: the composed output must render back to
    # the exact input spelling. Task 18 (wave 1): all four are now lexicon-
    # recognized (Tigist and Kidist as canonicals, Fikir on Fikre, Yohanis
    # on Yohannes), so the public function serves stored fidel — the rule
    # path is exercised directly, same as the Kebede/tzehay tests below.
    for spelling in ("Fikir", "Tigist", "Kidist", "Yohanis"):
        out = _invert_run(spelling.lower(), "practical")
        assert transliterate(out) == spelling, spelling


def test_rule_path_epenthesis_gap_falls_back_to_key_equality() -> None:
    # "Tigst" (PROGRESS-named deletion variant): no fidel string renders a
    # bare word-final "gst", so the exact round-trip is impossible; the
    # chosen reading renders with the epenthetic vowel and keeps the key.
    out = to_fidel("Tigst")
    assert transliterate(out) == "Tigist"
    assert phonetic_key(transliterate(out)) == phonetic_key("Tigst")


def test_rule_path_folds_gemination() -> None:
    # Gemination is unmarked in fidel (plan pair Kebede/Kebbede).
    assert _invert_run("kebbede", "practical") == _invert_run("kebede", "practical")


def test_rule_path_folds_collapsed_homophone_romanization() -> None:
    # "tz" is the ፀ-series romanization; normalize collapses ፀ→ጸ, so the
    # inverse folds tz→ts (Tzehay is a recorded lexicon variant; the rule
    # path is exercised directly).
    assert _invert_run("tzehay", "practical") == _invert_run("tsehay", "practical")


def test_rule_path_output_never_contains_collapsed_series() -> None:
    # Post-collapse contract: rule output is normalize-stable, i.e. free of
    # the homophone source series (the inverse table has no rows for them).
    for spelling in ("Fikir", "Yohannis", "Tigst"):
        out = to_fidel(spelling)
        assert normalize(out) == out, spelling


# --- contract edges ---------------------------------------------------------


def test_unknown_scheme_raises() -> None:
    with pytest.raises(ValueError, match="unknown scheme"):
        to_fidel("Tesfaye", scheme="bgn_pcgn")


def test_unsegmentable_run_raises() -> None:
    # "x" has no practical-scheme reading (no series romanizes to it).
    with pytest.raises(ValueError, match="cannot transliterate"):
        to_fidel("x")


def test_empty_and_whitespace_return_empty() -> None:
    assert to_fidel("") == ""
    assert to_fidel("   ") == ""


def test_deterministic() -> None:
    assert to_fidel("Yohannis") == to_fidel("Yohannis")
    assert to_fidel("Tsehay Gebremedhin") == to_fidel("Tsehay Gebremedhin")


#: Runs where the fold alone changes the key but the FULL invert round-trip
#: still preserves it, so they cannot live in KNOWN_KEY_EXCEPTIONS (the sweep
#: above asserts exact equality and these pass it). Task 18 wave 1, all three
#: from Yoseph: the h->kh rewrite lands after "p" (yoseph -> yosepkh); the
#: kh->h fold recovers "yoseph", whose "ph" fuses to F in the key, while the
#: raw run keys p + kh split (YSPH) -- key-changing fold, but composing with
#: the inverse table (which keeps p + h split too) cancels the difference.
FOLD_ONLY_KEY_EXCEPTIONS = frozenset({"yosepkh", "yosipkh", "yossepkh"})


def test_fold_run_is_key_neutral_for_the_swept_domain() -> None:
    # The input folds (tz/th/kh/gh) mirror the phonetic key's own digraph
    # folds; outside the pinned exceptions the fold never changes the key.
    for entry in lexicon().given_names:
        for variant in variants(entry.canonical):
            if "/" in variant or "." in variant:
                continue
            for run in _letter_runs(variant):
                if run in KNOWN_KEY_EXCEPTIONS or run in FOLD_ONLY_KEY_EXCEPTIONS:
                    continue
                assert phonetic_key(_fold_run(run)) == phonetic_key(run), run


def test_doctests() -> None:
    results = doctest.testmod(to_fidel_module)
    assert results.attempted > 0
    assert results.failed == 0
