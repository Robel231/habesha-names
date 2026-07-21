# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-21

Second minor release. Two new public functions (`guess_gender`,
`to_fidel`), a bundled lexicon nearly seven times the size of 0.1.0's, a
richer phonetic key, spaced-compound alignment, five new variant rules, and
the first human-curated golden pairs. **Match scores, variant output, and
`phonetic_key` strings change** — every such change is listed under Changed
and is the reason this is a minor bump rather than a patch.

### Added

- **`guess_gender(name) -> GenderGuess`** (planned ARCHITECTURE §5 API):
  lexicon-backed gender inference from the **given** token only —
  patronym and avonym tokens are the father's and grandfather's given
  names, so they are never used as evidence about the bearer. Lookup runs
  in three tiers of descending confidence (exact spelling 0.9, recorded
  variant 0.8, phonetic key 0.6 — flagged heuristics pending
  native-speaker review), each scaled by the matched entry's gender
  distribution; a name without a lexicon hit returns `('unknown', 0.0)`
  honestly, never a guess from spelling shape. Every decision (ignored
  tokens, matched entries, distributions, misses) is recorded in
  `GenderGuess.notes`.
- **`to_fidel(latin, scheme="practical") -> str`** (planned ARCHITECTURE
  §5 API, completing the public surface): reverse transliteration to
  Ethiopic script. Lexicon-first — a recognized canonical/variant
  spelling (given names, compound prefixes/second elements) returns the
  entry's stored conventional fidel verbatim, homophone series included;
  anything else is inverted by rule onto canonical post-collapse fidel
  (the practical scheme is lossy, so the rules never guess a collapsed
  homophone series — mirroring how `transliterate` normalizes first).
  Rule-path output is `normalize`-stable and keeps the input's phonetic
  key; it is a phonetic spelling, not necessarily the conventional
  orthography (ፊኪር for "Fikir" — convention writes ፍቅር, which only a
  lexicon entry can assert). Every output syllable is composed from the
  generated Unicode tables; the disambiguation preferences are flagged
  heuristics pending native-speaker review.

- **Curated golden pairs — the first human baseline** (`tests/golden/curated.json`):
  ten multi-token pairs authored by the repo owner, covering dropped
  avonyms, inverted given/patronym order, skipped generations, variant
  spellings inside multi-token names, and definitively distinct names. They
  ship `needs_human: false` and supersede any colliding generated pair (none
  collided). Their value was immediate: the generated corpus is 98% single
  -token, which left the role weights, `swap_penalty` and `missing_scale`
  **unmeasurable** — no value anywhere in their ranges changed a single
  generated pair. **Six of the ten pass; four are recorded as `known_fail`**,
  so the corpus now carries **7** `known_fail` records (3 generated + 4
  curated). These four are honest, newly-visible engine limits, not
  regressions: two are "skipped generation" pairs the matcher scores 0.8085
  through its truncation tolerance, and two are "one role matches, one
  differs" pairs whose scores **interleave with the existing analyst-review
  pins**, so no threshold can separate them without contradicting the
  task-3b review-zone decision.

### Changed

- **Bundled lexicon: 56 → 380 given-name entries**, authored by the repo
  owner (native speaker) across three waves from a corpus-mined candidate
  queue, and **all 380 ship `verified: true`**. Corpus coverage
  (occurrences sharing a key with a lexicon entry) rises 18.2% → **62.3%**
  and attested-variant recall to **97.1%** (strict 95.7%). Everything
  lexicon-first widens accordingly: `to_fidel` serves many more
  conventional spellings (e.g. "Gebre-Medhin" now resolves through the new
  Gebre given-name entry to ገብሬ-መድህን — given names win a spelling before
  compound prefixes; "Fikir" returns ፍቅሬ via its recording on the Fikre
  entry instead of a rule-path phonetic spelling), `guess_gender` covers
  far more names, and `match` gains recorded-variant evidence. The golden
  corpus regenerates 214 → **1752** pairs. Wave detail:
  - **Wave 1**: 150 entries (56 → 206), coverage 18.2% → 49.9%, corpus
    214 → 1039 pairs with 3 `known_fail` records of engine limits (the
    practical inverse table has no "ph" fold — Yoseph-family spellings key
    differently through the rule path — and the deliberately-accepted
    distinct entries Ali/Ayele share a phonetic key).
  - **Wave 2a**: 31 entries (206 → 237), coverage 49.9% → 53.5%, recall
    96.5% → 96.7%; corpus 1039 → 1151, `known_fail` unchanged at 3. Adds
    the deliberately-distinct pairs Berhane/Birhan (per the 2026-07-20
    ending-pair ruling) and Abeba/Abebe. One candidate (Gebreyohannes) was
    rejected as a `Gebre-` compound already served by compound handling.
  - **Wave 2b**: 143 entries (237 → 380), coverage 53.5% → 62.2%, recall
    97.1% (strict 95.7%); corpus 1151 → 1737. Seven candidates rejected:
    the `Gebre-`/`Welde-` compound family (Gebreyohannes, Gebreyesus,
    Gebreher, Gebreyes, Weldeyohannes, Weldesenbet), which the compound
    engine already matches at 0.95+ without lexicon entries, and Werku, a
    spelling of the existing Worku entry. `known_fail` grew 3 → 7 here:
    four fidel↔canonical pairs whose conventional Latin spelling is far
    from the raw transliteration (Afework, Wubshet, Wondwosen, Wube).
  - **Known-fail retirement via recorded variants**: four of those pairs
    were then retired by recording the raw transliteration as an attested
    variant on its entry, where the repo owner judged that form a spelling
    people actually type — `Fiseha`/Fisha, `Wubshet`/Wibshet, `Wube`/Wibe,
    `Wondwosen`/Wendiwesen — plus `Werku` recorded on the existing `Worku`
    entry. The remaining two of the four are deliberate: `Firehiwot`
    /Firehyiwet and `Afework`/Afewerik were ruled ENGINE ARTIFACTS rather
    than real spellings (the practical table renders ሕይወት as "hyiwet" and
    ርቅ as "rik"; no one writes them that way), so they stay recorded as
    honest engine limits instead of being papered over with invented
    variants.

