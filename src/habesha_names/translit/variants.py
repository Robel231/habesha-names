"""Latin spelling-variant generator (weighted rewrite engine, ARCHITECTURE 4.2).

Review status (task-3b, 2026-07-14): the linguistic shape of the rules was
reviewed by Robel -- the we<->wo rule (Welde/Wolde), wa<->ua (Huala/Hwala),
and gn<->ny (Tigrigna/Tigrinya) were mandated additions. The numeric
weights and engine constraints remain agent-chosen magnitudes, accepted
as-is for 0.1.0 (revisit with a human-curated corpus).

:func:`variants` takes a name in fidel or Latin and returns a ranked list
of plausible Latin spellings: the name's own (transliterated, name-cased)
spelling first, then rewrites ordered by cumulative likelihood. The engine
has two layers:

- **Token-level alternatives**: lexicon spelling groups (a given-name
  entry's canonical + variants stand in for each other; the Arabic-origin
  table of ARCHITECTURE 4.2 lives in ``given_names.json`` as the
  ``origin: "arabic"`` entries), compound splits/joins/abbreviations
  (Gebremedhin <-> Gebre Medhin <-> Gebre-Medhin <-> G/Medhin <-> G.Medhin,
  detected via ``parse.compounds``), and slash-abbreviation expansion of
  the input itself.
- **Character-level rewrites** within each token: ts<->tz<->s, q<->k,
  h<->kh, th->t, ie<->e, terminal -ay/-ai/-aye, gemination
  doubling/collapse, e->a (sixth-order vowel ambiguity), final w<->ou,
  and the task-16 corpus-evidence rules: epenthetic vowel insertion in
  consonant clusters (Mekdes -> Mekides/Mekedes, Ahmed -> Ahimed),
  guarded interior-vowel deletion (Tewodros -> Tewdros), e<->i wobble
  between consonants (Yohannes -> Yohannis), ei<->ie transposition
  (Hussein -> Hussien), and a first-vowel o->e wobble
  (Mohammed -> Mehammed, 1st-vs-4th-order fidel vowel confusion).

**Ending-pair constraint (task-16; RULED by Robel 2026-07-20)**: final
-u/-e/-ie/-a endings mark morphologically related but DISTINCT names
(Haile/Hailu, Berhane/Berhanu/Birhan, Kassa/Kassie/Kassu), so no rule
here rewrites a word-final vowel: insertion and deletion only ever act
between two consonants, the e<->i wobble requires a following consonant,
and the ei<->ie transposition is suppressed at word-final position. The
ruling confirmed the final e<->ie pair (key-preserving -- it bridges
renderings within one final-vowel class, never across the -u/-e/-a
splits) and RETIRED the last-stem-vowel e->a application (task-16b):
Berhane -> Berhana crosses exactly the final-vowel-class boundary the
ruling treats as name-distinguishing. e->a now applies to first and
interior stem vowels only.

Rewrites are classified by whether they preserve the HabeshaKey
(``match.phonetic``) of the base spelling. Key-preserving rewrites may
combine (up to ``_MAX_REWRITES`` per variant); a key-breaking rewrite is
only ever applied on its own, so no variant drifts more than one
sound-changing step from the input. Variants below ``_MIN_WEIGHT``
cumulative likelihood are dropped even inside the top-N.

Deterministic by construction: fixed exploration limits, best-first
enumeration with total tie-breaking, final ordering by (weight desc,
spelling asc). No lexicon entry is required for the rules to fire -- the
lexicon only adds curated alternatives (ARCHITECTURE 4.5).

Known asymmetries (confirmed as-is for 0.1.0, task-3b): plain s is never
rewritten to ts ("Sehay" only reaches "Tsehay" via its lexicon group),
a->e is not applied (only e->a), and t->th is not applied (only th->t).
"""

from __future__ import annotations

import heapq
import re
from collections.abc import Sequence
from functools import cache

from habesha_names._data import lexicon
from habesha_names.parse.compounds import match_pair, split_joined
from habesha_names.translit.to_latin import transliterate

#: Default number of variants returned (ARCHITECTURE 4.2: top-N, N=25).
DEFAULT_N = 25

