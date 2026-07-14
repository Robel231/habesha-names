"""Transliteration scheme tables (fidel -> Latin).

verified: true -- native-speaker review completed by Robel (task-3b,
2026-07-14). Every consonant and vowel choice below is a recorded decision
(PROGRESS.md -> Decisions log); changing any of them is a new linguistic
decision, not a refactor.

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
#: verified: true -- decided by Robel, task-3b (2026-07-14).
_CONSONANTS: dict[str, str] = {
    "h": "h",
    "l": "l",
    "m": "m",
    "r": "r",
    "s": "s",
    "sh": "sh",
    "q": "k",  # ቀ: practical usage merges ejective k' into k (Kenenisa)
    "qw": "kw",  # follows the q->k decision
    "qh": "q",  # ቐ: Tigrinya distinction preserved (ቀ stays k)
    "qhw": "qw",
    "b": "b",
    "v": "v",
    "t": "t",
    "c": "ch",  # ቸ: collides with ጨ by design (practical merge)
    "xw": "hw",  # ኈ (x collapses to h, xw is not collapsed)
    "n": "n",
    "ny": "gn",  # ኘ: gn (Agegnehu); gn<->ny is a variant rewrite rule
    "glottal": "",  # አ carries only its vowel
    "k": "k",
    "kw": "kw",
    "kx": "h",  # ኸ: order-1 stays at this default (task-3b)
    "kxw": "hw",
    "w": "w",  # ወ order 1 -> "we" (Weizero, Welde); we<->wo is a variant rule
    "z": "z",
    "zh": "zh",
    "y": "y",
    "d": "d",
    "dd": "dh",  # ዸ (rare, Oromo dh)
    "j": "j",
    "g": "g",
    "gw": "gw",
    "gg": "ng",  # ጘ (velar nasal, rare)
    "th": "t",  # ጠ ejective: practical drops the distinction (Taitu)
    "ch": "ch",  # ጨ ejective: collides with ቸ by design
    "ph": "p",  # ጰ ejective: practical drops the distinction (Paulos)
    "ts'": "ts",  # ጸ: ts (Tsehay); ts<->s<->tz are variant rewrite rules
    "f": "f",
    "p": "p",
    "ry": "ry",  # ፘ ⁄ ፙ ⁄ ፚ: rare one-off syllables
    "my": "my",
    "fy": "fy",
    "mw": "mw",  # Sebatbeit supplement series
    "bw": "bw",
    "fw": "fw",
    "pw": "pw",
}

#: Latin vowel per order. Order 6 (ə) is empty here: the bare consonant is
#: the cell value and ``to_latin`` inserts the epenthetic vowel by context.
#: verified: true -- decided by Robel, task-3b (2026-07-14).
_VOWELS: dict[int, str] = {
    1: "e",  # ä; becomes "a" after gutturals, see _GUTTURAL_A
    2: "u",
    3: "i",
    4: "a",
    5: "e",  # é rendered plain ("Selassie" handled via lexicon variants)
    6: "",
    7: "o",
    8: "ua",  # labialized column: "ua" not "wa" (ሏ -> lua, ሟ -> mua)
}

#: Series whose first-order vowel is pronounced (and romanized) "a", not "e":
#: the gutturals block the ä vowel (ሀ = "ha", አ = "a" -- hence Tsehay, Abebe).
#: Post-collapse gutturals only; hh/x/pharyngeal never reach the table.
#: verified: true -- kx/xw stay OUT (order-1 "he"/"hwe"), decided task-3b.
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
        onset = _CONSONANTS[consonant]
        if order == 4 and len(consonant) > 1 and onset.endswith("w"):
            # Labialized-velar a-forms render "ua", not "wa" (task-3b):
            # ኋ -> hua, ኳ -> kua, ጓ -> gua, ቋ -> kua. Plain ዋ stays "wa".
            table[(consonant, order)] = onset[:-1] + "ua"
            continue
        table[(consonant, order)] = onset + vowel
    return table


#: (consonant label, vowel order) -> Latin, for every post-collapse syllable.
#: verified: true -- see module docstring.
PRACTICAL: dict[tuple[str, int], str] = _build_practical()

#: Registered schemes. v0.1 ships only "practical"; bgn_pcgn/academic are v0.2.
SCHEMES: dict[str, dict[tuple[str, int], str]] = {"practical": PRACTICAL}
