"""HabeshaKey -- phonetic key for romanized Habesha names.

A Soundex-family key tuned for the spelling variation of Ethiopian/Eritrean
names: two names share a key when they are plausibly the same name written
by different romanizers. The consonant rules were tuned against the golden
corpus in Task 8; the v2 vowel representation below is Task 14 engine work
with linguistic consequences (review-queued, PROGRESS.md).

Pipeline (fidel input is transliterated first, so ፀሐይ keys like "Tsehay"):

1. transliterate (practical scheme; Latin text passes through), lowercase,
   drop every character outside a-z (spaces too: "Haile Mariam" keys like
   "Hailemariam").
2. Digraph folding, left-to-right greedy: ts/tz -> s, sh -> x, ch -> c,
   kh/gh -> h, ph -> f, th -> t.
3. Glide fold: every non-initial "y" becomes "i" -- in romanized Habesha
   names a medial/final y writes the vowel or glide /i/, so ay/ai
   spellings and y/i alternations key identically (Haymanot = Haimanot,
   Maryam = Mariyam = Mariam, Hailemaryam = Hailemariam). Added by Task 8
   corpus tuning; a string-initial "y" (Yohannes) still counts as a
   consonant.
4. Collapse runs of the same letter (Kebbede -> Kebede).
5. Fold the terminal glide -aye / -ay / -ai into a terminal marker "A"
   (Tesfaye = Tesfay = Tesfai); what remains is the *stem*.
6. Record the stem's FIRST and LAST vowels as coarse classes: a -> "a",
   e/i -> "e", o/u -> "o" (so Mohammed and Muhammed agree). Vowels between
   them carry no signal (Fatuma = Fatima, Tewodros = Tewdros).
7. Key = uppercase consonant skeleton (+ terminal marker) + ":" + first
   class + last class, e.g. "Tsehay" -> "SHA:ee" (one stem vowel serves as
   both first and last).

Vowel representation history (Task 14, HabeshaKey v2): v1 kept only the
first-vowel class, which let full-skeleton collisions through -- Bekele and
Bikila both keyed "BKL:e" (a 0.90 false match, the 0.1.0 known_fail). The
final-vowel slot separates them (BKL:ee vs BKL:ea) and encodes a real
property of Habesha names: final vowels are morphologically salient
(Haile/Hailu, Berhane/Berhanu are distinct related names, not spellings).
Rejected alternatives -- (a) the full per-position vowel-class sequence and
(b) that sequence with adjacent-class collapse: both split attested true
variants that differ in interior vowels (Fatuma/Fatima, Almaz/Alimaz) and
would make interior-vowel rewrites key-breaking, shrinking variant sets;
(c) a vowel-count slot: splits epenthesis pairs (Tewodros/Tewdros).

Known, deliberate limits (review queue): q and k are NOT folded, w counts
as a consonant, and same-name spellings that differ in the final-vowel
CLASS key apart (Hiwot/Hiiwet -- bridged by the lexicon variant term in
``match.token.sim``). Tuned against the mechanical golden corpus plus the
Task 14 pins only.
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

#: Coarse vowel classes for the two stem-vowel slots kept in the key.
_VOWEL_CLASS: dict[str, str] = {"a": "a", "e": "e", "i": "e", "o": "o", "u": "o"}

#: Terminal glide spellings folded into the "A" marker; longest first.
#: ("aie" is what the postvocalic y-fold turns "aye" into; "aye"/"ay" are
#: kept for clarity even though the fold rewrites them before this step.)
_TERMINAL_SUFFIXES: tuple[str, ...] = ("aye", "aie", "ay", "ai")


def phonetic_key(name: str) -> str:
    """Return the HabeshaKey for a name token (fidel or Latin).

    Same key = plausibly the same name under romanization variance. Returns
    ``""`` when the input contains no letters. Deterministic; case,
    punctuation, and fidel-vs-Latin script do not affect the key.

    >>> phonetic_key("Tsehay")
    'SHA:ee'
    >>> phonetic_key("Sehay") == phonetic_key("Tsehai") == "SHA:ee"
    True
    >>> phonetic_key("ፀሐይ") == phonetic_key("Tsehay")
    True
    >>> phonetic_key("Mohammed") == phonetic_key("Muhammed")
    True
    >>> phonetic_key("Bekele") == phonetic_key("Bikila")  # BKL:ee vs BKL:ea
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
    for k in range(1, len(folded)):
        # Glide fold (Task 8 tuning): a non-initial y writes the vowel /i/.
        if folded[k] == "y":
            folded[k] = "i"
    collapsed = [ch for k, ch in enumerate(folded) if k == 0 or ch != folded[k - 1]]
    if not collapsed:
        return ""
    text = "".join(collapsed)
    terminal = False
    for suffix in _TERMINAL_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            terminal = True
            break
    stem_vowels = [_VOWEL_CLASS[ch] for ch in text if ch in _VOWEL_CLASS]
    vowel_part = stem_vowels[0] + stem_vowels[-1] if stem_vowels else ""
    skeleton = "".join(ch for ch in text if ch not in _VOWEL_CLASS).upper()
    if terminal:
        skeleton += "A"
    return f"{skeleton}:{vowel_part}"