# Engine constraints -- agent-chosen, review-queued (see module docstring).
# _MIN_WEIGHT lowered 0.02 -> 0.01 in task-16: corpus-attested spellings
# combine two mid-weight rewrites (e.g. Berhanu -> Birehanu = e->i wobble
# x epenthetic e, 0.15 x 0.12 = 0.018) and the old floor discarded them.
_MIN_WEIGHT = 0.01  #: cumulative-likelihood floor for emitted variants
_MAX_REWRITES = 3  #: max simultaneous rewrites when all preserve the key
_EXPLORE_LIMIT = 64  #: combinations explored per enumeration stage
_MAX_POPS = 4096  #: hard safety cap on best-first heap pops

# Weights -- all invented magnitudes, review-queued.
_W_LEXICON = 0.85  #: another spelling from the same given_names.json group
_W_COMPOUND_RESHAPE = 0.8  #: joined <-> spaced compound
_W_COMPOUND_HYPHEN = 0.6  #: hyphenated compound form
_W_COMPOUND_SLASH = 0.5  #: G/Medhin-style abbreviation
_W_COMPOUND_DOT = 0.4  #: G.Medhin-style abbreviation

#: Character alternative: (replacement, weight, breaks_key).
_Alt = tuple[str, float, bool]
#: Token-level alternative: (replacement tokens, weight, breaks_key).
_TokenAlt = tuple[tuple[str, ...], float, bool]

#: Terminal glide suffixes and their alternates, longest suffix first.
_GLIDE_ALTS: tuple[tuple[str, tuple[_Alt, ...]], ...] = (
    ("aye", (("ay", 0.8, False), ("ai", 0.6, False))),
    ("ay", (("aye", 0.7, False), ("ai", 0.7, False))),
    ("ai", (("ay", 0.7, False), ("aye", 0.6, False))),
)

#: Two-letter sequences and their alternates (left-to-right greedy scan).
#: Most fold to the same HabeshaKey symbol; the ones flagged key-breaking
#: change the consonant skeleton (ou->w, wa<->ua, gn<->ny) or may change
#: a stem-vowel class slot (we<->wo), so they only ever apply alone.
_DIGRAPH_ALTS: dict[str, tuple[_Alt, ...]] = {
    "ts": (("s", 0.6, False), ("tz", 0.4, False)),
    "tz": (("ts", 0.7, False), ("s", 0.5, False)),
    "kh": (("h", 0.7, False),),
    "th": (("t", 0.6, False),),
    # task-16: ei<->ie transposition (Hussein <-> Hussien). Both orders keep
    # the same stem-vowel classes, so the swap is key-preserving; the
    # word-final occurrence is suppressed in _token_sites (ending-pair
    # constraint -- see module docstring).
    "ie": (("e", 0.6, False), ("ei", 0.2, False)),
    "ei": (("ie", 0.3, False),),
    "ou": (("w", 0.3, True),),
    # task-3b (Robel): both spellings occur in the wild for each pair.
    "we": (("wo", 0.6, True),),  # Welde <-> Wolde, Weizero <-> Woizero
    "wo": (("we", 0.6, True),),
    "wa": (("ua", 0.5, True),),  # Hwala <-> Huala (labialized rendering)
    "ua": (("wa", 0.5, True),),
    "gn": (("ny", 0.5, True),),  # Agegnehu <-> Agenyehu
    "ny": (("gn", 0.5, True),),
}

_W_UNDOUBLE = 0.6  #: collapse a doubled letter (Kebbede -> Kebede)
_W_DOUBLE = 0.12  #: double an intervocalic consonant (Kebede -> Kebbede)
_W_Q_TO_K = 0.7
_W_K_TO_Q = 0.3
_W_H_TO_KH = 0.15
_W_W_TO_OU = 0.3  #: word-final w only (Getachew -> Getachou)
_W_E_TO_IE = 0.2  #: word-final e only
_W_E_TO_A = 0.15  #: sixth-order vowel ambiguity (Gebre -> Gabre); first and
#: interior vowels only -- the last-stem-vowel application was retired by
#: the task-16 ending-pair ruling (2026-07-20).

