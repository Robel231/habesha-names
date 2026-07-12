"""HabeshaKey -- phonetic key for romanized Habesha names.

A Soundex-family key tuned for the spelling variation of Ethiopian/Eritrean
names: two names share a key when they are plausibly the same name written
by different romanizers. Per ARCHITECTURE §4.4 the exact rules are
provisional until tuned against the golden corpus (Task 8); every rule below
is an unreviewed default (verified: false, PROGRESS.md review queue).

Pipeline (fidel input is transliterated first, so ፀሐይ keys like "Tsehay"):

1. transliterate (practical scheme; Latin text passes through), lowercase,
   drop every character outside a-z (spaces too: "Haile Mariam" keys like
   "Hailemariam").
2. Digraph folding, left-to-right greedy: ts/tz -> s, sh -> x, ch -> c,
   kh/gh -> h, ph -> f, th -> t.
3. Collapse runs of the same letter (Kebbede -> Kebede).
4. Record the first vowel as a coarse class: a -> "a", e/i -> "e",
   o/u -> "o" (so Mohammed and Muhammed agree).
5. Fold the terminal glide -aye / -ay / -ai into a terminal marker "A"
   (Tesfaye = Tesfay = Tesfai).
6. Key = uppercase consonant skeleton (+ terminal marker) + ":" + vowel
   class, e.g. "Tsehay" -> "SHA:e".

Known, deliberate limits (review queue): q and k are NOT folded, medial
ay/ai are NOT folded (Haymanot vs Haimanot key differently), and y/w count
as consonants. Tuning happens in Task 8, not here.
"""

from __future__ import annotations

from habesha_names.translit.to_latin import transliterate

#: Two-letter sequences folded to one sound symbol (scan is left-to-right
#: greedy, so "tsh" folds ts first and never sees "sh"). "x" and "c" are
#: internal symbols for the sh/ch sounds, not romanizations.
_DIGRAPH_FOLD: dict[str, str] = {
    "ts": "s",
    "tz": "s",
    "sh": "x",
    "ch": "c",
    "kh": "h",
    "gh": "h",
    "ph": "f",
    "th": "t",
}

#: Coarse vowel classes for the single vowel slot kept in the key.
_VOWEL_CLASS: dict[str, str] = {"a": "a", "e": "e", "i": "e", "o": "o", "u": "o"}

#: Terminal glide spellings folded into the "A" marker; longest first.
_TERMINAL_SUFFIXES: tuple[str, ...] = ("aye", "ay", "ai")


def phonetic_key(name: str) -> str:
    """Return the HabeshaKey for a name token (fidel or Latin).

    Same key = plausibly the same name under romanization variance. Returns
    ``""`` when the input contains no letters. Deterministic; case,
    punctuation, and fidel-vs-Latin script do not affect the key.

    >>> phonetic_key("Tsehay")
    'SHA:e'
    >>> phonetic_key("Sehay") == phonetic_key("Tsehai") == "SHA:e"
    True
    >>> phonetic_key("ፀሐይ") == phonetic_key("Tsehay")
    True
    >>> phonetic_key("Mohammed") == phonetic_key("Muhammed")
    True
    >>> phonetic_key("Alemu") == phonetic_key("Almaz")
    False
    >>> phonetic_key("...")
    ''
    """
    latin = transliterate(name).lower()
    letters = [ch for ch in latin if "a" <= ch <= "z"]
    folded: list[str] = []
    i = 0
    while i < len(letters):
        pair = "".join(letters[i : i + 2])
        if pair in _DIGRAPH_FOLD:
            folded.append(_DIGRAPH_FOLD[pair])
            i += 2
        else:
            folded.append(letters[i])
            i += 1
    collapsed = [ch for k, ch in enumerate(folded) if k == 0 or ch != folded[k - 1]]
    if not collapsed:
        return ""
    text = "".join(collapsed)
    first_vowel = next((_VOWEL_CLASS[ch] for ch in text if ch in _VOWEL_CLASS), "")
    terminal = False
    for suffix in _TERMINAL_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            terminal = True
            break
    skeleton = "".join(ch for ch in text if ch not in _VOWEL_CLASS).upper()
    if terminal:
        skeleton += "A"
    return f"{skeleton}:{first_vowel}"
