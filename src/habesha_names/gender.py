"""Probabilistic gender inference from the given name (ARCHITECTURE 3, v0.2).

:func:`guess_gender` parses the input with the normal parser and looks up
the **given** token only against the lexicon gender distributions
(``given_names.json``, ARCHITECTURE 4.5). Habesha names are patronymic:
the second and third tokens are the father's and grandfather's given
names, so they are evidence about *those* people, never about the bearer
-- they are deliberately ignored (and noted).

Lookup runs in three tiers of descending confidence (IMPLEMENTATION_PLAN_V02
Task 20):

1. **exact** -- the token is an entry's canonical Latin spelling or its
   fidel form (compared after ``normalize``, so homophone spellings hit).
2. **variant** -- the token is one of an entry's recorded alternate
   spellings (native-speaker reviewed, same name by authorship).
3. **phonetic key** -- the token's HabeshaKey equals an entry spelling's
   key. Weakest: a key unifies plausible romanizations, so it can reach a
   *different* name that merely sounds alike (e.g. Maram would key like a
   Mariam entry).

The returned confidence is ``tier constant x P(majority gender)`` from the
matched entry's distribution -- e.g. an exact hit on an entry with
``{"f": 0.97, "m": 0.03}`` yields ``('f', 0.9 * 0.97)``. If several
entries match at the winning tier (legitimately possible: distinct names
may share a phonetic key, Bekele/Bikila-style), agreement uses the most
conservative probability; disagreement or a balanced distribution returns
``('unknown', 0.0)`` with the conflict noted. No lexicon hit at any tier
returns ``('unknown', 0.0)`` honestly -- this function never guesses from
spelling shape.

The tier constants below are agent-invented magnitudes, not measured
priors (verified: false; PROGRESS.md review queue).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Literal

from habesha_names._data import GivenName, lexicon
from habesha_names.fidel.normalize import normalize
from habesha_names.match.phonetic import phonetic_key
from habesha_names.parse.parser import parse

Gender = Literal["f", "m", "unknown"]

#: Lookup-tier confidence scales -- agent-chosen heuristics (verified:
#: false; PROGRESS.md review queue). Ordering is the plan's contract
#: (exact > variant > key); the magnitudes are not. The variant tier sits
#: ABOVE the key tier because a recorded variant is native-speaker-reviewed
#: "same name" evidence, while a key match may bridge to a different name
#: that sounds alike.
_CONFIDENCE_EXACT = 0.9
_CONFIDENCE_VARIANT = 0.8
_CONFIDENCE_KEY = 0.6


@dataclass(frozen=True)
class GenderGuess:
    """Gender evidence for the bearer of a name (ARCHITECTURE 4.5 data).

    ``confidence`` is 0.0 whenever ``gender`` is ``"unknown"``; otherwise
    it is the lookup tier's constant scaled by the matched entry's majority
    probability, in (0, 1]. ``notes`` records every decision: the given
    token used, ignored patronym/avonym tokens, the matched entries with
    their distributions, or the honest miss.
    """

    gender: Gender
    confidence: float
    notes: list[str]


def _majority(distribution: dict[str, float]) -> tuple[Literal["f", "m"] | None, float]:
    """Majority gender and its probability; ``(None, p)`` on an exact tie."""
    f = distribution.get("f", 0.0)
    m = distribution.get("m", 0.0)
    if f > m:
        return "f", f
    if m > f:
        return "m", m
    return None, f


def _add(index: dict[str, list[GivenName]], key: str, entry: GivenName) -> None:
    if key:
        bucket = index.setdefault(key, [])
        if entry not in bucket:
            bucket.append(entry)


@cache
def _exact_index() -> dict[str, tuple[GivenName, ...]]:
    """Lowercased canonical + normalized fidel -> entries (file order)."""
    index: dict[str, list[GivenName]] = {}
    for entry in lexicon().given_names:
        _add(index, entry.canonical.lower(), entry)
        _add(index, normalize(entry.fidel), entry)
    return {key: tuple(entries) for key, entries in index.items()}


@cache
def _variant_index() -> dict[str, tuple[GivenName, ...]]:
    """Lowercased recorded variant spelling -> entries (file order)."""
    index: dict[str, list[GivenName]] = {}
    for entry in lexicon().given_names:
        for variant in entry.variants:
            _add(index, variant.lower(), entry)
    return {key: tuple(entries) for key, entries in index.items()}


@cache
def _key_index() -> dict[str, tuple[GivenName, ...]]:
    """HabeshaKey over every recognized spelling -> entries (file order)."""
    index: dict[str, list[GivenName]] = {}
    for entry in lexicon().given_names:
        for spelling in (entry.canonical, *entry.variants, entry.fidel):
            _add(index, phonetic_key(spelling), entry)
    return {key: tuple(entries) for key, entries in index.items()}


def _decide(
    entries: tuple[GivenName, ...], tier: float, how: str, notes: list[str]
) -> GenderGuess:
    """Resolve the matched entries' distributions into one guess."""
    majorities: list[tuple[Literal["f", "m"] | None, float]] = []
    for entry in entries:
        evidence = " / ".join(f"{g} {p:g}" for g, p in sorted(entry.gender.items()))
        notes.append(f"matched lexicon entry {entry.canonical!r} ({how}; gender {evidence})")
        majorities.append(_majority(entry.gender))
    gender = majorities[0][0]
    if gender is None or any(other != gender for other, _ in majorities):
        notes.append("gender evidence is balanced or conflicting across matches")
        return GenderGuess(gender="unknown", confidence=0.0, notes=notes)
    confidence = tier * min(probability for _, probability in majorities)
    return GenderGuess(gender=gender, confidence=confidence, notes=notes)