# task-16 rules -- weights are invented magnitudes shaped by corpus gap
# frequencies (review-queued): i-epenthesis is the dominant attested form
# (Ahimed 655 vs Ahemed 130 for Ahmed), deletion and the wobbles are rarer.
_W_EPENTHETIC_I = 0.3  #: insert epenthetic i into a consonant cluster
_W_EPENTHETIC_E = 0.12  #: insert epenthetic e into a consonant cluster
_W_VOWEL_DELETE = 0.1  #: drop a guarded interior vowel (Tewodros -> Tewdros)
_W_E_I_WOBBLE = 0.15  #: e<->i between consonants (Yohannes -> Yohannis)
_W_O_TO_E_FIRST = 0.2  #: first-vowel o->e (Mohammed -> Mehammed); key-breaking

_VOWELS = frozenset("aeiou")

#: One-sound consonant digraphs: epenthesis never splits them and a vowel
#: deletion never fuses one (ts/sh/ch/... fold to a single HabeshaKey
#: symbol, so creating or destroying one would change the skeleton; gn/ny
#: do not fold in the key but are kept here as single sounds per task-3b).
_ONE_SOUND_PAIRS = frozenset({"ts", "tz", "sh", "ch", "kh", "gh", "ph", "th", "gn", "ny"})

#: Stem-vowel classes as the HabeshaKey buckets them (match.phonetic).
#: y is included because the key folds non-initial y to i, making it an
#: e-class stem vowel for guard purposes.
_VOWEL_CLASSES = {"a": "a", "e": "e", "i": "e", "o": "o", "u": "o", "y": "e"}


def _is_consonant(ch: str) -> bool:
    """Consonant for the task-16 cluster rules; y is excluded (glide)."""
    return ch not in _VOWELS and ch != "y"

#: "G/Medhin" / "G.Medhin": one letter, a slash or period, a remainder.
_ABBREVIATION_RE = re.compile(r"^([a-z])[/.](.+)$")


@cache
def _spelling_groups() -> dict[str, tuple[str, ...]]:
    """Lowercased spelling -> its full lexicon group (canonical first).

    Given-name groups take priority; compound prefixes and second elements
    contribute their canonical + recognized-variant spellings too (task-3b:
    Welde/Wolde, Selassie/Silase), so those alternates surface at token level.
    """
    groups: dict[str, tuple[str, ...]] = {}
    lex = lexicon()
    spelling_sets: list[tuple[str, ...]] = [
        (entry.canonical, *entry.variants) for entry in lex.given_names
    ]
    spelling_sets.extend(
        (prefix.latin, *prefix.variants) for prefix in lex.compound_prefixes if prefix.variants
    )
    spelling_sets.extend(
        (second.latin, *second.variants) for second in lex.compound_seconds if second.variants
    )
    for group in spelling_sets:
        for spelling in group:
            groups.setdefault(spelling.lower(), group)
    return groups


@cache
def _abbreviation_candidates() -> dict[str, tuple[tuple[str, float], ...]]:
    return {entry.abbrev.lower(): entry.candidates for entry in lexicon().abbreviations}


@cache
def _prefix_latins() -> frozenset[str]:
    return frozenset(prefix.latin for prefix in lexicon().compound_prefixes)


@cache
def _second_latins() -> frozenset[str]:
    return frozenset(
        spelling.lower()
        for second in lexicon().compound_seconds
        for spelling in (second.latin, *second.variants)
    )


def _abbreviatable(prefix_latin: str) -> bool:
    """True when the prefix round-trips through a known slash abbreviation."""
    candidates = _abbreviation_candidates().get(prefix_latin[0].lower(), ())
    return any(name == prefix_latin for name, _ in candidates)


def _compound_alternatives(
    prefix_latin: str, second_latin: str, *, joined_input: bool
) -> list[_TokenAlt]:
    """The other written shapes of a detected compound (ARCHITECTURE 4.2)."""
    pre, sec = prefix_latin.lower(), second_latin.lower()
    alternatives: list[_TokenAlt] = []
    if joined_input:
        alternatives.append(((pre, sec), _W_COMPOUND_RESHAPE, False))
    else:
        alternatives.append(((pre + sec,), _W_COMPOUND_RESHAPE, False))
    alternatives.append(((f"{pre}-{sec}",), _W_COMPOUND_HYPHEN, False))
    if _abbreviatable(prefix_latin):
        alternatives.append(((f"{pre[0]}/{sec}",), _W_COMPOUND_SLASH, True))
        alternatives.append(((f"{pre[0]}.{sec}",), _W_COMPOUND_DOT, True))
    return alternatives


