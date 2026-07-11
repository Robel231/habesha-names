"""Fidel text normalization: homophone collapsing, punctuation, whitespace.

Several fidel series are pronounced identically in modern Amharic, so the
same name is spelled differently by different writers (ARCHITECTURE 4.1).
:func:`normalize` collapses those series onto one canonical series before
any comparison:

- ሀ-series / ሐ-series / ኀ-series → ሀ-series
- ሠ-series → ሰ-series
- ፀ-series → ጸ-series
- ዐ-series → አ-series

The vowel order is always preserved (ሒ → ሂ, ሥ → ስ, ፃ → ጻ, ዕ → እ): the
collapse swaps the consonant series label via ``decompose``/``compose`` and
never touches the order. The mapping is built mechanically from the generated
tables at import time; no fidel character is hand-typed here.

:func:`normalize` also applies Unicode NFC, strips Ethiopic punctuation
(። ፣ ፤ …, with the wordspace ፡ becoming an ASCII space so it keeps
separating tokens), and collapses whitespace runs. Non-Ethiopic text passes
through with only NFC + whitespace normalization, so the function is safe on
Latin and mixed-script input.

Out of scope here (documented, not silently altered): Ethiopic digits,
tonal marks, combining gemination/length marks, and the Extended block pass
through unchanged; the labialized-velar series ኈ/ቘ/ዀ are not collapsed
(the plan pins exactly the four collapses above).
"""

from __future__ import annotations

import unicodedata

from habesha_names.fidel.tables import CODEPOINT_BY_SYLLABLE, ETHIOPIC_RANGES, SYLLABLES

#: Homophone collapse, as consonant series label → canonical series label
#: (labels as in ``tables.CONSONANT_BY_BASE``). Pinned by IMPLEMENTATION_PLAN
#: Task 2: ሀ/ሐ/ኀ→ሀ, ሠ→ሰ, ፀ→ጸ, ዐ→አ.
HOMOPHONE_SERIES: dict[str, str] = {
    "hh": "h",  # ሐ-series → ሀ-series
    "x": "h",  # ኀ-series → ሀ-series
    "sz": "s",  # ሠ-series → ሰ-series
    "tz": "ts'",  # ፀ-series → ጸ-series
    "pharyngeal": "glottal",  # ዐ-series → አ-series
}

#: U+1361 ETHIOPIC WORDSPACE — a word separator, normalized to an ASCII
#: space (not stripped, which would merge adjacent name tokens).
ETHIOPIC_WORDSPACE = "፡"


def _ethiopic_punctuation() -> frozenset[str]:
    """Every punctuation character in the Ethiopic blocks, per unicodedata."""
    return frozenset(
        chr(cp)
        for first, last in ETHIOPIC_RANGES
        for cp in range(first, last + 1)
        if unicodedata.category(chr(cp)).startswith("P")
    )


#: Ethiopic punctuation stripped by :func:`normalize` (the wordspace becomes
#: a space instead). Derived from Unicode categories, not hand-listed.
ETHIOPIC_PUNCTUATION: frozenset[str] = _ethiopic_punctuation()


def _build_translation() -> dict[int, str | None]:
    """str.translate table: homophone collapse + punctuation handling.

    Raises ``KeyError`` at import if any homophone source syllable lacks a
    same-order target — the generated tables guarantee it does not (verified
    against Unicode 15.1; tests re-assert it).
    """
    table: dict[int, str | None] = {}
    for cp, (consonant, order) in SYLLABLES.items():
        target = HOMOPHONE_SERIES.get(consonant)
        if target is not None:
            table[cp] = chr(CODEPOINT_BY_SYLLABLE[(target, order)])
    for char in ETHIOPIC_PUNCTUATION:
        table[ord(char)] = " " if char == ETHIOPIC_WORDSPACE else None
    return table


_TRANSLATION: dict[int, str | None] = _build_translation()


def normalize(text: str) -> str:
    """Normalize text for name comparison.

    Applies, in order: Unicode NFC → fidel homophone collapse (vowel order
    preserved) → Ethiopic punctuation strip (wordspace ፡ → space) →
    whitespace collapse and trim. Idempotent; never raises on any input
    string. Non-Ethiopic characters are untouched apart from NFC and
    whitespace handling.

    >>> normalize("ኃይለ ሥላሴ")
    'ሃይለ ስላሴ'
    >>> normalize("ወይዘሮ፡ጸሐይ።")
    'ወይዘሮ ጸሀይ'
    >>> normalize("  Tesfaye \\t Gebremedhin ")
    'Tesfaye Gebremedhin'
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TRANSLATION)
    return " ".join(text.split())
