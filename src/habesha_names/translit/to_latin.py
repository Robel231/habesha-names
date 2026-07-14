"""Fidel -> Latin transliteration (practical scheme).

:func:`transliterate` ALWAYS normalizes first (``fidel.normalize.normalize``),
so homophone spellings transliterate identically by construction:
ፀሐይ and ጸሀይ both yield "Tsehay". The scheme tables therefore only cover
post-collapse series (see ``schemes.py``).

Context rules applied on top of the ``PRACTICAL`` cell values -- reviewed
and decided by Robel (task-3b, 2026-07-14):

- Sixth-order (ə) syllables are rendered as the bare consonant when they are
  word-final or follow a vowel; word-initially, or after a consonant, an
  epenthetic "i" is appended: ስላሴ -> "Silase", ገብረመድህን -> "Gebremedhin",
  but ተስፋዬ -> "Tesfaye" (bare ስ after "e").
- Word-final clusters of sixth-order consonants epenthesize (cluster rule):
  the epenthetic "i" goes immediately before the final coda, where the coda
  is the last consonant -- or the last TWO when they form the permissible
  final cluster "st". ፍቅር -> "Fikir", ዮሐንስ -> "Yohanis", ትግስት -> "Tigist",
  ቅድስት -> "Kidist" (and ገብረመድህን keeps "medhin": d-h-i-n).
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


#: Consonant pairs allowed as a bare word-final cluster (no epenthesis
#: between them): sibilant + stop, as in Tigist/Kidist. Anything else
#: breaks with "i" before the final consonant (Fikir, Yohanis, medhin).
_FINAL_CODAS: frozenset[tuple[str, str]] = frozenset({("s", "t")})


def _run_start(word: str) -> int:
    """Index where the word-final run of sixth-order syllables begins."""
    start = len(word)
    for i in range(len(word) - 1, -1, -1):
        entry = SYLLABLES.get(ord(word[i]))
        if entry is None or entry[1] != 6:
            break
        start = i
    return start


def _render_word(word: str, table: dict[tuple[str, int], str]) -> str:
    """Transliterate one whitespace-delimited, already-normalized word."""
    parts: list[str] = []
    last = len(word) - 1
    run_start = _run_start(word)
    cluster: list[int] = []  # char indices rendered as bare consonants
    #                          since the last vowel, within the final run
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
            elif i >= run_start:
                # Inside the word-final sixth-order run: only its first
                # consonant may epenthesize by left context (word-initial
                # or after a passthrough consonant); the rest stay bare
                # here and the cluster rule below places the vowel.
                if i == run_start and not after_vowel and not final:
                    latin = latin + "i"
            elif not (final or after_vowel):
                latin = latin + "i"
            if i >= run_start and latin:
                if latin[-1] in _LATIN_VOWELS:
                    cluster.clear()  # this syllable supplied a vowel
                else:
                    cluster.append(i)
        parts.append(latin)
    if len(cluster) >= 2:
        # Cluster epenthesis (task-3b): "i" goes right before the coda.
        coda = 2 if (parts[cluster[-2]], parts[cluster[-1]]) in _FINAL_CODAS else 1
        if len(cluster) > coda:
            parts[cluster[-coda - 1]] += "i"
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
