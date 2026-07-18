# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

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
- Variant engine: rewrites that change the final stem vowel (e.g.
  Gebre → Gebra) are now classified key-breaking and no longer combine
  with other rewrites.
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

### Fixed

- **Bekele ↔ Bikila no longer collide** (0.90 → 0.40): the 0.1.0
  known-limitation false match is retired; the pair is now a pinned
  different-person record in the golden corpus.
- **Spaced-compound spelling rewrites no longer misalign**: the last two
  0.1.0 known-limitation records — Gebremedhin ↔ "Gebrie Medhin"
  (0.42 → 0.93) and Hailemariam ↔ "Hailie Mariam" (0.43 → 0.95) — are
  retired; the golden corpus now has **zero `known_fail` records**.

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