- **HabeshaKey v2** (phonetic key): the key now records the stem's first
  AND last vowel classes instead of a single first-vowel slot
  (`Tsehay` → `SHA:ee`, previously `SHA:e`). Interior vowels still carry
  no signal (Fatuma = Fatima, Tewodros = Tewdros), but final-vowel
  distinctions — morphologically salient in Habesha names
  (Haile/Hailu, Berhane/Berhanu) — now separate keys. Key strings are
  not a stable API surface, but match scores shift where keys split:
  same-name spellings differing in final-vowel class (Ahmed/Ahmad,
  Mohammed/Mohammad, Hiwot/Hiiwet) now score 0.85 via the lexicon
  variant term instead of 0.90 via the phonetic term. Per the project's
  versioning policy, output-changing tuning lands in a minor release.
- Parser: a spaced compound whose element is a **rewritten spelling**
  ("Gebrie Medhin", "Hailie Mariam") now joins via a phonetic-key
  fallback on the prefix/second-element indexes. The joined token keeps
  the input spelling ("Gebriemedhin" — the key evidences structure, not
  the canonical spelling), the parse note names the matched elements,
  and such joins carry new, lower `compound_confidence` values
  (0.75 overflow / 0.5 ambiguous, vs 0.9 / 0.65 for exact-spelling
  joins). Distinct sibling names (Hailu vs Haile-) do not join — the
  HabeshaKey v2 final-vowel slot keys them apart. `variants()` output is
  unchanged (the variant engine uses exact element matches only).
- Variant engine: five corpus-evidenced rewrite rules added (all weights
  flagged for native-speaker review): **epenthetic i/e insertion** in
  consonant clusters (Ahmed → Ahimed, Mekdes → Mekides/Mekedes,
  Gebremedhin → Gebremedihin, Almaz → Alimaz), **guarded interior-vowel
  deletion** (Tewodros → Tewdros, Mulugeta → Mulgeta), **e↔i wobble**
  between consonants (Yohannes → Yohannis), **ei↔ie transposition**
  (Hussein → Hussien), and a key-breaking **first-vowel o→e wobble**
  (Mohammed → Mehammed). The variant-emission likelihood floor dropped
  0.02 → 0.01 to admit attested two-rewrite chains (Berhanu → Birehanu).
  No rule touches a word-final vowel: final `-u/-e/-ie/-a` endings mark
  morphologically related but distinct names (Haile/Hailu,
  Berhane/Berhanu/Birhan) and are deliberately not bridged.
- **`VARIANT_WEIGHT` raised 0.85 → 0.90** (`habesha_names.match.token`). A
  token pair matched through a recorded lexicon variant asserts a
  ground-truth equivalence, so it now clears the 0.85 same-person gate with
  margin instead of landing exactly on it: previously **287 golden "same"
  pairs passed with a margin of precisely 0.0000**, and a multi-token name
  that took any penalty elsewhere could drop under the gate on arithmetic
  alone. **This changes published output** — `sim("Bekele", "Beqele")` now
  returns `0.9` (was `0.85`) — and is a minor-bump output change under the
  project's versioning policy. `VARIANT_WEIGHT` now ties `PHONETIC_WEIGHT`;
  the tie resolves to `"phonetic"`, preserving the documented
  more-explainable-method-wins ordering. No golden-corpus verdict changed:
  pass/fail counts and every `known_fail` record are identical before and
  after, and corpus recall/coverage are byte-identical (the eval path never
  calls `match()`).

