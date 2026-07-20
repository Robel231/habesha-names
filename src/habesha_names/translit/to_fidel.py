"""Latin -> fidel reverse transliteration (practical scheme inverse).

verified: false -- the disambiguation preferences below are agent-chosen
linguistic decisions (informed by the verified lexicon's own fidel, counts
in PROGRESS.md -> Human review queue), pending Robel's native-speaker
review. Nothing in this module hand-types a fidel character: every output
syllable is composed via :func:`habesha_names.fidel.syllable.compose` from
the generated tables, and the inverse surface table is built from the same
``PRACTICAL`` cells that drive the forward direction.

Contract (mirrors how :func:`~habesha_names.translit.to_latin.transliterate`
normalizes first):

- **Lexicon first.** A token recognized as a given-name canonical or
  recorded variant (or a compound prefix / second element spelling)
  returns that entry's STORED conventional fidel verbatim -- including
  homophone series that :func:`~habesha_names.fidel.normalize.normalize`
  would collapse (ፀሐይ, ኃይለ...). Recovering the conventional homophone
  choice is exactly what the lexicon knows and rules cannot.
- **Rule path otherwise.** Unrecognized spellings are inverted onto
  canonical POST-COLLAPSE fidel only: the practical scheme is lossy
  (ሀ/ሐ/ኀ all render "h") and the inverse cannot recover which homophone
  series a writer would choose, so it never guesses one -- collapsed
  series have no rows in ``PRACTICAL`` and therefore cannot be emitted.
  Rule-path output is ``normalize``-stable by construction. The same is
  deliberately NOT true of the lexicon path (its value is the
  conventional spelling), so ``normalize(to_fidel(x)) == to_fidel(x)``
  holds only for rule-path output.

Rule-path pipeline per ASCII-letter run: lowercase -> fold the digraph
romanizations of merged consonants (tz -> ts, th -> t, kh -> h, gh -> h;
the same folds ``match.phonetic`` applies, so the fold is provably
phonetic-key-neutral) -> collapse doubled letters (gemination is unmarked
in fidel) -> best-first segmentation into practical-scheme surfaces ->
compose each candidate and verify it by rendering back through
:func:`transliterate`: the cheapest candidate whose rendering reproduces
the folded run wins; if epenthesis makes an exact rendering impossible
(e.g. "Tigst" renders back as "Tigist"), the cheapest candidate with the
same HabeshaKey wins instead; failing that, the cheapest candidate at
all. A run with no segmentation ("x" has no practical-scheme reading)
raises ``ValueError``.

Ambiguity resolutions (all review-queued linguistic decisions; evidence =
syllable counts over the verified lexicon's own fidel):

- epenthetic "i" vs true vowel: every written vowel is treated as a true
  vowel order (ፊኪር-style spellings, not ፍቅር) -- conventional 6th-order
  spellings come back via the lexicon path only;
- word-final "e" is a true vowel (a word-final 6th order renders bare, so
  it can never produce "e" forward);
- "e" -> order 1 over order 5 (evidence 60:13); "i" -> order 3; "u" -> 2;
  "o" -> 7; "a" -> order 4 after a consonant, glottal አ (order 1) as a
  bare vowel (evidence 15:0); "ha" -> ሃ (h, order 4; evidence 6:5);
- merged consonant series resolve to the unmarked side: k over ቀ/q
  (evidence tied 4:4), t over ጠ, ch over ጨ, p over ጰ, h over ኸ;
- gemination: doubled letters collapse (unmarked in fidel);
- digraph segmentation: handled by the search itself -- ts/sh/ch/gn/zh
  surfaces compete with their letterwise readings and the render check
  rejects wrong splits;
- ua/wa: "Cua" prefers the labialized-velar glyphs of the task-3b
  decision (ኋ/ኳ/ጓ) over the archaic -OA column; "wa" is plain ዋ;
- "i" after a vowel prefers the glide ይ (ወይዘሮ/ሃይለ pattern) over the
  carrier ኢ, except word-finally where ይ renders "y".

Signature note: ARCHITECTURE 4.2 sketches to_fidel as returning ranked
candidates; the v0.2 plan (Task 21) specifies the single-output signature
implemented here. The conflict is logged in PROGRESS.md per protocol.
"""

from __future__ import annotations

import heapq
import re
import unicodedata
from functools import cache, lru_cache

from habesha_names._data import lexicon
from habesha_names.fidel.syllable import compose
from habesha_names.match.phonetic import phonetic_key
from habesha_names.translit.schemes import SCHEMES
from habesha_names.translit.to_latin import transliterate

_VOWELS = frozenset("aeiou")

_LETTER_RUN_RE = re.compile(r"[A-Za-z]+")