def _abbreviation_alternatives(token: str) -> list[_TokenAlt]:
    """Expansions of a slash-abbreviated input token, one per candidate."""
    matched = _ABBREVIATION_RE.match(token)
    if matched is None:
        return []
    candidates = _abbreviation_candidates().get(matched.group(1))
    remainder = matched.group(2)
    if candidates is None or remainder not in _second_latins():
        return []
    alternatives: list[_TokenAlt] = []
    for name, weight in candidates:
        if name in _prefix_latins():
            alternatives.append(((name.lower() + remainder,), weight, True))
        else:
            alternatives.append(((name.lower(), remainder), weight, True))
    return alternatives


#: Structural choice point: (first token index, token count, alternatives).
_TokenDim = tuple[int, int, tuple[_TokenAlt, ...]]


def _structural_dims(tokens: tuple[str, ...]) -> list[_TokenDim]:
    """Token-level choice points: compounds, abbreviations, lexicon groups."""
    dims: list[_TokenDim] = []
    claimed = [False] * len(tokens)
    for i in range(len(tokens) - 1):
        if claimed[i] or claimed[i + 1]:
            continue
        pair = match_pair(tokens[i], tokens[i + 1])
        # Exact matches only: the Task 15 phonetic-key fallback evidences
        # structure, not spelling, and the alternatives below are built from
        # the CANONICAL element spellings -- emitting those for a fuzzy hit
        # would smuggle an unweighted spelling rewrite into the ranking.
        if pair is not None and pair.exact:
            claimed[i] = claimed[i + 1] = True
            alternatives = _compound_alternatives(
                pair.prefix.latin, pair.second.latin, joined_input=False
            )
            dims.append((i, 2, _sorted_alts(alternatives)))
    for i, token in enumerate(tokens):
        if claimed[i]:
            continue
        alternatives = _abbreviation_alternatives(token)
        group = _spelling_groups().get(token)
        if group is not None:
            alternatives.extend(
                ((other.lower(),), _W_LEXICON, True) for other in group if other.lower() != token
            )
        compound = split_joined(token)
        if compound is not None:
            alternatives.extend(
                _compound_alternatives(
                    compound.prefix.latin, compound.second.latin, joined_input=True
                )
            )
        if alternatives:
            dims.append((i, 1, _sorted_alts(alternatives)))
    return dims


def _sorted_alts(alternatives: list[_TokenAlt]) -> tuple[_TokenAlt, ...]:
    return tuple(sorted(alternatives, key=lambda alt: (-alt[1], alt[0])))


#: Character choice point: (token index, start, end, alternatives).
_CharDim = tuple[int, int, int, tuple[_Alt, ...]]
#: Character choice point within one token: (start, end, alternatives).
_Site = tuple[int, int, tuple[_Alt, ...]]


