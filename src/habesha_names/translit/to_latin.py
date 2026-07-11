"""Fidel -> Latin transliteration (practical scheme).

:func:`transliterate` ALWAYS normalizes first (``fidel.normalize.normalize``),
so homophone spellings transliterate identically by construction:
ፀሐይ and ጸሀይ both yield "Tsehay". The scheme tables therefore only cover
post-collapse series (see ``schemes.py``).

Context rules applied on top of the ``PRACTICAL`` cell values -- all of them
unreviewed linguistic defaults (verified: false, PROGRESS.md review queue):

- Sixth-order (ə) syllables are rendered as the bare consonant when they are
  word-final or follow a vowel; otherwise (word-initial, or after a
  consonant) an epenthetic "i" is appended: ስላሴ -> "Silase",
  ገብረመድህን -> "Gebremedhin", but ተስፋዬ -> "Tesfaye" (bare ስ after "e").
- Sixth-order የ (y) after a vowel is a glide: "i" word-medially (ኃይለ ->
  "Haile"), "y" word-finally (ጸሐይ -> "Tsehay").
- Words that start with a fidel syllable are capitalized (name-cased);
  non-Ethiopic words pass through untouched.

Characters with no table entry after normalization (Latin letters, digits,
Ethiopic digits/tonal/combining marks, Extended-block fidel) pass through
unchanged.
"""

from __future__ import annotations

from habesha_names.fidel.normalize import normalize
from habesha_names.fidel.tables import SYLLABLES
from habesha_names.translit.schemes import SCHEMES

_LATIN_VOWELS = frozenset("aeiou")


def _render_word(word: str, table: dict[tuple[str, int], str]) -> str:
    """Transliterate one whitespace-delimited, already-normalized word."""
    parts: list[str] = []
    last = len(word) - 1
    for i, char in enumerate(word):
        entry = SYLLABLES.get(ord(char))
        if entry is None:
            parts.append(char)
            continue
        consonant, order = entry
        latin = table[(consonant, order)]
        if order == 6:
            prev = parts[-1][-1:] if parts else ""
            after_vowel = prev in _LATIN_VOWELS
            final = i == last
            if consonant == "y" and after_vowel:
                latin = "y" if final else "i"
            elif not (final or after_vowel):
                latin = latin + "i"
        parts.append(latin)
    result = "".join(parts)
    if result and word and ord(word[0]) in SYLLABLES:
        result = result[0].upper() + result[1:]
    return result


def transliterate(text: str, scheme: str = "practical") -> str:
    """Transliterate fidel text to Latin using a named scheme.

    Normalizes first (NFC, homophone collapse, punctuation, whitespace), so
    all homophone spellings of a name produce the same Latin form. Words
    written in fidel come back name-cased; anything else passes through.
    Raises ``ValueError`` for an unknown ``scheme`` (v0.1 has "practical").

    >>> transliterate("ተስፋዬ")
    'Tesfaye'
    >>> transliterate("ፀሐይ") == transliterate("ጸሀይ") == "Tsehay"
    True
    >>> transliterate("ወይዘሮ፡ጸሐይ ገብረመድህን።")
    'Weizero Tsehay Gebremedhin'
    >>> transliterate("Tesfaye")
    'Tesfaye'
    """
    try:
        table = SCHEMES[scheme]
    except KeyError:
        known = ", ".join(sorted(SCHEMES))
        raise ValueError(f"unknown scheme {scheme!r} (known: {known})") from None
    words = normalize(text).split(" ")
    return " ".join(_render_word(word, table) for word in words)
