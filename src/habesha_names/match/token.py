"""Token-pair similarity: in-repo Jaro-Winkler plus the HabeshaKey backstop.

Per ARCHITECTURE §4.4, ``sim(a, b)`` is the max of a phonetic-exact score
and Jaro-Winkler over normalized tokens. The third component of the §4.4
formula, variant-set overlap, requires the Task 7 variant engine and is
wired in Task 8 -- until then ``sim`` is a lower bound on the final design.

Jaro-Winkler is implemented here from the standard definition (stdlib-only
rule): prefix scale 0.1, prefix capped at 4, boost applied only when the
Jaro score exceeds 0.7. Both empty strings compare equal (1.0); one empty
side scores 0.0. The algorithm itself is case-sensitive; ``sim`` normalizes
(transliterate fidel, lowercase, strip non-letters) before comparing.

``PHONETIC_WEIGHT`` (the score a phonetic-key match guarantees) is an
agent-chosen constant pending Task 8 corpus tuning (review queue).
"""

from __future__ import annotations

from habesha_names.match.phonetic import phonetic_key
from habesha_names.translit.to_latin import transliterate

#: Score guaranteed when two tokens share a HabeshaKey. Provisional (Task 8).
PHONETIC_WEIGHT = 0.9

_WINKLER_PREFIX_SCALE = 0.1
_WINKLER_MAX_PREFIX = 4
_WINKLER_BOOST_THRESHOLD = 0.7


def _jaro(a: str, b: str) -> float:
    """Plain Jaro similarity from the standard definition."""
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    if len_a == 0 or len_b == 0:
        return 0.0
    window = max(max(len_a, len_b) // 2 - 1, 0)
    a_matched = [False] * len_a
    b_matched = [False] * len_b
    for i in range(len_a):
        lo = max(0, i - window)
        hi = min(len_b, i + window + 1)
        for j in range(lo, hi):
            if not b_matched[j] and a[i] == b[j]:
                a_matched[i] = True
                b_matched[j] = True
                break
    matches = sum(a_matched)
    if matches == 0:
        return 0.0
    a_seq = [a[i] for i in range(len_a) if a_matched[i]]
    b_seq = [b[j] for j in range(len_b) if b_matched[j]]
    transpositions = sum(x != y for x, y in zip(a_seq, b_seq)) // 2
    return (matches / len_a + matches / len_b + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str) -> float:
    """Jaro-Winkler similarity of two strings, in [0, 1].

    Standard definition: Jaro similarity, boosted by shared-prefix length
    (capped at 4, scale 0.1) when the Jaro score exceeds 0.7. Symmetric and
    case-sensitive; callers wanting name semantics should use :func:`sim`.

    >>> jaro_winkler("MARTHA", "MARHTA") == 17.3 / 18
    True
    >>> jaro_winkler("Kebede", "Kebede")
    1.0
    >>> jaro_winkler("a", "")
    0.0
    """
    score = _jaro(a, b)
    if score <= _WINKLER_BOOST_THRESHOLD:
        return score
    prefix = 0
    for char_a, char_b in zip(a, b):
        if char_a != char_b or prefix == _WINKLER_MAX_PREFIX:
            break
        prefix += 1
    return score + prefix * _WINKLER_PREFIX_SCALE * (1.0 - score)


def _norm(token: str) -> str:
    """Transliterate (fidel passes to Latin), lowercase, keep only a-z."""
    latin = transliterate(token).lower()
    return "".join(ch for ch in latin if "a" <= ch <= "z")


def sim(a: str, b: str) -> float:
    """Similarity of two name tokens (fidel or Latin), in [0, 1].

    ``max(phonetic-exact * PHONETIC_WEIGHT, jaro_winkler)`` over normalized
    tokens; identical normalized tokens score exactly 1.0, and a missing
    (letterless) side scores 0.0. Variant-set overlap joins the max in
    Task 8. Symmetric and deterministic.

    >>> sim("Tesfaye", "Tesfaye")
    1.0
    >>> sim("ፀሐይ", "Tsehay")
    1.0
    >>> round(sim("Tzehay", "Sehay"), 2)  # phonetic backstop beats JW here
    0.9
    >>> sim("", "Abebe")
    0.0
    """
    norm_a, norm_b = _norm(a), _norm(b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0
    score = jaro_winkler(norm_a, norm_b)
    key_a = phonetic_key(norm_a)
    if key_a and key_a == phonetic_key(norm_b):
        score = max(score, PHONETIC_WEIGHT)
    return score