#: Digraph romanizations of consonants the practical scheme merges away,
#: folded before segmentation. Each fold is one ``match.phonetic`` already
#: applies (tz/ts -> s, th -> t, kh/gh -> h), so folding cannot change the
#: input's HabeshaKey: "Tzehay" -> "tsehay" (ፀ collapses to ጸ, mirroring
#: normalize), "Bethlehem" -> "betlehem" (ጠ and ተ both render "t").
_INPUT_FOLDS: dict[str, str] = {"tz": "ts", "th": "t", "kh": "h", "gh": "h"}

# Disambiguation costs -- agent-chosen, review-queued (module docstring).
_BASE_COST = 1.0  #: per emitted syllable, so shorter readings win
_GLIDE_I_COST = 0.75  #: "i" after a vowel as glide ይ, preferred over ኢ
_PREFERENCE_BONUS = 0.5  #: subtracted for an explicitly preferred reading

#: Extra cost per consonant series, so unmarked/common series win the
#: merged surfaces (k over q for "k...", t over th, c over ch, p over ph,
#: h over kx) and rare series never beat a letterwise reading ("ngi" is
#: n+g, not the velar-nasal ጝ).
_SERIES_PENALTY: dict[str, float] = {
    "q": 1.0,
    "kw": 1.0,
    "gw": 1.0,
    "xw": 1.0,
    "th": 2.0,
    "ch": 2.0,
    "ph": 2.0,
    "qw": 2.0,
    "kx": 3.0,
    "kxw": 3.0,
    "qhw": 3.0,
    "dd": 3.0,
    "gg": 3.0,
    "ry": 3.0,
    "my": 3.0,
    "fy": 3.0,
    "mw": 3.0,
    "bw": 3.0,
    "fw": 3.0,
    "pw": 3.0,
}

#: Extra cost per vowel order: order 5 loses to order 1 on the shared "e"
#: surfaces (evidence 60:13 across the verified lexicon), and the archaic
#: -OA column (order 8 of plain series: ሇ/ኯ/ጏ) loses to the task-3b
#: labialized-velar glyphs (ኋ/ኳ/ጓ) on the "Cua" surfaces.
_ORDER_PENALTY: dict[int, float] = {5: 0.25, 8: 2.0}

#: Per-surface preferred reading where the generic ranking would pick
#: wrong: "ha" is ሃ (evidence 6:5, and ኃ-family names collapse to ሃ).
_SURFACE_PREFERENCE: dict[str, tuple[str, int]] = {"ha": ("h", 4)}

# Search caps (deterministic; same spirit as translit.variants).
_MAX_POPS = 4096  #: best-first heap pops per run
_CACHE_SIZE = 4096  #: memoized inversions (bounded, like match internals)


def _choice_cost(surface: str, consonant: str, order: int) -> float:
    cost = _BASE_COST + _SERIES_PENALTY.get(consonant, 0.0) + _ORDER_PENALTY.get(order, 0.0)
    if _SURFACE_PREFERENCE.get(surface) == (consonant, order):
        cost -= _PREFERENCE_BONUS
    return cost


@cache
def _inverse_surfaces(scheme: str) -> tuple[dict[str, tuple[tuple[float, str, int], ...]], int]:
    """Surface -> readings as (cost, consonant, order), cheapest first.

    Built from the forward scheme table itself, so the inverse can only
    ever emit post-collapse syllables the forward direction produces. The
    empty surface (bare 6th-order glottal እ renders nothing) is excluded.
    """
    by_surface: dict[str, list[tuple[float, str, int]]] = {}
    for (consonant, order), surface in SCHEMES[scheme].items():
        if surface:
            by_surface.setdefault(surface, []).append(
                (_choice_cost(surface, consonant, order), consonant, order)
            )
    ranked = {surface: tuple(sorted(options)) for surface, options in by_surface.items()}
    return ranked, max(len(surface) for surface in ranked)


@cache
def _lexicon_fidel() -> dict[str, str]:
    """Lowercased recognized spelling -> stored conventional fidel.

    Given-name entries take priority, then compound prefixes, then second
    elements (same precedence as ``translit.variants``' spelling groups).
    """
    forms: dict[str, str] = {}
    lex = lexicon()
    for entry in lex.given_names:
        for spelling in (entry.canonical, *entry.variants):
            forms.setdefault(spelling.lower(), entry.fidel)
    for prefix in lex.compound_prefixes:
        for spelling in (prefix.latin, *prefix.variants):
            forms.setdefault(spelling.lower(), prefix.fidel)
    for second in lex.compound_seconds:
        for spelling in (second.latin, *second.variants):
            forms.setdefault(spelling.lower(), second.fidel)
    return forms


