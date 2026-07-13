# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_(nothing yet)_

## [0.1.0] - 2026-07-13

Initial release. All linguistic data (lexicons, transliteration defaults,
variant rules, golden corpus) is agent-seeded and flagged
`"verified": false` pending native-speaker review.

### Added

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
