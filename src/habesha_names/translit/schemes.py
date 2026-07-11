"""Transliteration scheme tables (fidel -> Latin).

verified: false -- EVERY Latin value in this module is unreviewed linguistic
data chosen by a non-native-speaker agent. Each non-obvious choice is listed
in PROGRESS.md -> Human review queue with the alternatives considered; Robel
decides the finals. Do not treat these defaults as authoritative.

The ``PRACTICAL`` scheme is the workhorse (ARCHITECTURE 4.2): how Ethiopians
actually romanize names -- ASCII only, no diacritics, lossy on purpose
(e.g. both the ejective and plain series may share one Latin form).

Contract: :func:`habesha_names.translit.to_latin.transliterate` calls
:func:`habesha_names.fidel.normalize.normalize` first, unconditionally.
Therefore this table defines cells ONLY for post-collapse consonant series:
the homophone sources (hh ሐ, x ኀ, sz ሠ, tz ፀ, pharyngeal ዐ) can never reach
the table and deliberately have no rows.

The table is keyed ``(consonant label, vowel order) -> Latin`` and is built
at import time from the generated ``fidel.tables`` (labels and the set of
existing syllables come from Unicode data; nothing here is a hand-typed
fidel<->codepoint pair). Sixth-order cells hold the bare consonant; the
context-dependent epenthetic vowel is applied by ``to_latin`` (see there).
"""

from __future__ import annotations

from habesha_names.fidel.normalize import HOMOPHONE_SERIES
from habesha_names.fidel.tables import SYLLABLES

#: Latin onset per post-collapse consonant series label.
#: verified: false -- agent defaults, see PROGRESS.md human review queue.
_CONSONANTS: dict[str, str] = {
    "h": "h",
    "l": "l",
    "m": "m",
    "r": "r",
    "s": "s",
    "sh": "sh",
    "q": "k",  # ቀ: practical usage favors k (Kenenisa); review queue: q vs k
    "qw": "kw",  # follows the q->k default
    "qh": "q",  # ቐ (Tigrinya): review queue
    "qhw": "qw",
    "b": "b",
    "v": "v",
    "t": "t",
    "c": "ch",  # ቸ: collides with ጨ by design; review queue
    "xw": "hw",  # ኈ (x collapses to h, xw is not collapsed); review queue
    "n": "n",
    "ny": "gn",  # ኘ: review queue: gn vs ny
    "glottal": "",  # አ carries only its vowel
    "k": "k",
    "kw": "kw",
    "kx": "h",  # ኸ: review queue: h vs kh
    "kxw": "hw",
    "w": "w",
    "z": "z",
    "zh": "zh",  # ዠ: review queue: zh vs j
    "y": "y",
    "d": "d",
    "dd": "dh",  # ዸ (rare, Oromo dh): review queue
    "j": "j",
    "g": "g",
    "gw": "gw",
    "gg": "ng",  # ጘ (velar nasal, rare): review queue
    "th": "t",  # ጠ ejective: practical drops the distinction (Taitu)
    "ch": "ch",  # ጨ ejective: collides with ቸ by design; review queue
    "ph": "p",  # ጰ ejective: practical drops the distinction (Paulos)
    "ts'": "ts",  # ጸ: review queue: ts vs s vs tz
    "f": "f",
    "p": "p",
    "ry": "ry",  # ፘ ⁄ ፙ ⁄ ፚ: rare one-off syllables; review queue
    "my": "my",
    "fy": "fy",
    "mw": "mw",  # Sebatbeit supplement series; review queue
    "bw": "bw",
    "fw": "fw",
    "pw": "pw",
}

#: Latin vowel per order. Order 6 (ə) is empty here: the bare consonant is
#: the cell value and ``to_latin`` inserts the epenthetic vowel by context.
#: verified: false -- agent defaults, see PROGRESS.md human review queue.
_VOWELS: dict[int, str] = {
    1: "e",  # ä; becomes "a" after gutturals, see _GUTTURAL_A
    2: "u",
    3: "i",
    4: "a",
    5: "e",  # é rendered plain (Selassie's "ie" is NOT reproduced); review queue
    6: "",
    7: "o",
    8: "wa",  # labialized column (-WA/-OA forms); review queue
}

#: Series whose first-order vowel is pronounced (and romanized) "a", not "e":
#: the gutturals block the ä vowel (ሀ = "ha", አ = "a" -- hence Tsehay, Abebe).
#: Post-collapse gutturals only; hh/x/pharyngeal never reach the table.
#: verified: false -- whether kx/xw belong here is a review-queue question.
_GUTTURAL_A: frozenset[str] = frozenset({"h", "glottal"})


def _build_practical() -> dict[tuple[str, int], str]:
    """Cross the components over exactly the syllables that exist in Unicode."""
    table: dict[tuple[str, int], str] = {}
    for consonant, order in SYLLABLES.values():
        if consonant in HOMOPHONE_SERIES:
            continue  # collapsed away by normalize(); no row on purpose
        vowel = _VOWELS[order]
        if order == 1 and consonant in _GUTTURAL_A:
            vowel = "a"
        table[(consonant, order)] = _CONSONANTS[consonant] + vowel
    return table


#: (consonant label, vowel order) -> Latin, for every post-collapse syllable.
#: verified: false -- see module docstring.
PRACTICAL: dict[tuple[str, int], str] = _build_practical()

#: Registered schemes. v0.1 ships only "practical"; bgn_pcgn/academic are v0.2.
SCHEMES: dict[str, dict[tuple[str, int], str]] = {"practical": PRACTICAL}
