"""Token-pair similarity: Jaro-Winkler, HabeshaKey backstop, variant overlap.

Per ARCHITECTURE §4.4, ``sim(a, b)`` is the max of three components over
normalized tokens: a phonetic-exact score (``PHONETIC_WEIGHT`` when the
HabeshaKeys agree), variant-set overlap (``VARIANT_WEIGHT`` when either
token appears in the other's Task 7 ``variants()`` output), and
Jaro-Winkler. Task 8 corpus tuning added one interaction: when the two
HabeshaKeys DIFFER, the Jaro-Winkler component is damped by
``KEY_MISMATCH_DAMP`` -- similar-looking but phonetically distinct names
(Tesfaye/Tesfa, Abebe/Abebech) otherwise score ~0.94 on shared prefixes
alone, above any usable same-person threshold. Genuine spelling variants
whose keys differ (Bekele/Beqele, Mohammed/Mahamed, G/Medhin) are caught
by the variant-overlap and lexicon terms instead.

Jaro-Winkler is implemented here from the standard definition (stdlib-only
rule): prefix scale 0.1, prefix capped at 4, boost applied only when the
Jaro score exceeds 0.7. Both empty strings compare equal (1.0); one empty
side scores 0.0. The algorithm itself is case-sensitive; ``sim`` normalizes
(transliterate fidel, lowercase, strip non-letters) before comparing.

``PHONETIC_WEIGHT`` and ``KEY_MISMATCH_DAMP`` are agent-chosen constants
tuned only against the mechanical golden corpus (verified: false,
PROGRESS.md review queue); task-22b swept both and left them as shipped.
``VARIANT_WEIGHT`` is Robel's ruling (task-22b): 0.90, deliberately above
the 0.85 gate. It now TIES ``PHONETIC_WEIGHT``; the tie resolves to
"phonetic", preserving the documented more-explainable-method-wins order.
Normalization, key, and variant-set lookups are memoized in bounded
``lru_cache``\\ s -- pure memoization, no behavioral state.
"""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

from habesha_names.match.phonetic import phonetic_key
from habesha_names.translit.to_latin import transliterate
from habesha_names.translit.variants import variants

#: Score guaranteed when two tokens share a HabeshaKey. Provisional (Task 8).
PHONETIC_WEIGHT = 0.9

#: Score guaranteed when one token is in the other's variant set. Ruled by
#: Robel (task-22b, 2026-07-21): a recorded variant asserts a ground-truth
#: equivalence, so it sits comfortably ABOVE the 0.85 same-person gate rather
#: than exactly on it -- a multi-token structure can then absorb a small
#: penalty elsewhere without the pair failing. Was 0.85 (0.1.0-0.2.0-dev).
VARIANT_WEIGHT = 0.90

#: Jaro-Winkler multiplier when the two HabeshaKeys differ. Provisional.
KEY_MISMATCH_DAMP = 0.6

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


@lru_cache(maxsize=65536)
def _norm(token: str) -> str:
    """Transliterate (fidel passes to Latin), lowercase, keep only a-z."""
    latin = transliterate(token).lower()
    return "".join(ch for ch in latin if "a" <= ch <= "z")


@lru_cache(maxsize=65536)
def _key(norm_token: str) -> str:
    """HabeshaKey of an already-normalized token."""
    return phonetic_key(norm_token)


@lru_cache(maxsize=8192)
def _variant_norms(norm_token: str) -> frozenset[str]:
    """Normalized forms of the token's Task 7 variant set (top-N default)."""
    return frozenset(_norm(variant) for variant in variants(norm_token))


class TokenSim(NamedTuple):
    """A token similarity score plus the component that produced it."""

    score: float
    method: str  #: "exact" | "phonetic" | "variant" | "jaro_winkler" | "none"


@lru_cache(maxsize=131072)
def _sim_norms(norm_a: str, norm_b: str) -> TokenSim:
    """Symmetric similarity core over two distinct normalized tokens.

    Memoized: batch dedup compares the same token pairs constantly, and
    the Jaro-Winkler inner loop dominates runtime otherwise. Callers pass
    the pair in sorted order so both directions share one cache entry.
    """
    key_a, key_b = _key(norm_a), _key(norm_b)
    keys_match = bool(key_a) and key_a == key_b
    jw = jaro_winkler(norm_a, norm_b)
    if not keys_match:
        jw *= KEY_MISMATCH_DAMP
    best = TokenSim(jw, "jaro_winkler")
    if keys_match and PHONETIC_WEIGHT >= best.score:
        best = TokenSim(PHONETIC_WEIGHT, "phonetic")
    if best.score < VARIANT_WEIGHT and (
        norm_b in _variant_norms(norm_a) or norm_a in _variant_norms(norm_b)
    ):
        best = TokenSim(VARIANT_WEIGHT, "variant")
    return best


def sim_detail(a: str, b: str) -> TokenSim:
    """Like :func:`sim`, but also reports which component won.

    Methods: ``"exact"`` (identical normalized tokens), ``"phonetic"``
    (shared HabeshaKey), ``"variant"`` (one token is in the other's
    variant set), ``"jaro_winkler"``, ``"none"`` (a letterless side).
    On score ties the more explainable method wins (phonetic over JW).

    >>> sim_detail("Tzehay", "Sehay")
    TokenSim(score=0.9, method='phonetic')
    >>> sim_detail("Bekele", "Beqele")
    TokenSim(score=0.9, method='variant')
    """
    norm_a, norm_b = _norm(a), _norm(b)
    if not norm_a or not norm_b:
        return TokenSim(0.0, "none")
    if norm_a == norm_b:
        return TokenSim(1.0, "exact")
    if norm_b < norm_a:
        norm_a, norm_b = norm_b, norm_a
    return _sim_norms(norm_a, norm_b)


def sim(a: str, b: str) -> float:
    """Similarity of two name tokens (fidel or Latin), in [0, 1].

    Max of phonetic-exact (``PHONETIC_WEIGHT``), variant-set overlap
    (``VARIANT_WEIGHT``), and Jaro-Winkler (damped by ``KEY_MISMATCH_DAMP``
    when the HabeshaKeys differ) over normalized tokens; identical
    normalized tokens score exactly 1.0, and a missing (letterless) side
    scores 0.0. Symmetric and deterministic.

    >>> sim("Tesfaye", "Tesfaye")
    1.0
    >>> sim("ፀሐይ", "Tsehay")
    1.0
    >>> round(sim("Tzehay", "Sehay"), 2)  # phonetic backstop beats JW here
    0.9
    >>> sim("Bekele", "Beqele")  # variant-set overlap (q<->k, keys differ)
    0.9
    >>> round(sim("Tesfaye", "Tesfa"), 2)  # different name: JW damped
    0.57
    >>> sim("", "Abebe")
    0.0
    """
    return sim_detail(a, b).score
