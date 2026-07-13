"""Full-name matching: alignment, scoring, and explanation (ARCHITECTURE 4.4).

:func:`match` parses both names (which strips titles, expands slash
abbreviations, and joins compound given names -- §4.4 step 1), builds a
token-similarity matrix over the positional roles (given / patronym /
avonym), and scores the best role alignment:

- **Swap tolerance**: alignments that cross roles (given matching
  patronym, common when systems disagree on token order) are allowed at a
  small multiplicative penalty (``MatchWeights.swap_penalty``) and flagged
  via ``MatchResult.swapped``.
- **Truncation tolerance**: a 2-token name matched against a 3-token name
  loses a mild multiplicative penalty per unmatched role
  (``1 - role_weight * missing_scale``), not the role's full weight -- an
  absent avonym is weak evidence, not a mismatch.
- **Positional weights**: given 0.45, patronym 0.35, avonym 0.20
  (ARCHITECTURE §4.4), overridable through the :class:`MatchWeights`
  config dataclass. A pair aligned across two roles uses the mean of the
  two role weights.

The score is the weighted mean of aligned token similarities (normalized
over the aligned weights) times the penalties, so it stays in [0, 1].
Every decision is auditable: ``MatchResult.pairs`` carries each aligned
token pair with its similarity and the component that produced it, and
``notes`` carries both parses' notes plus alignment notes ("avonym
missing in b", swap flags).

``swap_penalty = 0.98`` and ``missing_scale = 0.5`` are agent-chosen
constants tuned only against the mechanical golden corpus (verified:
false, PROGRESS.md review queue). Determinism: ties between alignments
keep the first candidate in a fixed enumeration order, which always
starts with the in-order alignment. Parsing is memoized in a bounded
``lru_cache`` (pure memoization; ``parse`` itself is deterministic).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

from habesha_names.match.token import sim_detail
from habesha_names.parse.parser import parse

_ROLES = ("given", "patronym", "avonym")

#: All injective role alignments, precomputed: _ALIGNMENTS[big][small] lists
#: every ordered choice of `small` distinct indices out of range(big), with
#: the in-order alignment first (deterministic tie-breaking relies on this).
_ALIGNMENTS = {
    big: {small: tuple(permutations(range(big), small)) for small in range(1, big + 1)}
    for big in range(1, 4)
}


@dataclass(frozen=True)
class MatchWeights:
    """Scoring configuration for :func:`match` (ARCHITECTURE §4.4 step 4)."""

    given: float = 0.45
    patronym: float = 0.35
    avonym: float = 0.20
    #: Multiplier applied once when the best alignment crosses roles.
    swap_penalty: float = 0.98
    #: Fraction of an unmatched role's weight deducted multiplicatively:
    #: each unmatched role costs a factor (1 - role_weight * missing_scale).
    missing_scale: float = 0.5

    def __post_init__(self) -> None:
        for name in ("given", "patronym", "avonym"):
            if getattr(self, name) <= 0:
                raise ValueError(f"weight {name!r} must be positive")
        for name in ("swap_penalty", "missing_scale"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name!r} must be in [0, 1]")

    def role_weight(self, index: int) -> float:
        return (self.given, self.patronym, self.avonym)[index]


DEFAULT_WEIGHTS = MatchWeights()


@dataclass(frozen=True)
class TokenPair:
    """One aligned token pair with its similarity and scoring method."""

    token_a: str
    token_b: str
    role_a: str  #: "given" | "patronym" | "avonym"
    role_b: str
    sim: float
    method: str  #: "exact" | "phonetic" | "variant" | "jaro_winkler" | "none"


@dataclass(frozen=True)
class MatchResult:
    """Score plus full explanation of one name comparison (ARCHITECTURE §4.4).

    Supports ``float(result)`` and direct comparison with numbers, so
    ``match(a, b) > 0.9`` just works.
    """

    score: float
    pairs: list[TokenPair]
    swapped: bool
    notes: list[str]

    def __float__(self) -> float:
        return self.score

    def __gt__(self, other: float) -> bool:
        return self.score > other

    def __ge__(self, other: float) -> bool:
        return self.score >= other

    def __lt__(self, other: float) -> bool:
        return self.score < other

    def __le__(self, other: float) -> bool:
        return self.score <= other


@lru_cache(maxsize=16384)
def _prepared(raw: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Parse a name into its role tokens and parse notes (memoized)."""
    parsed = parse(raw)
    tokens = tuple(
        token for token in (parsed.given, parsed.patronym, parsed.avonym) if token is not None
    )
    return tokens, tuple(parsed.notes)


