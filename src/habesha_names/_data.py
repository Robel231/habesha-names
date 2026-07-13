"""Lazy, validated loader for the packaged lexicon data.

The JSON files under ``habesha_names/data/`` are reviewable linguistic
assets, not code (ARCHITECTURE 2, 4.5): agent-seeded entries ship
``"verified": false`` until Robel (native speaker) reviews them — the
contracts and workflow live in ``data/schema.md``. This module is the only
stateful component in the library: :func:`lexicon` reads the files once, on
first call, via ``importlib.resources`` and returns a frozen singleton.

Validation is strict and happens entirely at load time: wrong or extra
keys, bad types, non-Ethiopic ``fidel`` values, duplicate entries, and
gender/weight distributions that do not sum to 1 all raise
:class:`LexiconError` immediately, so malformed data can never leak into
parsing or matching.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any, NoReturn

from habesha_names.fidel.syllable import is_ethiopic

_PACKAGE = "habesha_names.data"
_SCHEMA_VERSION = 1

_GENDERS = frozenset({"f", "m"})
_TITLE_CATEGORIES = frozenset({"civil", "academic", "professional", "religious"})
_ORIGINS = frozenset({"amharic", "tigrinya", "geez", "arabic", "biblical", "oromo"})
_FREQ_TIERS = frozenset({1, 2, 3})
_SUM_TOLERANCE = 1e-6


class LexiconError(ValueError):
    """A packaged data file is malformed (see ``data/schema.md``)."""


@dataclass(frozen=True)
class Title:
    """A title/honorific that may precede a name (Ato, W/ro, Dr, ...)."""

    canonical: str
    abbreviations: tuple[str, ...]
    fidel: tuple[str, ...]
    gender: str | None  # "m" | "f" | None (not gendered)
    category: str  # civil | academic | professional | religious
    verified: bool


@dataclass(frozen=True)
class CompoundPrefix:
    """First element of a compound given name (Gebre-, Haile-, ...)."""

    latin: str
    fidel: str
    gender: str | None
    verified: bool


@dataclass(frozen=True)
class CompoundSecond:
    """Second element of a compound given name (-Mariam, -Medhin, ...)."""

    latin: str
    fidel: str
    verified: bool


@dataclass(frozen=True)
class AbbreviationExpansion:
    """Slash-abbreviation letter with weighted expansions (G/ -> Gebre, Girma)."""

    abbrev: str
    candidates: tuple[tuple[str, float], ...]  # (expansion, weight), weight non-increasing
    verified: bool


@dataclass(frozen=True)
class GivenName:
    """One lexicon entry, per the ARCHITECTURE 4.5 contract."""

    fidel: str
    canonical: str
    variants: tuple[str, ...]
    gender: dict[str, float]  # probability over {"f", "m"}, sums to 1
    origin: str
    freq_tier: int
    verified: bool


@dataclass(frozen=True)
class Lexicon:
    """All packaged lexicon data, loaded and validated."""

    titles: tuple[Title, ...]
    compound_prefixes: tuple[CompoundPrefix, ...]
    compound_seconds: tuple[CompoundSecond, ...]
    abbreviations: tuple[AbbreviationExpansion, ...]
    given_names: tuple[GivenName, ...]


def _fail(filename: str, where: str, message: str) -> NoReturn:
    raise LexiconError(f"{filename}: {where}: {message}")


def _entry(value: Any, keys: frozenset[str], filename: str, where: str) -> dict[str, Any]:
    """Require a JSON object with exactly ``keys`` (typo safety for hand-edited data)."""
    if not isinstance(value, dict):
        _fail(filename, where, f"expected an object, got {type(value).__name__}")
    missing = sorted(keys - value.keys())
    extra = sorted(value.keys() - keys)
    if missing or extra:
        _fail(filename, where, f"missing keys {missing}, unexpected keys {extra}")
    return value


def _string(entry: dict[str, Any], key: str, filename: str, where: str) -> str:
    value = entry[key]
    if not isinstance(value, str) or not value:
        _fail(filename, where, f"{key!r} must be a non-empty string")
    return value


def _bool(entry: dict[str, Any], key: str, filename: str, where: str) -> bool:
    value = entry[key]
    if not isinstance(value, bool):
        _fail(filename, where, f"{key!r} must be a boolean")
    return value


def _latin_name(value: str, filename: str, where: str, *, extra_chars: str = "") -> str:
    if not all(("a" <= ch.lower() <= "z") or ch in extra_chars for ch in value):
        _fail(filename, where, f"non-ASCII-letter character in Latin form {value!r}")
    return value


def _fidel_text(value: str, filename: str, where: str, *, allow_slash: bool = False) -> str:
    checked = value.replace("/", "") if allow_slash else value
    if not is_ethiopic(checked):
        _fail(filename, where, f"{value!r} is not Ethiopic script")
    if unicodedata.normalize("NFC", value) != value:
        _fail(filename, where, f"{value!r} is not NFC-normalized")
    return value


def _optional_gender(entry: dict[str, Any], filename: str, where: str) -> str | None:
    value = entry["gender"]
    if value is None:
        return None
    if not isinstance(value, str) or value not in _GENDERS:
        _fail(filename, where, f"'gender' must be 'f', 'm', or null, got {value!r}")
    return value


def _string_list(entry: dict[str, Any], key: str, filename: str, where: str) -> tuple[str, ...]:
    value = entry[key]
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        _fail(filename, where, f"{key!r} must be a list of non-empty strings")
    if len({item.lower() for item in value}) != len(value):
        _fail(filename, where, f"duplicate values in {key!r}")
    return tuple(value)


def _unique(values: list[str], filename: str, what: str) -> None:
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            _fail(filename, what, f"duplicate entry {value!r}")
        seen.add(key)


def _root(data: Any, keys: frozenset[str], filename: str) -> dict[str, Any]:
    root = _entry(data, keys | {"schema"}, filename, "top level")
    if root["schema"] != _SCHEMA_VERSION:
        _fail(filename, "top level", f"unsupported schema version {root['schema']!r}")
    return root


def _entries(root: dict[str, Any], key: str, filename: str) -> list[Any]:
    value = root[key]
    if not isinstance(value, list) or not value:
        _fail(filename, "top level", f"{key!r} must be a non-empty list")
    return value


_TITLE_KEYS = frozenset({"canonical", "abbreviations", "fidel", "gender", "category", "verified"})


def _parse_titles(data: Any, filename: str = "titles.json") -> tuple[Title, ...]:
    root = _root(data, frozenset({"entries"}), filename)
    titles: list[Title] = []
    for raw in _entries(root, "entries", filename):
        entry = _entry(raw, _TITLE_KEYS, filename, "title entry")
        canonical = _string(entry, "canonical", filename, "title entry")
        where = f"title {canonical!r}"
        _latin_name(canonical, filename, where)
        abbreviations = _string_list(entry, "abbreviations", filename, where)
        for form in abbreviations:
            _latin_name(form, filename, where, extra_chars="/.")
        fidel = _string_list(entry, "fidel", filename, where)
        if not fidel:
            _fail(filename, where, "'fidel' must list at least one form")
        for form in fidel:
            _fidel_text(form, filename, where, allow_slash=True)
        category = _string(entry, "category", filename, where)
        if category not in _TITLE_CATEGORIES:
            _fail(filename, where, f"unknown category {category!r}")
        titles.append(
            Title(
                canonical=canonical,
                abbreviations=abbreviations,
                fidel=fidel,
                gender=_optional_gender(entry, filename, where),
                category=category,
                verified=_bool(entry, "verified", filename, where),
            )
        )
    _unique([t.canonical for t in titles], filename, "titles")
    return tuple(titles)


_PREFIX_KEYS = frozenset({"latin", "fidel", "gender", "verified"})
_SECOND_KEYS = frozenset({"latin", "fidel", "verified"})
_ABBREV_KEYS = frozenset({"abbrev", "candidates", "verified"})
_CANDIDATE_KEYS = frozenset({"expansion", "weight"})

_Compounds = tuple[
    tuple[CompoundPrefix, ...],
    tuple[CompoundSecond, ...],
    tuple[AbbreviationExpansion, ...],
]


def _parse_candidates(
    entry: dict[str, Any], filename: str, where: str
) -> tuple[tuple[str, float], ...]:
    raw = entry["candidates"]
    if not isinstance(raw, list) or not raw:
        _fail(filename, where, "'candidates' must be a non-empty list")
    candidates: list[tuple[str, float]] = []
    for item in raw:
        candidate = _entry(item, _CANDIDATE_KEYS, filename, where)
        expansion = _string(candidate, "expansion", filename, where)
        _latin_name(expansion, filename, where)
        weight = candidate["weight"]
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or not 0 < weight <= 1:
            _fail(filename, where, f"weight for {expansion!r} must be a number in (0, 1]")
        candidates.append((expansion, float(weight)))
    weights = [weight for _, weight in candidates]
    if abs(sum(weights) - 1.0) > _SUM_TOLERANCE:
        _fail(filename, where, f"candidate weights sum to {sum(weights)}, expected 1.0")
    if weights != sorted(weights, reverse=True):
        _fail(filename, where, "candidates must be listed in non-increasing weight order")
    _unique([expansion for expansion, _ in candidates], filename, where)
    return tuple(candidates)


def _parse_compounds(data: Any, filename: str = "compounds.json") -> _Compounds:
    root = _root(
        data, frozenset({"prefixes", "second_elements", "abbreviation_expansions"}), filename
    )
    prefixes: list[CompoundPrefix] = []
    for raw in _entries(root, "prefixes", filename):
        entry = _entry(raw, _PREFIX_KEYS, filename, "prefix entry")
        latin = _string(entry, "latin", filename, "prefix entry")
        where = f"prefix {latin!r}"
        prefixes.append(
            CompoundPrefix(
                latin=_latin_name(latin, filename, where),
                fidel=_fidel_text(_string(entry, "fidel", filename, where), filename, where),
                gender=_optional_gender(entry, filename, where),
                verified=_bool(entry, "verified", filename, where),
            )
        )
    seconds: list[CompoundSecond] = []
    for raw in _entries(root, "second_elements", filename):
        entry = _entry(raw, _SECOND_KEYS, filename, "second-element entry")
        latin = _string(entry, "latin", filename, "second-element entry")
        where = f"second element {latin!r}"
        seconds.append(
            CompoundSecond(
                latin=_latin_name(latin, filename, where),
                fidel=_fidel_text(_string(entry, "fidel", filename, where), filename, where),
                verified=_bool(entry, "verified", filename, where),
            )
        )
    abbreviations: list[AbbreviationExpansion] = []
    for raw in _entries(root, "abbreviation_expansions", filename):
        entry = _entry(raw, _ABBREV_KEYS, filename, "abbreviation entry")
        abbrev = _string(entry, "abbrev", filename, "abbreviation entry")
        where = f"abbreviation {abbrev!r}"
        _latin_name(abbrev, filename, where)
        abbreviations.append(
            AbbreviationExpansion(
                abbrev=abbrev,
                candidates=_parse_candidates(entry, filename, where),
                verified=_bool(entry, "verified", filename, where),
            )
        )
    _unique([p.latin for p in prefixes], filename, "prefixes")
    _unique([s.latin for s in seconds], filename, "second_elements")
    _unique([a.abbrev for a in abbreviations], filename, "abbreviation_expansions")
    return tuple(prefixes), tuple(seconds), tuple(abbreviations)


_GIVEN_KEYS = frozenset(
    {"fidel", "canonical", "variants", "gender", "origin", "freq_tier", "verified"}
)


def _parse_gender_distribution(
    entry: dict[str, Any], filename: str, where: str
) -> dict[str, float]:
    raw = entry["gender"]
    if not isinstance(raw, dict) or not raw:
        _fail(filename, where, "'gender' must be a non-empty object")
    distribution: dict[str, float] = {}
    for key, value in raw.items():
        if key not in _GENDERS:
            _fail(filename, where, f"unknown gender key {key!r}")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value <= 1:
            _fail(filename, where, f"gender weight for {key!r} must be a number in (0, 1]")
        distribution[key] = float(value)
    total = sum(distribution.values())
    if abs(total - 1.0) > _SUM_TOLERANCE:
        _fail(filename, where, f"gender weights sum to {total}, expected 1.0")
    return distribution


def _parse_given_names(data: Any, filename: str = "given_names.json") -> tuple[GivenName, ...]:
    root = _root(data, frozenset({"entries"}), filename)
    names: list[GivenName] = []
    for raw in _entries(root, "entries", filename):
        entry = _entry(raw, _GIVEN_KEYS, filename, "given-name entry")
        canonical = _string(entry, "canonical", filename, "given-name entry")
        where = f"given name {canonical!r}"
        _latin_name(canonical, filename, where)
        variants = _string_list(entry, "variants", filename, where)
        for variant in variants:
            _latin_name(variant, filename, where)
            if variant.lower() == canonical.lower():
                _fail(filename, where, f"variant {variant!r} repeats the canonical form")
        origin = _string(entry, "origin", filename, where)
        if origin not in _ORIGINS:
            _fail(filename, where, f"unknown origin {origin!r}")
        freq_tier = entry["freq_tier"]
        if isinstance(freq_tier, bool) or freq_tier not in _FREQ_TIERS:
            _fail(filename, where, f"'freq_tier' must be one of {sorted(_FREQ_TIERS)}")
        names.append(
            GivenName(
                fidel=_fidel_text(_string(entry, "fidel", filename, where), filename, where),
                canonical=canonical,
                variants=variants,
                gender=_parse_gender_distribution(entry, filename, where),
                origin=origin,
                freq_tier=freq_tier,
                verified=_bool(entry, "verified", filename, where),
            )
        )
    _unique([n.canonical for n in names], filename, "given-name canonicals")
    _unique([n.fidel for n in names], filename, "given-name fidel forms")
    return tuple(names)


def _check_cross_references(
    prefixes: tuple[CompoundPrefix, ...],
    given_names: tuple[GivenName, ...],
    abbreviations: tuple[AbbreviationExpansion, ...],
) -> None:
    """Every abbreviation expansion must resolve to known lexicon data."""
    known = {p.latin for p in prefixes} | {n.canonical for n in given_names}
    for expansion in abbreviations:
        for candidate, _ in expansion.candidates:
            if candidate not in known:
                _fail(
                    "compounds.json",
                    f"abbreviation {expansion.abbrev!r}",
                    f"expansion {candidate!r} is neither a known prefix "
                    "nor a known given name",
                )


def _read(filename: str) -> Any:
    text = resources.files(_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise LexiconError(f"{filename}: invalid JSON: {error}") from error


@cache
def lexicon() -> Lexicon:
    """Load, validate, and cache the packaged lexicon (lazy singleton).

    The data files are read on the first call only; later calls return the
    same frozen :class:`Lexicon` object. Raises :class:`LexiconError` if any
    file violates the contracts in ``data/schema.md``.

    >>> lex = lexicon()
    >>> lexicon() is lex
    True
    >>> any(title.canonical == "Ato" for title in lex.titles)
    True
    >>> any(name.canonical == "Tsehay" for name in lex.given_names)
    True
    """
    titles = _parse_titles(_read("titles.json"))
    prefixes, seconds, abbreviations = _parse_compounds(_read("compounds.json"))
    given_names = _parse_given_names(_read("given_names.json"))
    _check_cross_references(prefixes, given_names, abbreviations)
    return Lexicon(
        titles=titles,
        compound_prefixes=prefixes,
        compound_seconds=seconds,
        abbreviations=abbreviations,
        given_names=given_names,
    )