### Removed

- **Last-stem-vowel e→a rewrite retired** (variant engine), per the
  native-speaker ending-pair ruling (2026-07-20): the final stem vowel is
  morphologically load-bearing in Habesha names — Berhane → Berhana
  crosses the same final-vowel-class boundary as the
  Berhane/Berhanu/Birhan possessive series ("light" / "his light" /
  "my light"), so rewriting it manufactures a *different* name, not a
  spelling variant (likewise Gebre → Gabre, Abebe → Abeba — Abeba being
  a plausibly distinct female name). e→a still applies to first and
  interior stem vowels (Gebre → Gabre unchanged). Recorded lexicon
  variants already cover the reviewed Arabic-style e/a spelling pairs
  (Ahmed/Ahmad, Mohammed/Mohammad, Solomon/Soloman), so the retirement
  only narrows variant output for out-of-lexicon names. The confirmed
  word-final e↔ie rewrite (Zewde → Zewdie) is unaffected — it bridges
  renderings within one final-vowel class, never across the -u/-e/-a
  ending splits.

### Fixed

All three limitations carried into 0.1.0 are addressed; the third only in
part, and deliberately so.

- **Bekele ↔ Bikila no longer collide** (0.90 → 0.40): the first 0.1.0
  known-limitation false match is retired via the richer phonetic key; the
  pair is now a pinned different-person record in the golden corpus.
- **Spaced-compound spelling rewrites no longer misalign**: the second
  0.1.0 known limitation — Gebremedhin ↔ "Gebrie Medhin" (0.42 → 0.93) and
  Hailemariam ↔ "Hailie Mariam" (0.43 → 0.95) — is retired via the
  parser's phonetic-key compound fallback.
- **The golden corpus is no longer purely mechanical, and the tuning
  constants are no longer merely "accepted as-is"** — the third 0.1.0
  known limitation. `tests/golden/curated.json` is a tracked,
  human-authored second source whose pairs drop `needs_human` and win
  outright over a colliding generated pair, and the deferred retune ran
  against the expanded corpus: every in-scope constant was swept
  one-at-a-time over a grid against a fixed pair population. It moved
  exactly one constant — `VARIANT_WEIGHT`, above. `KEY_MISMATCH_DAMP` and
  `PHONETIC_WEIGHT` were swept and deliberately left at their shipped
  values (each sits inside a plateau where no corpus pair changes verdict),
  and the parser confidence constants were accepted as shipped, `match()`
  never reading them. **What remains unfinished is stated under Known
  limitations rather than claimed as done**: the corpus is still
  overwhelmingly generated, and the five role constants stay unmeasurable
  at its current composition.

### Known limitations (carried into 0.2.0)

- **The golden corpus records 7 `known_fail` pairs**, against a 0.2.0
  target of 0. Each is an asserted, documented engine limit — the suite
  requires it to keep failing until the engine or the data changes.
  Three are generated: ፍሬሕይወት/Firehiwot (0.56) and አፈወርቅ/Afework (0.55),
  fidel↔canonical pairs whose conventional Latin spelling is far from the
  raw transliteration (retiring them needs a transliteration-table
  decision, not more data), plus Ali ↔ Ayele (0.90), two distinct names
  that legitimately share a phonetic key. Four are curated: two
  skipped-generation truncations ("Abebe Kebede Tadesse" vs "Abebe
  Tadesse", 0.81) that the matcher's truncation tolerance places in the
  review zone rather than reading as non-matches, and two "one role
  matches, one differs" pairs ("Dawit Alemu" vs "Dawit Girma" 0.69,
  "Gebreyesus Hailu" vs "Gebre Hailu" 0.74) whose scores interleave with
  the analyst-review-zone pins the 0.1.0 score bands promise — the engine
  sees one structure there, so no threshold separates them.
- **Five matcher constants remain accepted-as-shipped, not calibrated** —
  the `given`/`patronym`/`avonym` role weights, `swap_penalty` and
  `missing_scale`. 33 of 1752 golden pairs are multi-token, and no value
  anywhere in these constants' plausible ranges changes a single verdict.
  Calibrating them would be fitting to noise; more curated multi-token
  pairs are what would make them measurable.
- **Coverage is 62.3%**, so roughly a third of corpus name occurrences
  still get rule-based handling only, which is weaker for names whose
  conventional spelling diverges from their transliteration.

## [0.1.0] - 2026-07-14

First stable release. The linguistic defaults shipped in 0.1.0a1 have now
passed native-speaker review; the public API is stable within 0.1.x.

### Verified