def _token_sites(token: str) -> list[_Site]:
    """Character-level choice points for one lowercase alphabetic token."""
    first_vowel = next((i for i, ch in enumerate(token) if ch in _VOWELS), -1)
    last_vowel = next(
        (i for i in range(len(token) - 1, -1, -1) if token[i] in _VOWELS), -1
    )
    # Stem-vowel positions as the HabeshaKey sees them (non-initial y acts
    # as an i-class vowel); the task-16 guards prove a rewrite cannot move
    # a first/last stem-vowel-class slot of the key.
    stems = [i for i, ch in enumerate(token) if ch in _VOWELS or (i > 0 and ch == "y")]
    claimed = [False] * len(token)
    ranges: list[tuple[int, int]] = []
    sites: list[_Site] = []

    def claim(start: int, end: int, alts: tuple[_Alt, ...]) -> None:
        for k in range(start, end):
            claimed[k] = True
        ranges.append((start, end))
        sites.append((start, end, alts))

    def deletion_ok(k: int) -> bool:
        """True when dropping the vowel at k provably preserves the key.

        task-16 guards: the vowel sits between two distinct consonants
        that do not fuse into a one-sound digraph; it is never the first
        stem vowel, and it is the last stem vowel only when a same-class
        vowel precedes it AND a coda cluster follows (Tigist -> Tigst).
        A word-final vowel is untouchable by construction (ending-pair
        constraint, module docstring).
        """
        if not (0 < k < len(token) - 1) or len(stems) < 2:
            return False
        prev_ch, next_ch = token[k - 1], token[k + 1]
        if not (_is_consonant(prev_ch) and _is_consonant(next_ch)):
            return False
        if prev_ch == next_ch or prev_ch + next_ch in _ONE_SOUND_PAIRS:
            return False
        if k == stems[0]:
            return False
        if k == stems[-1] and (
            _VOWEL_CLASSES[token[stems[-2]]] != _VOWEL_CLASSES[token[k]]
            or len(token) - 1 - k < 2
        ):
            return False
        return True

    for suffix, glide_alts in _GLIDE_ALTS:
        if token.endswith(suffix) and len(token) > len(suffix):
            claim(len(token) - len(suffix), len(token), glide_alts)
            break
    i = 0
    while i < len(token) - 1:
        pair = token[i : i + 2]
        digraph_alts = _DIGRAPH_ALTS.get(pair)
        if digraph_alts is not None and not claimed[i] and not claimed[i + 1]:
            if pair in ("ie", "ei") and i + 2 == len(token):
                # Ending-pair constraint (task-16): never transpose a
                # word-final ie/ei -- final -ie belongs to the -u/-e/-ie/-a
                # morphological endings reserved for Robel's ruling.
                digraph_alts = tuple(a for a in digraph_alts if a[0] not in ("ie", "ei"))
            if pair in ("we", "wo") and deletion_ok(i + 1):
                # The vowel of we/wo is claimed with the digraph, yet its
                # attested drop (Tewodros -> Tewdros) must stay reachable:
                # expressed as an extra alternative of this same site.
                digraph_alts = (*digraph_alts, ("w", _W_VOWEL_DELETE, False))
            if digraph_alts:
                claim(i, i + 2, digraph_alts)
                i += 2
                continue
        i += 1
    i = 0
    while i < len(token) - 1:
        if token[i] == token[i + 1] and not claimed[i] and not claimed[i + 1]:
            claim(i, i + 2, ((token[i], _W_UNDOUBLE, False),))
            i += 2
        else:
            i += 1
    # task-16: epenthetic-vowel insertion points inside consonant clusters
    # (Mekdes -> Mekides/Mekedes). Zero-width sites: _apply_chars inserts
    # the vowel before position j; they claim no characters, so cluster
    # consonants keep their own rewrite sites. Guards: never split a
    # one-sound unit (digraph/double), and the inserted e-class vowel must
    # not become a first/last stem-vowel-class slot of a different class.
    for j in range(1, len(token)):
        c1, c2 = token[j - 1], token[j]
        if not (_is_consonant(c1) and _is_consonant(c2)) or c1 == c2:
            continue
        if c1 + c2 in _ONE_SOUND_PAIRS or any(s < j < e for s, e in ranges):
            continue
        before = [p for p in stems if p < j]
        after = [p for p in stems if p >= j]
        if not (before or after):
            continue  # vowelless token: an inserted vowel would rewrite the key
        if not before and _VOWEL_CLASSES[token[after[0]]] != "e":
            continue
        if not after and _VOWEL_CLASSES[token[before[-1]]] != "e":
            continue
        sites.append(
            (j, j, (("i", _W_EPENTHETIC_I, False), ("e", _W_EPENTHETIC_E, False)))
        )
    for i, ch in enumerate(token):
        if claimed[i]:
            continue
        alts: list[_Alt] = []
        final = i == len(token) - 1
        if ch == "q":
            alts.append(("k", _W_Q_TO_K, True))
        elif ch == "k":
            alts.append(("q", _W_K_TO_Q, True))
        elif ch == "h":
            alts.append(("kh", _W_H_TO_KH, False))
        elif ch == "w" and final:
            alts.append(("ou", _W_W_TO_OU, True))
        elif ch == "e" and i > 0:
            if final:
                alts.append(("ie", _W_E_TO_IE, False))
            if i == first_vowel:
                if token.count("e") <= 2:
                    # Changing the FIRST vowel changes a HabeshaKey vowel
                    # slot (key-breaking). Gated to tokens with at most two
                    # e's: on e-heavier names the greedy Jaro-Winkler
                    # matching scrambles and the variant drifts below 0.8
                    # similarity (Bekele -> Bakele scores 0.78).
                    alts.append(("a", _W_E_TO_A, True))
            elif i != last_vowel:
                # Interior vowels only. The LAST stem vowel is excluded:
                # the last-stem-vowel e->a application (Gebre -> Gebra,
                # Berhane -> Berhana) was RETIRED by the task-16 ending-pair
                # ruling (Robel, 2026-07-20) -- it bridged exactly the
                # final-vowel-class boundary that marks morphologically
                # distinct names (Berhane/Berhana-style possessive endings).
                alts.append(("a", _W_E_TO_A, False))
        # task-16 vowel rules; each is provably key-preserving via the
        # guards except first-vowel o->e, which moves a class slot
        # (o -> e class) and is therefore key-breaking (applies alone).
        if (
            ch in "ei"
            and 0 < i < len(token) - 1
            and _is_consonant(token[i - 1])
            and _is_consonant(token[i + 1])
        ):
            # e<->i wobble between consonants (Yohannes -> Yohannis); the
            # following-consonant requirement keeps word-final vowels out.
            alts.append(("i" if ch == "e" else "e", _W_E_I_WOBBLE, False))
        if ch == "o" and i == first_vowel:
            # 1st-vs-4th-order fidel vowel confusion (Mohammed -> Mehammed).
            alts.append(("e", _W_O_TO_E_FIRST, True))
        if ch in _VOWELS and deletion_ok(i):
            alts.append(("", _W_VOWEL_DELETE, False))
        if (
            ch not in _VOWELS
            and 0 < i < len(token) - 1
            and token[i - 1] in _VOWELS
            and token[i + 1] in _VOWELS
        ):
            alts.append((ch + ch, _W_DOUBLE, False))
        if alts:
            claim(i, i + 1, tuple(sorted(alts, key=lambda alt: (-alt[1], alt[0]))))
    sites.sort(key=lambda site: (site[0], site[1]))
    return sites