def _fold_run(run: str) -> str:
    """Lowercase run -> folded, degeminated form the search inverts."""
    folded: list[str] = []
    i = 0
    while i < len(run):
        pair = run[i : i + 2]
        if pair in _INPUT_FOLDS:
            folded.append(_INPUT_FOLDS[pair])
            i += 2
        else:
            folded.append(run[i])
            i += 1
    text = "".join(folded)
    return "".join(ch for i, ch in enumerate(text) if i == 0 or ch != text[i - 1])


@lru_cache(maxsize=_CACHE_SIZE)
def _invert_run(run: str, scheme: str) -> str:
    """Rule-based inverse for one lowercase ASCII-letter run.

    Best-first search over segmentations into practical-scheme surfaces;
    every complete candidate is composed and verified by rendering back
    through :func:`transliterate`. Preference order: cheapest exact
    rendering, else cheapest same-HabeshaKey rendering, else cheapest
    candidate. Raises ``ValueError`` when no segmentation exists.
    """
    surfaces, max_len = _inverse_surfaces(scheme)
    folded = _fold_run(run)
    target_key = phonetic_key(folded)
    heap: list[tuple[float, int, tuple[tuple[str, int], ...]]] = [(0.0, 0, ())]
    pops = 0
    key_match: str | None = None
    fallback: str | None = None
    while heap and pops < _MAX_POPS:
        cost, pos, choices = heapq.heappop(heap)
        pops += 1
        if pos == len(folded):
            fidel = "".join(compose(consonant, order) for consonant, order in choices)
            rendered = transliterate(fidel, scheme).lower()
            if rendered == folded:
                return fidel
            if key_match is None and phonetic_key(fidel) == target_key:
                key_match = fidel
            if fallback is None:
                fallback = fidel
            continue
        for length in range(min(max_len, len(folded) - pos), 0, -1):
            options = surfaces.get(folded[pos : pos + length])
            if options is None:
                continue
            for option_cost, consonant, order in options:
                heapq.heappush(
                    heap, (cost + option_cost, pos + length, (*choices, (consonant, order)))
                )
        if folded[pos] == "i" and 0 < pos < len(folded) - 1 and folded[pos - 1] in _VOWELS:
            # Medial "i" after a vowel: glide ይ (ሃይለ), cheaper than ኢ.
            # Word-final ይ renders "y", so the option stops before the end.
            heapq.heappush(heap, (cost + _GLIDE_I_COST, pos + 1, (*choices, ("y", 6))))
    if key_match is not None:
        return key_match
    if fallback is not None:
        return fallback
    raise ValueError(f"cannot transliterate {run!r} to fidel (scheme {scheme!r})")


def _convert_token(token: str, scheme: str) -> str:
    parts: list[str] = []
    pos = 0
    for found in _LETTER_RUN_RE.finditer(token):
        parts.append(token[pos : found.start()])
        run = found.group().lower()
        stored = _lexicon_fidel().get(run)
        parts.append(stored if stored is not None else _invert_run(run, scheme))
        pos = found.end()
    parts.append(token[pos:])
    return "".join(parts)


def to_fidel(latin: str, scheme: str = "practical") -> str:
    """Transliterate a Latin-spelled name to fidel (Ethiopic script).

    Lexicon-first: a spelling recognized as a given-name canonical or
    recorded variant (or a compound prefix / second element) returns that
    entry's stored conventional fidel -- homophone series included, which
    is exactly what rules cannot recover. Anything else is inverted by
    rule onto canonical post-collapse fidel: the result is
    ``normalize``-stable and keeps the input's phonetic key, but it is a
    phonetic spelling, not necessarily the conventional one (ዮሃኒስ for
    "Yohannis", where convention writes ዮሐንስ).

    Whitespace-separated tokens are converted independently; characters
    outside A-Z (hyphens, digits, fidel) pass through unchanged. Raises
    ``ValueError`` for an unknown ``scheme`` or for a letter run with no
    practical-scheme reading (e.g. a bare "x").

    >>> to_fidel("Tsehay")
    'ፀሐይ'
    >>> to_fidel("Tsehay") == to_fidel("tsehai")  # recognized variant
    True
    >>> to_fidel("Gebre-Medhin")  # given-name entry wins the spelling
    'ገብሬ-መድህን'
    >>> transliterate(to_fidel("Yohannis"))  # rule path keeps the sound
    'Yohanis'
    """
    if scheme not in SCHEMES:
        known = ", ".join(sorted(SCHEMES))
        raise ValueError(f"unknown scheme {scheme!r} (known: {known})")
    text = unicodedata.normalize("NFC", latin)
    return " ".join(_convert_token(token, scheme) for token in text.split())