def match(a: str, b: str, *, weights: MatchWeights | None = None) -> MatchResult:
    """Score how plausibly two full names (fidel or Latin) are the same name.

    Both names are parsed first (titles stripped, slash abbreviations
    expanded, compounds joined), then the positional roles are aligned
    optimally with swap and truncation tolerance and scored by weighted
    token similarity. Symmetric in score, deterministic, in [0, 1].
    Raises ``ValueError`` when either side has no name tokens.

    >>> match("Abebe Bikila Wolde", "Abebe Bikila Wolde").score
    1.0
    >>> float(match("Ato Abebe Bikila", "abebe bikila"))
    1.0
    >>> match("G/Medhin Tesfaye", "Gebremedhin Tesfaye") > 0.99
    True
    >>> match("Abebe Bikila", "Bikila Abebe").swapped
    True
    >>> round(float(match("Abebe Bikila Wolde", "Abebe Bikila")), 2)
    0.9
    >>> match("Abebe Bikila", "Almaz Tesfahun") <= 0.6
    True
    """
    config = DEFAULT_WEIGHTS if weights is None else weights
    tokens_a, notes_a = _prepared(a)
    tokens_b, notes_b = _prepared(b)
    notes = [f"a: {note}" for note in notes_a] + [f"b: {note}" for note in notes_b]

    # Align the shorter side into the longer one (injective, brute force:
    # at most 3 roles per side). "small"/"big" is an internal orientation;
    # reported pairs always stay (token_a, token_b).
    a_is_small = len(tokens_a) <= len(tokens_b)
    small = tokens_a if a_is_small else tokens_b
    big = tokens_b if a_is_small else tokens_a
    detail = [[sim_detail(s, g) for g in big] for s in small]

    role_w = (config.given, config.patronym, config.avonym)
    best_score = -1.0
    best_perm: tuple[int, ...] = ()
    best_crossed = False
    for perm in _ALIGNMENTS[len(big)][len(small)]:
        weighted = 0.0
        total = 0.0
        crossed = False
        for i, j in enumerate(perm):
            pair_weight = role_w[i] + role_w[j]
            weighted += pair_weight * detail[i][j].score
            total += pair_weight
            crossed = crossed or i != j
        score = weighted / total
        for j in range(len(big)):
            if j not in perm:
                score *= 1.0 - role_w[j] * config.missing_scale
        if crossed:
            score *= config.swap_penalty
        if score > best_score:
            best_score, best_perm, best_crossed = score, perm, crossed

    pairs: list[TokenPair] = []
    for i, j in enumerate(best_perm):
        index_a, index_b = (i, j) if a_is_small else (j, i)
        found = detail[i][j]
        pairs.append(
            TokenPair(
                token_a=tokens_a[index_a],
                token_b=tokens_b[index_b],
                role_a=_ROLES[index_a],
                role_b=_ROLES[index_b],
                sim=found.score,
                method=found.method,
            )
        )
    pairs.sort(key=lambda pair: _ROLES.index(pair.role_a))
    shorter_side = "a" if a_is_small else "b"
    for j in range(len(big)):
        if j not in best_perm:
            notes.append(f"{_ROLES[j]} missing in {shorter_side}")
    if best_crossed:
        notes.append("tokens aligned across roles (order swap tolerated)")
    return MatchResult(score=best_score, pairs=pairs, swapped=best_crossed, notes=notes)