def guess_gender(name: str) -> GenderGuess:
    """Guess the bearer's gender from the given name, via the lexicon.

    Parses ``name`` (title stripping, comma inversion, compound joining,
    fidel or Latin) and looks up the given token only -- patronym and
    avonym tokens are ignored, they describe the father and grandfather.
    Lookup tiers: exact spelling, recorded variant, phonetic key
    (descending confidence). Without a lexicon hit the answer is
    ``('unknown', 0.0)`` -- honestly, never a guess from spelling shape.
    Raises ``ValueError`` when no name tokens remain after normalization
    (same contract as :func:`~habesha_names.parse.parser.parse`).

    >>> guess = guess_gender("Ato Abebe Bikila")
    >>> (guess.gender, guess.confidence)
    ('m', 0.9)
    >>> guess_gender("ፀሐይ ገብረመድህን").gender
    'f'
    >>> guess_gender("Tesfai").gender  # recorded variant of Tesfaye
    'm'
    >>> unknown = guess_gender("Maram")  # not in the lexicon
    >>> (unknown.gender, unknown.confidence)
    ('unknown', 0.0)
    """
    parsed = parse(name)
    given = parsed.given
    notes = [f"evidence: given name {given!r} only"]
    for role, value in (("patronym", parsed.patronym), ("avonym", parsed.avonym)):
        if value is not None:
            notes.append(f"{role} {value!r} ignored (not evidence about the bearer)")
    lookup = normalize(given).lower()
    key = phonetic_key(given)
    tiers: tuple[tuple[tuple[GivenName, ...] | None, float, str], ...] = (
        (_exact_index().get(lookup), _CONFIDENCE_EXACT, "exact spelling"),
        (_variant_index().get(lookup), _CONFIDENCE_VARIANT, "recorded variant spelling"),
        (_key_index().get(key) if key else None, _CONFIDENCE_KEY, f"phonetic key {key!r}"),
    )
    for entries, tier, how in tiers:
        if entries:
            return _decide(entries, tier, how, notes)
    notes.append(f"no lexicon entry matches {given!r} (exact, variant, or phonetic key)")
    return GenderGuess(gender="unknown", confidence=0.0, notes=notes)
