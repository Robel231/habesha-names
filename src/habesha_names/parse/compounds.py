"""Compound given-name detection and slash-abbreviation expansion.

Habesha compound given names ("Hailemariam", "Gebremedhin") are a known
prefix (ገብረ Gebre-, ኃይለ Haile-, ...) plus a second element (ማርያም -Mariam,
መድህን -Medhin, ...), written joined, spaced, or slash-abbreviated
("G/Medhin", "G.Medhin") -- ARCHITECTURE 4.3. This module detects all three
forms against the packaged lexicon:

- :func:`split_joined` -- one token that is prefix + second element.
- :func:`match_pair` -- two adjacent tokens forming prefix + second element.
- :func:`expand_abbreviation` -- "G/Medhin"-style single-letter abbreviation,
  expanded via the weighted candidates in ``compounds.json``. The top-weight
  candidate is applied; every candidate is recorded in the returned note so
  downstream consumers (and auditors) can see what was chosen over what.

Latin forms are matched case-insensitively; fidel forms are compared after
:func:`~habesha_names.fidel.normalize.normalize`, so homophone spellings
behave identically. Indexes are built lazily from the lexicon on first use;
this module holds no other state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

from habesha_names._data import CompoundPrefix, CompoundSecond, lexicon
from habesha_names.fidel.normalize import normalize
from habesha_names.fidel.syllable import is_ethiopic

#: "G/Medhin" / "G.Medhin": one ASCII letter, a slash or period, a remainder.
_ABBREVIATION_RE = re.compile(r"^([A-Za-z])[/.](.+)$")


@dataclass(frozen=True)
class CompoundMatch:
    """A detected prefix + second-element compound."""

    prefix: CompoundPrefix
    second: CompoundSecond
    joined: str  #: canonical joined form, in the script of the matched input


@dataclass(frozen=True)
class Expansion:
    """A slash-abbreviation expansion (top-weight candidate applied)."""

    tokens: tuple[str, ...]  #: replacement token(s)
    is_compound: bool  #: True when the replacement is one joined compound
    confidence: float  #: lexicon weight of the chosen candidate
    note: str  #: human-readable record including every candidate


@cache
def _prefix_keys() -> tuple[tuple[str, CompoundPrefix], ...]:
    """(lookup key, prefix) pairs in file order: lowercased Latin + normalized fidel."""
    pairs: list[tuple[str, CompoundPrefix]] = []
    for prefix in lexicon().compound_prefixes:
        pairs.append((prefix.latin.lower(), prefix))
        pairs.append((normalize(prefix.fidel), prefix))
    return tuple(pairs)


@cache
def _prefix_index() -> dict[str, CompoundPrefix]:
    index: dict[str, CompoundPrefix] = {}
    for key, prefix in _prefix_keys():
        index.setdefault(key, prefix)
    return index


@cache
def _second_index() -> dict[str, CompoundSecond]:
    index: dict[str, CompoundSecond] = {}
    for second in lexicon().compound_seconds:
        index.setdefault(second.latin.lower(), second)
        index.setdefault(normalize(second.fidel), second)
    return index


@cache
def _abbreviation_index() -> dict[str, tuple[tuple[str, float], ...]]:
    return {entry.abbrev.lower(): entry.candidates for entry in lexicon().abbreviations}


def _joined_form(prefix: CompoundPrefix, second: CompoundSecond, sample: str) -> str:
    """Canonical joined form, in the script of ``sample`` (a matched input token)."""
    if is_ethiopic(sample):
        return normalize(prefix.fidel) + normalize(second.fidel)
    return prefix.latin + second.latin.lower()


def split_joined(token: str) -> CompoundMatch | None:
    """Detect a single token that is an already-joined compound.

    >>> match = split_joined("Hailemariam")
    >>> (match.prefix.latin, match.second.latin)
    ('Haile', 'Mariam')
    >>> split_joined("Tesfaye") is None
    True
    """
    key = normalize(token).lower()
    for prefix_key, prefix in _prefix_keys():
        if len(key) > len(prefix_key) and key.startswith(prefix_key):
            second = _second_index().get(key[len(prefix_key) :])
            if second is not None:
                return CompoundMatch(prefix, second, _joined_form(prefix, second, token))
    return None


def match_pair(first: str, second: str) -> CompoundMatch | None:
    """Detect a spaced compound written as two adjacent tokens.

    >>> match_pair("Haile", "Mariam").joined
    'Hailemariam'
    >>> match_pair("Abebe", "Bikila") is None
    True
    """
    prefix = _prefix_index().get(normalize(first).lower())
    element = _second_index().get(normalize(second).lower())
    if prefix is None or element is None:
        return None
    return CompoundMatch(prefix, element, _joined_form(prefix, element, first))


def expand_abbreviation(token: str) -> Expansion | None:
    """Expand a "G/Medhin"-style slash abbreviation via the lexicon.

    The single letter must be a known abbreviation and the remainder a known
    second element; anything else returns ``None`` (in particular title
    abbreviations like "W/ro" never expand here). The top-weight candidate
    is applied: a compound-prefix candidate yields one joined token, a
    given-name candidate stays a separate token ahead of the second element.

    >>> expansion = expand_abbreviation("G/Medhin")
    >>> expansion.tokens
    ('Gebremedhin',)
    >>> expansion.confidence
    0.8
    >>> expand_abbreviation("W/ro") is None
    True
    """
    matched = _ABBREVIATION_RE.match(token)
    if matched is None:
        return None
    letter, remainder = matched.group(1), matched.group(2)
    candidates = _abbreviation_index().get(letter.lower())
    element = _second_index().get(normalize(remainder).lower())
    if candidates is None or element is None:
        return None
    chosen, weight = candidates[0]
    prefix = _prefix_index().get(chosen.lower())
    if prefix is not None:
        tokens: tuple[str, ...] = (_joined_form(prefix, element, remainder),)
    else:
        tokens = (chosen, element.latin)
    listed = ", ".join(f"{name} ({value:g})" for name, value in candidates)
    note = f"abbreviation {token!r} expanded with top candidate {chosen!r} (candidates: {listed})"
    return Expansion(tokens=tokens, is_compound=prefix is not None, confidence=weight, note=note)
