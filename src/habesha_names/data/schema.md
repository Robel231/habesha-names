# Data file contracts — `habesha_names/data/`

These JSON files are **reviewable linguistic assets, not code** (ARCHITECTURE §2, §4.5).
They are loaded, validated, and frozen by `habesha_names._data.lexicon()`; any violation
of the contracts below raises `LexiconError` at first load.

## The `verified` workflow (non-negotiable)

- The coding agent may **seed** entries, but every agent-seeded entry ships
  `"verified": false`. Only Robel (native speaker) flips a flag to `true`, after
  reviewing the entry. The flag is provenance, not a runtime switch: v0.1 code uses
  unverified entries, but no entry may ever be *added* pre-verified.
- Agent-chosen values inside an entry (fidel spellings, variants, gender guesses,
  origins, frequency tiers/weights) are ALL covered by the entry's flag and are listed
  in `PROGRESS.md → Human review queue`.

## General rules (enforced by the loader)

- UTF-8, top-level object with `"schema": 1` plus the file-specific keys below.
- Every entry must have **exactly** the documented keys — no missing, no extras
  (catches typos in hand-edited data).
- `fidel` values must be Ethiopic-script per `fidel.syllable.is_ethiopic`
  (a `/` is additionally allowed inside title abbreviation forms such as `ወ/ሮ`).
  Fidel is stored **as conventionally written** (e.g. ፀሐይ, ኃይለ); consumers apply
  `fidel.normalize.normalize()` at comparison time — do not pre-collapse homophones here.
- Latin name values are ASCII letters only; title abbreviation forms may also use
  `/` and `.` (`W/ro`, `Dr.`).
- Entry order in the file is the canonical order (deterministic outputs); duplicates
  (case-insensitive) are rejected.

## `titles.json` — `{"schema": 1, "entries": [...]}`

| key | type | meaning |
|---|---|---|
| `canonical` | str | Canonical Latin form (`Ato`, `Woizero`, `Dr`) |
| `abbreviations` | list[str] | Other written Latin forms (`W/ro`, `Dr.`, `Doctor`) |
| `fidel` | list[str] | Fidel forms incl. slash abbreviations (`ወይዘሮ`, `ወ/ሮ`) |
| `gender` | `"m"` \| `"f"` \| `null` | `null` = not gendered |
| `category` | `"civil"` \| `"academic"` \| `"professional"` \| `"religious"` | |
| `verified` | bool | see workflow above |

## `compounds.json` — `{"schema": 1, "prefixes": [...], "second_elements": [...], "abbreviation_expansions": [...]}`

Compound given names = prefix + second element (Gebre + Medhin → Gebremedhin), per
ARCHITECTURE §4.3.

- **prefixes**: `latin` (str), `fidel` (str), `gender` (`"m"`/`"f"`/`null`), `verified` (bool).
- **second_elements**: `latin` (str), `fidel` (str), `verified` (bool).
- **abbreviation_expansions**: `abbrev` (str, the letter before `/` or `.` — `"G"` for
  `G/Medhin`), `candidates` (list of `{"expansion": str, "weight": float}`, weights sum
  to 1.0 and are listed in non-increasing order), `verified` (bool). Every `expansion`
  must be a known prefix `latin` or a known given-name `canonical` (e.g. `G/` →
  Gebre 0.8, Girma 0.2). Weights are corpus-frequency estimates — agent-seeded ones are
  guesses pending review.

## `given_names.json` — `{"schema": 1, "entries": [...]}`

Entry contract fixed by ARCHITECTURE §4.5:

```json
{
  "fidel": "ፀሐይ",
  "canonical": "Tsehay",
  "variants": ["Tsehai", "Sehay", "Tzehay"],
  "gender": {"f": 0.97, "m": 0.03},
  "origin": "amharic",
  "freq_tier": 1,
  "verified": false
}
```

- `variants`: common Latin spellings other than `canonical` (must not repeat it).
  Not exhaustive — `translit.variants` (Task 7) generates rule-based variants; this
  list only records attested high-frequency spellings.
- `gender`: probability distribution over `f`/`m`, values sum to 1.0.
- `origin`: one of `amharic`, `tigrinya`, `geez`, `arabic`, `biblical`, `oromo`.
- `freq_tier`: 1 (very common) · 2 (common) · 3 (notable). Relative guess, not a count.

## Review checklist for Robel (per entry)

1. Is the fidel spelling the conventional one (homophone choice included)?
2. Is `canonical` the most common Latin spelling, and are `variants` real/attested?
3. Gender distribution, origin, and tier plausible?
4. Flip `"verified": true` only when all of the above hold; otherwise fix and flip.
