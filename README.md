# habesha-names

Ethiopian/Eritrean name intelligence for Python: Fidel handling,
transliteration, spelling variants, patronymic-aware parsing, and
fuzzy matching.

[![PyPI version](https://img.shields.io/pypi/v/habesha-names)](https://pypi.org/project/habesha-names/)
[![Python versions](https://img.shields.io/pypi/pyversions/habesha-names)](https://pypi.org/project/habesha-names/)
[![License](https://img.shields.io/pypi/l/habesha-names)](https://github.com/Robel231/habesha-names/blob/main/LICENSE)

## The problem

Habesha names are patronymic: a full name is a given name followed by the
father's given name (and sometimes the grandfather's) — there is no family
surname, so "first/last name" fields are semantically wrong. One name
written in Fidel has many legitimate Latin spellings (ተስፋዬ → Tesfaye,
Tesfai, Tesfay, ...), because there is no standard romanization and Fidel
itself has homophone letters (ሀ/ሐ/ኀ, ሰ/ሠ, ጸ/ፀ) whose choice varies by
writer. Compound given names split, join, and abbreviate
(Gebremedhin / Gebre Medhin / G/Medhin), and token order swaps freely
across documents. Western name-matching logic applied to this reality
produces duplicate customer records, failed KYC lookups, and rejected
remittance matches for the same real person.

## Install

```
pip install habesha-names
```

Zero runtime dependencies (stdlib only). Fully typed — ships `py.typed`.

## 60-second tour

Every example below is a doctest and runs in CI against the real package —
the outputs shown are actual outputs.

### Transliterate

```python
>>> from habesha_names import transliterate
>>> transliterate("ተስፋዬ")
'Tesfaye'

```

Homophone guarantee: Fidel spellings that sound identical transliterate
identically, whichever homophone letters the writer chose.

```python
>>> transliterate("ፀሐይ") == transliterate("ጸሀይ") == "Tsehay"
True

```

### Parse

```python
>>> from habesha_names import parse
>>> p = parse("Ato Abebe Bikila")
>>> (p.title, p.given, p.patronym)
('Ato', 'Abebe', 'Bikila')

```

Fidel input parses the same way (title recognized, roles assigned):

```python
>>> pf = parse("ወይዘሮ ጸሐይ ገብረመድህን")
>>> (pf.title, pf.given, pf.patronym)
('Weizero', 'ጸሀይ', 'ገብረመድህን')

```

By default the second token is a patronym (`has_surname='no'`). For
diaspora data, where the second token may be an inherited surname, the
parser records uncertainty instead of deciding:

```python
>>> parse("Abebe Bikila", assume_diaspora=True).has_surname
'unknown'

```

### Match

```python
>>> from habesha_names import match
>>> result = match("Tesfaye", "Tesfai")
>>> round(result.score, 2)
0.91
>>> [(pair.token_a, pair.token_b, pair.method) for pair in result.pairs]
[('Tesfaye', 'Tesfai', 'jaro_winkler')]
>>> result.swapped
False

```

`match` returns a `MatchResult` (usable directly in comparisons) carrying
the score, the aligned token pairs with the method that matched each pair,
a `swapped` flag, and human-readable `notes`. Unrelated names score low:

```python
>>> match("Abebe", "Girma").score
0.0

```

### Variants

The Latin spellings of a name your database is likely to contain:

```python
>>> from habesha_names import variants
>>> variants("Haile", n=5)
['Haile', 'Hayle', 'Hailie', 'Khaile', 'Haille']

```

### Phonetic key

Spelling variants collapse to one blocking/indexing key:

```python
>>> from habesha_names import phonetic_key
>>> phonetic_key("Tesfaye") == phonetic_key("Tesfai")
True

```

### Guess gender

Lexicon-backed and honest about its limits: only the given name is used
(the patronym is the *father's* given name — it says nothing about the
bearer), and a name the lexicon does not know returns `'unknown'` rather
than a guess from spelling shape:

```python
>>> from habesha_names import guess_gender
>>> guess = guess_gender("Ato Abebe Bikila")
>>> (guess.gender, guess.confidence)
('m', 0.9)
>>> guess_gender("ፀሐይ ገብረመድህን").gender
'f'
>>> guess_gender("Maram").gender
'unknown'

```

### To fidel (reverse transliteration)

Latin spellings back to Ethiopic script. Lexicon-first: a recognized
spelling returns the entry's stored conventional fidel — including the
homophone letters (ፀ, ሐ …) that rules alone could never pick, because the
practical romanization is lossy. Unrecognized spellings are inverted by
rule onto post-collapse fidel: a phonetic spelling that transliterates
back consistently, not necessarily the conventional orthography.

```python
>>> from habesha_names import to_fidel
>>> to_fidel("Tsehay")                       # recognized: conventional fidel
'ፀሐይ'
>>> to_fidel("Tsehai") == to_fidel("Tsehay")  # recorded variants too
True
>>> transliterate(to_fidel("Yohannis"))       # unrecognized: rule path
'Yohanis'

```

### Normalize and script detection

```python
>>> from habesha_names import normalize, is_ethiopic
>>> normalize("ፀሐይ")                    # Fidel homophones collapse: ፀ→ጸ, ሐ→ሀ
'ጸሀይ'
>>> is_ethiopic("ተስፋዬ")
True

```

## KYC, AML, and remittance matching

A remittance operator keys in the sender as spelled on the form; the KYC
record was created years earlier from a different document, with the tokens
in the other order and the patronym abbreviated. Same person, zero exact
overlap between the strings:

```python
>>> from habesha_names import match
>>> result = match("Tesfai G/Medhin", "Gebremedhin Tesfaye")
>>> round(result.score, 2)
0.94
>>> result.swapped
True
>>> for note in result.notes:
...     print(note)
a: abbreviation 'G/Medhin' expanded with top candidate 'Gebre' (candidates: Gebre (0.8), Girma (0.2))
b: given 'Gebremedhin' is a joined compound (Gebre + Medhin)
tokens aligned across roles (order swap tolerated)

```

Scores are calibrated to three bands:

| score | reading |
|---|---|
| ≥ 0.85 | likely the same person |
| 0.60 – 0.85 | review zone — route to an analyst |
| ≤ 0.60 | likely different people |

The middle band is intentional: records like "Tesfaye Girma" vs
"Tesfahun Girma" (different given name, shared patronym — plausibly
siblings) land there by design, because a shared patronym is exactly the
near-match a human should see.

What this library does **not** do: it performs no identity verification and
no sanctions or watchlist screening, and it makes no claim that two records
belong to the same person. It is a deterministic name-processing
primitive — parsing, normalization, and explainable similarity scoring —
for use inside such systems, with every score accompanied by the evidence
(`pairs`, `notes`) an auditor would ask for.

## Linguistic decisions

The practical transliteration scheme's defaults are native-speaker
reviewed: every consonant and vowel choice was reviewed and signed off by
Robel Shemeles (task-3b, 2026-07-14), with each choice recorded in the
project's internal decisions log. Homophone collapse happens in
`normalize`, which `transliterate` applies unconditionally, so the
transliteration table deliberately has no rows for collapsed letter series.
Changing any table cell is a linguistic decision, not a refactor — the
contract and the reasoning are documented in the
[`translit/schemes.py` docstring](src/habesha_names/translit/schemes.py).

## Data provenance

The bundled lexicons (given names, titles, compound elements) are
common-name reference data — seeded during development, then reviewed
entry-by-entry by a native speaker — not scraped data and not records of
any individual. As of 0.2.0 every bundled entry is reviewed and ships
`"verified": true` — 380 given names, 12 titles, and the compound
prefixes and second elements. Per-file origins, generation sources, and
verification status are documented in
[DATA_PROVENANCE.md](DATA_PROVENANCE.md).

## Versioning and stability

The public API — `parse`, `match`, `variants`, `transliterate`,
`normalize`, `phonetic_key`, `is_ethiopic`, and (new in the 0.2 line)
`guess_gender` and `to_fidel` — is stable within a minor series;
everything else is internal. Transliteration outputs are part of
the contract: changing any transliteration table cell changes outputs and
therefore bumps the minor version, never a patch release.

## Known limitations

All three limitations carried into 0.1.0 are resolved in the 0.2 line:
Bekele ↔ Bikila no longer collide (0.90 → 0.40, via the richer phonetic
key), spaced-compound spelling rewrites like "Gebrie Medhin" vs
"Gebremedhin" now align through a phonetic-key fallback in the parser, and
the golden corpus is no longer purely mechanical — it carries a
native-speaker-curated pair set, against which the matcher's variant weight
was calibrated.

What is still imperfect:

- **The golden corpus records 7 `known_fail` pairs.** These are documented
  engine limits, not silent bugs: the test suite asserts each one *keeps*
  failing until the engine or the data changes. Three come from the
  generated corpus — two names whose conventional Latin spelling is far
  from the raw transliteration, so the Fidel spelling and the Latin
  canonical score below the same-person gate (ፍሬሕይወት/Firehiwot,
  አፈወርቅ/Afework), plus Ali ↔ Ayele, two distinct names that legitimately
  share a phonetic key and so score 0.90. Four come from the curated set
  and mark two structural limits: a name shortened by a skipped generation
  ("Abebe Kebede Tadesse" vs "Abebe Tadesse") lands in the review zone
  (0.81) rather than reading as a non-match, and a pair where one role
  matches and the other differs ("Dawit Alemu" vs "Dawit Girma", 0.69) is
  scored the same way whether the two are siblings or strangers — which is
  the review-zone behaviour the score bands promise, so it cannot be
  tightened without contradicting them.
- **Lexicon coverage.** 380 given-name entries cover roughly 62% of name
  occurrences in the development corpus; the remainder gets rule-based
  handling only, which is weaker for names whose conventional spelling
  diverges from their transliteration.
- **Final-vowel-class pairs.** Same-name spellings that differ in
  final-vowel class and have no lexicon entry rest on damped edit
  similarity alone — deliberately, since that ending often marks a
  genuinely different name (Haile/Hailu, Berhane/Berhanu).
- **Role tuning.** The matcher's role weights, swap penalty, and
  missing-role scale remain accepted-as-shipped heuristics. The curated
  corpus is still small enough that no value in their plausible ranges
  changes a verdict, so calibrating them would be fitting to noise.
  `VARIANT_WEIGHT` is the one constant the curated pairs did move.

## Contributing

Issues are welcome, especially edge-case names: spellings that fail to
match, romanizations we do not generate, parsing mistakes on real name
structures. Note that linguistic decisions — transliteration table cells,
lexicon entries, variant rules — require native-speaker sign-off (Robel)
before they land; new lexicon entries ship `"verified": false` until
reviewed, which is why the shipped lexicon is entirely `verified: true` —
the flag tracks the queue, not the release.

## Development

```
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .[dev]
check.bat        # pytest -q && ruff check . && mypy src --strict
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design and
[CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT — see [LICENSE](LICENSE).