- Native-speaker review (July 2026) of the practical transliteration
  scheme and the full bundled lexicon (given names, titles, compound
  elements); every lexicon entry now ships `"verified": true`. Newly
  added entries start `"verified": false` until reviewed.

### Changed

- Transliteration: 6th-order word-final **cluster epenthesis** — an
  epenthetic vowel breaks up impermissible final consonant clusters
  (Fikir, Tigist, Kidist, Yohanis), with `st` kept as a permissible coda.
- Transliteration: labialized syllables render as **`ua`, not `wa`**
  (Huala, Guadegnu).
- Canonical forms: **Weizero/Weizerit** (titles) and **Welde** (compound
  prefix) are now the canonical romanizations; Woizero/Wolde remain
  recognized via a new `variants` field in the lexicon schema. Rewrite
  rules we↔wo (mandatory), wa↔ua, and gn↔ny added to the variant engine.
- Conventional canonicals (e.g. Mohammed, Yohannes, Daniel, Mariam) come
  from the lexicon; the raw table outputs (Mehamed, Yohanis, Danel,
  Maryam, …) are kept as recognized variants.
- Golden corpus: sibling-style pairs (shared patronym, different given
  name) now carry an explicit **`review` expectation band** rather than a
  match/no-match verdict; corpus regenerated 201 → 204 pairs, `known_fail`
  reduced 6 → 3 (Mohammed pair resolved). The Selassie xfail was retired
  via the lexicon plus a matcher-level round-trip test.

### Added

- **Score-interpretation policy** (README): ≥ 0.85 likely same person,
  0.60–0.85 review zone routed to an analyst, ≤ 0.60 likely different
  people. The review band is deliberate: sibling-style records score
  there by design.
- Development Status classifier raised to `4 - Beta`; alpha disclaimers
  removed from the README and package docstring.

### Known limitations (carried into 0.1.0)

- **Bekele ↔ Bikila score 0.90**: the phonetic key's single first-vowel
  class slot folds these distinct names together; a richer vowel
  representation is planned for v0.2 (recorded `known_fail`).
- Spelling rewrites inside *spaced* compound forms can misalign against
  the joined form (e.g. "Gebrie Medhin" vs "Gebremedhin"); recorded as
  `known_fail` corpus entries.
- The golden corpus remains mechanically generated and only partially
  human-curated; matcher tuning constants are accepted as-is, to be
  revisited against a fully curated corpus.

## [0.1.0a1] - 2026-07-13

First installable release — an **alpha**. The engine, tests, and packaging
below are complete and CI-gated; the linguistic defaults they encode are
not yet verified, so match scores and variant outputs may change in 0.1.0
final and the API is not yet frozen.

### Works (implemented, tested, shipped)

- Fidel script core: generated Unicode Ethiopic tables (U+1200–U+137F,
  U+1380–U+139F), syllable decomposition/composition, `is_ethiopic`.
- `normalize`: fidel homophone collapsing (ሀ/ሐ/ኀ, ሰ/ሠ, ጸ/ፀ, አ/ዐ),
  Ethiopic punctuation handling, NFC, whitespace normalization.
- `transliterate`: practical (no-diacritics) fidel → Latin scheme.
- Seed lexicons (titles, compound names, ~56 given names) with a
  validated lazy loader; all linguistic data flagged `"verified": false`
  pending native-speaker review.
- `parse`: title stripping, script detection, compound-name detection,
  G/Medhin-style abbreviation expansion, comma inversion, positional
  given/patronym/avonym roles, diaspora mode.
- `variants`: ranked plausible Latin spelling variants for fidel or
  Latin input (weighted rewrite engine + compound/abbreviation forms).
- `phonetic_key` (HabeshaKey) and token similarity (in-repo
  Jaro-Winkler with phonetic and variant-overlap backstops).
- `match`: explainable full-name matching with swap and truncation
  tolerance, configurable weights, and a golden-corpus quality gate
  (201 pairs) plus a ≥50k matches/sec benchmark gate.
- Public API (`habesha_names.__all__`): `parse`, `match`, `variants`,
  `transliterate`, `normalize`, `phonetic_key`, `is_ethiopic`.

### Unverified (pending native-speaker review; may change in 0.1.0 final)

- The practical transliteration scheme's defaults (ቀ→k, 6th-order
  epenthesis, ጸ→ts, ኘ→gn, labialized/guttural/glide rules, …).
- The seed lexicons: every `given_names.json`, `titles.json`, and
  `compounds.json` entry ships `"verified": false`.
- Variant-rule weights and matcher tuning constants (phonetic/variant
  weights, key-mismatch damp, swap/missing penalties).
- The golden corpus: all 201 pairs are agent-generated
  (`needs_human: true`), including 6 documented `known_fail` engine
  limits.