def _char_dims(tokens: Sequence[str]) -> list[_CharDim]:
    """Character-level choice points, per token, in deterministic order."""
    dims: list[_CharDim] = []
    for t_index, token in enumerate(tokens):
        if not all("a" <= ch <= "z" for ch in token):
            continue  # slash forms, passthrough text: no character rewrites
        dims.extend((t_index, start, end, alts) for start, end, alts in _token_sites(token))
    return dims


def _combinations(
    dims: Sequence[Sequence[tuple[float, bool]]], max_rewrites: int, allow_break: bool
) -> list[tuple[float, tuple[int, ...]]]:
    """Best-first enumeration of rewrite combinations under the budget.

    ``dims[d]`` lists (weight, breaks_key) per alternative, identity first
    at weight 1.0, then non-increasing. Returns (weight, index vector)
    pairs in non-increasing weight order (ties broken by index vector).
    A combination is kept when all chosen rewrites preserve the key (at
    most ``max_rewrites`` of them) or when it is a single key-breaking
    rewrite and ``allow_break`` is set.
    """
    start = (0,) * len(dims)
    heap: list[tuple[float, tuple[int, ...]]] = [(-1.0, start)]
    seen = {start}
    results: list[tuple[float, tuple[int, ...]]] = []
    pops = 0
    while heap and len(results) < _EXPLORE_LIMIT and pops < _MAX_POPS:
        negated, state = heapq.heappop(heap)
        weight = -negated
        pops += 1
        rewrites = sum(1 for index in state if index)
        if rewrites and weight < _MIN_WEIGHT:
            continue  # successors only get lighter
        if rewrites > max_rewrites:
            continue  # successors never drop a rewrite
        breaks = sum(1 for d, index in enumerate(state) if index and dims[d][index][1])
        if breaks == 0 or (allow_break and breaks == 1 and rewrites == 1):
            results.append((weight, state))
        for d, index in enumerate(state):
            if index + 1 < len(dims[d]):
                successor = state[:d] + (index + 1,) + state[d + 1 :]
                if successor not in seen:
                    seen.add(successor)
                    succ_weight = weight / dims[d][index][0] * dims[d][index + 1][0]
                    heapq.heappush(heap, (-succ_weight, successor))
    return results


