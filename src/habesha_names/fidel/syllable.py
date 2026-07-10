"""Fidel syllable model: fidel character <-> (consonant series, vowel order).

Most of the Ethiopic block is laid out in 8-codepoint series, one consonant
per series with vowel orders 1-7 plus a labialized eighth column (see
``tables.py``, which is generated from ``unicodedata`` — never hand-typed).
"""

from __future__ import annotations

from typing import NamedTuple

from habesha_names.fidel.tables import CODEPOINT_BY_SYLLABLE, ETHIOPIC_RANGES, SYLLABLES


class Syllable(NamedTuple):
    """A fidel character analyzed as consonant series label + vowel order.

    ``consonant`` is a lowercase series label (e.g. ``"b"``, ``"ny"``,
    ``"ts'"``); ``order`` is 1-7 for the traditional vowel orders
    (ä, u, i, a, é, ə, o) or 8 for the labialized eighth column.
    """

    consonant: str
    order: int


def decompose(char: str) -> Syllable:
    """Decompose a single fidel character into its :class:`Syllable`.

    Raises ``ValueError`` if ``char`` is not exactly one character or is not
    an Ethiopic syllable known to the tables.

    >>> decompose("ቤ")
    Syllable(consonant='b', order=5)
    >>> decompose("ኙ")
    Syllable(consonant='ny', order=2)
    """
    if len(char) != 1:
        raise ValueError(f"decompose() expects a single character, got {char!r}")
    try:
        consonant, order = SYLLABLES[ord(char)]
    except KeyError:
        raise ValueError(f"not an Ethiopic syllable: {char!r}") from None
    return Syllable(consonant, order)


def compose(consonant: str, order: int) -> str:
    """Compose a fidel character from a consonant series label and vowel order.

    Inverse of :func:`decompose`. Raises ``ValueError`` if no fidel exists for
    the combination (labels are the ones in ``tables.CONSONANT_BY_BASE``; not
    every series has all eight orders).

    >>> compose("b", 5)
    'ቤ'
    >>> compose("h", 1)
    'ሀ'
    """
    try:
        return chr(CODEPOINT_BY_SYLLABLE[(consonant, order)])
    except KeyError:
        raise ValueError(f"no fidel syllable for consonant {consonant!r}, order {order}") from None


def is_ethiopic(text: str) -> bool:
    """Return ``True`` if ``text`` is written in Ethiopic script.

    True when the text contains at least one non-whitespace character and
    every non-whitespace character falls in an Ethiopic Unicode block
    (Ethiopic, Ethiopic Supplement, or Ethiopic Extended — including Ethiopic
    punctuation, digits, and combining marks). Whitespace is ignored; any
    non-Ethiopic character (e.g. Latin) makes the result ``False``.

    >>> is_ethiopic("ተስፋዬ")
    True
    >>> is_ethiopic("Tesfaye")
    False
    >>> is_ethiopic("")
    False
    """
    found = False
    for ch in text:
        if ch.isspace():
            continue
        cp = ord(ch)
        if not any(first <= cp <= last for first, last in ETHIOPIC_RANGES):
            return False
        found = True
    return found
