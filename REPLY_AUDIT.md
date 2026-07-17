# REPLY_AUDIT.md — LinkedIn reply vs. actual matcher

Audit of the verbatim LinkedIn reply against the code in `src/habesha_names/`.
Read-only investigation; no library code was changed. Empirical numbers come
from `verify_claims.py` (repo root, not committed) run on `PYTHONPATH=src`.

**Matcher entry points**
- Public: `match(a, b, *, weights=None) -> MatchResult` — [src/habesha_names/match/full.py:135](src/habesha_names/match/full.py#L135)
- Scoring loop (alignment + penalties): [full.py:174-190](src/habesha_names/match/full.py#L174)
- Positional weights: `MatchWeights(given=0.45, patronym=0.35, avonym=0.20, swap_penalty=0.98, missing_scale=0.5)` — [full.py:56-78](src/habesha_names/match/full.py#L56)
- Token similarity: `sim_detail(a, b) -> TokenSim` — [src/habesha_names/match/token.py:152](src/habesha_names/match/token.py#L152); core at [token.py:129-149](src/habesha_names/match/token.py#L129)
- Normalization: `_norm` (transliterate fidel→Latin, lowercase, keep a-z) — [token.py:104-107](src/habesha_names/match/token.py#L104)
- Phonetic key: `phonetic_key(name)` — [src/habesha_names/match/phonetic.py:63](src/habesha_names/match/phonetic.py#L63)
- Role assignment is **positional**: token 1=given, 2=patronym, 3=avonym — [parse/parser.py:211-213](src/habesha_names/parse/parser.py#L211)

**Score policy** (README / CHANGELOG:46-47): **≥0.85** likely same person ·
**0.60–0.85** review zone (route to analyst) · **≤0.60** likely different.
The library exposes no single boolean "threshold" — this is the documented band.

---

## Verdict table

| # | Claim | Verdict | Proof |
|---|-------|---------|-------|
| C1 | Matching is position-agnostic (tokens compared as a set/multiset, not slot-by-slot) | **PARTIALLY TRUE** | It brute-forces **every injective alignment** of the shorter name's tokens onto the longer's and keeps the best — `_ALIGNMENTS`/permutations loop, [full.py:50-53](src/habesha_names/match/full.py#L50) + [full.py:174-190](src/habesha_names/match/full.py#L174) — so a shared token *is* found regardless of position. But it is **not a multiset**: score depends on which positional roles align (`pair_weight = role_w[i] + role_w[j]`, [full.py:179](src/habesha_names/match/full.py#L179)) and a cross-role alignment pays `swap_penalty=0.98` ([full.py:187-188](src/habesha_names/match/full.py#L187)). The reply's own example (`Abebe Kebede Tadesse` vs `Abebe Tadesse`) does **not** "score high" — it lands 0.8085 (review zone). |
| C2 | Tokens normalized to a phonetic/canonical key before comparison, so `Tadesse`/`Tadese`/`ታደሰ` collapse to one key | **PARTIALLY TRUE (mechanism FALSE)** | Normalization before comparison is real: `_norm` transliterates fidel→Latin, lowercases, strips non-letters ([token.py:104-107](src/habesha_names/match/token.py#L104)). But tokens do **not** "collapse to the same key." The phonetic key is only **one of three** components, `max(phonetic 0.9, variant 0.85, Jaro-Winkler)` ([token.py:129-149](src/habesha_names/match/token.py#L129)); even a phonetic-key hit scores **0.9, not identity**. Empirically `Tadesse`/`Tadese` and `Tadesse`/`ታደሰ` each score **0.9714 via jaro_winkler** (not "one key"), so the full names score 0.9943, not 1.0. |
| C3 | First name weighted more heavily than patronymic tokens | **TRUE** | `given=0.45 > patronym=0.35 > avonym=0.20` ([full.py:60-62](src/habesha_names/match/full.py#L60)), applied as `role_w[i]` at [full.py:170,179](src/habesha_names/match/full.py#L170). |
| C4 | Weighting decays down the chain (given > father > grandfather) | **TRUE** | Same constants, strictly decreasing 0.45 → 0.35 → 0.20 ([full.py:60-62](src/habesha_names/match/full.py#L60)). |
| C5 | Truncated names penalized less than genuine mismatches | **TRUE** | An unmatched role costs a **mild multiplicative** factor `1 - role_w * missing_scale` (missing_scale=0.5), not the role's full weight — [full.py:184-186](src/habesha_names/match/full.py#L184): missing avonym = ×0.90, missing patronym = ×0.825. Empirically truncation `Abebe Kebede` = **0.90 (same)** vs. true negative = **0.27 (different)**. |

**Compound sub-claims in the reply, checked separately:**
- "*…still scores high because the shared tokens match regardless of position*" (re `Abebe Tadesse`) → **FALSE**: 0.8085, review zone, not "high."
- "*a match on the given name plus **either** the father or grandfather name clears threshold*" → **HALF FALSE**: given+father (`Abebe Kebede`) = 0.90 clears; given+grandfather with the middle dropped (`Abebe Tadesse`) = 0.8085 does **not** clear 0.85.
- "*a match on only the tail doesn't [clear]*" → **TRUE-ish**: given dropped (`Kebede Tadesse`) = 0.7595, below 0.85 (still review zone, not "different").

---

## Empirical scores (`verify_claims.py`)

Bands: **≥0.85 SAME · 0.60–0.85 REVIEW · ≤0.60 DIFFERENT**

| Pair (a vs b) | Case | Score | Band | Swapped |
|---|---|---|---|---|
| `Abebe Kebede Tadesse` / `Abebe Kebede` | truncation, tail dropped | **0.9000** | SAME | no |
| `Abebe Kebede Tadesse` / `Abebe Tadesse` | **skip-generation (commenter's case)** | **0.8085** | **REVIEW** | yes |
| `Abebe Kebede Tadesse` / `Abebe Tadesse Kebede` | **father/grandfather swapped (commenter's case)** | **0.9800** | SAME | yes |
| `Abebe Kebede Tadesse` / `Kebede Tadesse` | given name dropped | **0.7595** | REVIEW | yes |
| `Abebe Kebede Tadesse` / `Abebe Kebede Tadese` | spelling variant in tail | **0.9943** | SAME | no |
| `Abebe Kebede Tadesse` / `አበበ ከበደ ታደሰ` | script variant (fidel) | **0.9943** | SAME | no |
| `Abebe Kebede Tadesse` / `Girma Alemu Bekele` | true-negative baseline | **0.2741** | DIFFERENT | yes |

Headline: the **swap** case (both tokens present, order flipped) is handled well
(0.98). The **skip-generation** case — the commenter's literal example — is the
weak one at **0.81**, in the review zone, *not* an auto-same-person match.

---

## Rewritten reply (describes only what the code does — 885 chars)

> Good question — it's the messy case the matcher is built around. It doesn't align tokens slot-by-slot: it brute-forces every injective alignment of one name's tokens onto the other's and keeps the best, so a shared name matches regardless of which position it sits in. A father/grandfather swap is tolerated at a small penalty — `Abebe Kebede Tadesse` vs `Abebe Tadesse Kebede` scores ~0.98. Tokens are normalized first (fidel transliterated to Latin), then scored by a phonetic-key + spelling-variant + Jaro-Winkler blend, so `Tadesse`/`Tadese`/`ታደሰ` land ~0.97, not a hard identity. Positions are weighted given > father > grandfather (0.45/0.35/0.20) and a dropped generation is penalized mildly, not as a mismatch. One honest edge: skip a middle generation (`Abebe Tadesse`) and it scores ~0.81 — our review zone, not auto-same. Throw edge cases at it: `pip install habesha-names`.

---

## Correction follow-up (post as a reply — 323 chars)

> Correction on my earlier comment — I said the skip-a-generation case (`Abebe Kebede Tadesse` vs `Abebe Tadesse`) "scores high." It actually lands ~0.81, which is our review zone (0.60–0.85), not an automatic same-person match. A straight father/grandfather swap with no dropped token does score ~0.98. Wanted to be precise.

---

## Gap note: skip-generation before 0.1.1

The commenter's real scenario — same lineage, one **middle** generation omitted
(`Abebe Kebede Tadesse` vs `Abebe Tadesse`) — scores **0.8085**, landing in the
review zone rather than the same-person band. This is not a swap bug; the pure
swap case scores 0.98. It's two penalties stacking:

1. dropping the patronym costs `×0.825` (`1 - 0.35×0.5`, [full.py:184-186](src/habesha_names/match/full.py#L184)); and
2. aligning `Tadesse` (short-side patronym slot) to the long-side avonym counts as a cross-role "swap," costing another `×0.98` ([full.py:187-188](src/habesha_names/match/full.py#L187)).

Weighted token mean is a perfect 1.0; the penalties alone drag it to 0.81. Note
even **removing** the swap penalty only reaches 0.825 — still under 0.85 — so the
binding constraint is the interior-missing penalty, not the swap flag.

**What it'd take:** soften the missing-role penalty for an **interior** dropped
token when the given name is an exact match (e.g. a smaller `missing_scale`, or
skip the swap penalty when a crossing is caused purely by a dropped middle
token rather than a genuine reorder). Either is a `MatchWeights`-level tuning
change, not a redesign. Worth deciding deliberately: a skip-generation match is
arguably *supposed* to be analyst-review rather than auto-same, in which case
0.81 is correct and only the LinkedIn wording was wrong. Flag for the 0.1.1
tuning pass against a human-curated corpus (PROGRESS.md review queue).