def _apply_structural(
    tokens: tuple[str, ...], dims: Sequence[_TokenDim], state: tuple[int, ...]
) -> tuple[str, ...]:
    result = list(tokens)
    for (start, count, alts), index in sorted(
        zip(dims, state), key=lambda pair: -pair[0][0]
    ):
        if index:
            result[start : start + count] = alts[index - 1][0]
    return tuple(result)


def _apply_chars(
    tokens: tuple[str, ...], dims: Sequence[_CharDim], state: tuple[int, ...]
) -> tuple[str, ...]:
    result = list(tokens)
    # Right-to-left per token; at an equal start the wider site applies
    # first so a zero-width insertion at the same position lands BEFORE
    # the rewritten span (task-16 epenthesis sites).
    for (t_index, start, end, alts), index in sorted(
        zip(dims, state), key=lambda pair: (pair[0][0], -pair[0][1], -pair[0][2])
    ):
        if index:
            token = result[t_index]
            result[t_index] = token[:start] + alts[index - 1][0] + token[end:]
    return tuple(result)


def _name_case(token: str) -> str:
    """Capitalize the token start and each letter after '/', '.', or '-'."""
    chars: list[str] = []
    capitalize = True
    for ch in token:
        chars.append(ch.upper() if capitalize else ch)
        capitalize = ch in "/.-"
    return "".join(chars)


def variants(name: str, *, n: int = DEFAULT_N) -> list[str]:
    """Ranked plausible Latin spellings of a name (fidel or Latin input).

    The first entry is always the input's own spelling (transliterated if
    fidel, name-cased); the rest are rule-engine and lexicon rewrites in
    non-increasing likelihood order (ties broken alphabetically), capped
    at ``n`` (default 25) and deduplicated. Hyphens are treated as token
    separators. Returns ``[]`` for input with no tokens after
    normalization. Raises ``ValueError`` when ``n < 1``. Deterministic.

    >>> variants("Tesfaye")[0]
    'Tesfaye'
    >>> {"Tesfay", "Tesfai"} <= set(variants("Tesfaye"))
    True
    >>> {"Sehay", "Tzehay"} <= set(variants("ፀሐይ"))
    True
    >>> {"Gebre Medhin", "G/Medhin"} <= set(variants("Gebremedhin"))
    True
    >>> variants("ጸሀይ") == variants("ፀሐይ")
    True
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    tokens = tuple(part.lower() for part in transliterate(name).replace("-", " ").split())
    if not tokens:
        return []
    pool: dict[str, float] = {}
    structural = _structural_dims(tokens)
    structural_wb = [
        ((1.0, False), *((weight, breaks) for _, weight, breaks in alts))
        for _, _, alts in structural
    ]
    for weight_a, state_a in _combinations(structural_wb, _MAX_REWRITES, True):
        rewrites_a = sum(1 for index in state_a if index)
        breaks_a = any(
            structural_wb[d][index][1] for d, index in enumerate(state_a) if index
        )
        shaped = _apply_structural(tokens, structural, state_a)
        chars = _char_dims(shaped)
        chars_wb = [
            ((1.0, False), *((weight, breaks) for _, weight, breaks in alts))
            for _, _, _, alts in chars
        ]
        budget = 0 if breaks_a else _MAX_REWRITES - rewrites_a
        for weight_b, state_b in _combinations(chars_wb, budget, rewrites_a == 0):
            weight = weight_a * weight_b
            rewritten = rewrites_a + sum(1 for index in state_b if index)
            if rewritten and weight < _MIN_WEIGHT:
                continue
            spelling = " ".join(
                _name_case(token) for token in _apply_chars(shaped, chars, state_b)
            )
            if pool.get(spelling, 0.0) < weight:
                pool[spelling] = weight
    ranked = sorted(pool.items(), key=lambda item: (-item[1], item[0]))
    return [spelling for spelling, _ in ranked[:n]]
