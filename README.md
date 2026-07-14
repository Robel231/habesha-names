# habesha-names

Ethiopian/Eritrean name intelligence for Python: fidel script handling,
transliteration, spelling-variant generation, name parsing, and
patronymic-aware fuzzy matching.

## Alpha status

**Current release: 0.1.0a1 (alpha).** The practical transliteration
rules and the bundled name lexicon have now passed native-speaker
review (see [Data verification](#data-verification)); the golden test
corpus is still mechanically generated and pending human curation, and
**the API is not yet frozen**. Suitable for evaluation and integration
prototyping; pin the exact version if you depend on today's scores.

- **Zero runtime dependencies** — stdlib only
- **Deterministic and explainable** — no ML at runtime, no network calls;
  every match score ships an explanation object. Built for KYC/AML,
  remittance, HR, and entity-resolution pipelines.
- **Fully typed** (`py.typed`, mypy strict)

## Why

Habesha names break global identity systems:

1. **No family names.** A full name is given name + father's given name
   (+ grandfather's). "First/Last name" fields are semantically wrong.
2. **No standard romanization.** ጸሐይ → Tsehay / Tsehai / Sehay / Tzehay —
   same person, four database records.
3. **Compound given names.** "Haile Mariam" can be ONE given name
   (Hailemariam) or given + patronym.
4. **Abbreviation conventions.** Gebremedhin → G/Medhin, G.Medhin,
   Gebre Medhin — all common in official documents.
5. **Fidel homophones.** ሀ/ሐ/ኀ, ሰ/ሠ, ጸ/ፀ, አ/ዐ are pronounced identically;
   spelling varies by writer.

## Install

```
pip install --pre habesha-names
```

(Only alpha releases exist so far, so pip needs `--pre`; plain
`pip install habesha-names` will work once 0.1.0 final is out.
From a checkout: `pip install -e .`)

## Quick tour

Every snippet below is a doctest and runs in CI.

### Parse — name structure, not first/last fields

```python
>>> from habesha_names import parse
>>> p = parse("ወይዘሮ ጸሐይ ገብረመድህን")
>>> (p.title, p.given, p.patronym)
('Weizero', 'ጸሀይ', 'ገብረመድህን')
>>> p.script
'ethiopic'
>>> parse("Hailemariam Desalegn").given_is_compound
True
>>> parse("G/Medhin Tesfaye").given      # slash abbreviation expanded
'Gebremedhin'
>>> parse("Bikila, Abebe").given         # comma inversion handled
'Abebe'

```

### Variants — the spellings your database actually contains

```python
>>> from habesha_names import variants
>>> variants("ጸሐይ", n=6)
['Tsehay', 'Sehay', 'Tsehai', 'Tzehay', 'Tsehaye', 'Sehai']
>>> variants("Gebremedhin", n=5)
['Gebremedhin', 'Gebre Medhin', 'Gebre-Medhin', 'G/Medhin', 'G.Medhin']

```

### Match — patronymic-aware fuzzy matching

```python
>>> from habesha_names import match
>>> match("Ato Abebe Bikila", "abebe bikila") >= 0.85
True
>>> round(float(match("Tesfay Mohamed", "Tesfaye Muhammed")), 2)
0.94
>>> match("Abebe Bikila", "Bikila Abebe").swapped   # field swap tolerated
True
>>> match("Abebe Bikila", "Almaz Tesfahun") <= 0.6
True

```

### Score interpretation

Match scores are calibrated to three bands:

| score | reading |
|---|---|
| ≥ 0.85 | likely the same person |
| 0.60 – 0.85 | review zone — route to an analyst |
| ≤ 0.60 | likely different people |

The middle band is intentional, not indecision: records like
"Tesfaye Girma" vs "Tesfahun Girma" (siblings — different given name,
shared patronym) score there by design, because in KYC/AML pipelines a
shared patronym is exactly the kind of near-match a human should see.

### Explainability — every score can be justified

```python
>>> result = match("ወይዘሮ ጸሐይ ገብረመድህን", "Tsehay G/Medhin")
>>> result.score
1.0
>>> [(pair.token_a, pair.token_b, pair.method) for pair in result.pairs]
[('ጸሀይ', 'Tsehay', 'exact'), ('ገብረመድህን', 'Gebremedhin', 'exact')]
>>> for note in result.notes:
...     print(note)
a: patronym 'ገብረመድህን' is a joined compound (Gebre + Medhin)
b: abbreviation 'G/Medhin' expanded with top candidate 'Gebre' (candidates: Gebre (0.8), Girma (0.2))

```

### Normalize — fidel homophones collapse before comparison

```python
>>> from habesha_names import normalize
>>> normalize("ፀሐይ")                    # ፀ→ጸ, ሐ→ሀ
'ጸሀይ'
>>> normalize("ፀሐይ") == normalize("ጸሀይ")
True

```

### Transliterate — practical romanization, no diacritics

```python
>>> from habesha_names import transliterate
>>> transliterate("ተስፋዬ")
'Tesfaye'
>>> transliterate("ገብረመድህን")
'Gebremedhin'
>>> transliterate("ፀሐይ") == transliterate("ጸሀይ") == "Tsehay"
True

```

### Building blocks

```python
>>> from habesha_names import is_ethiopic, phonetic_key
>>> is_ethiopic("ተስፋዬ")
True
>>> phonetic_key("Tsehay") == phonetic_key("Sehai")   # HabeshaKey
True

```

## Public API

```python
from habesha_names import (
    parse, match, variants, transliterate,
    normalize, phonetic_key, is_ethiopic,
)
```

Everything else is internal. Reverse transliteration (`to_fidel`) and
gender inference (`guess_gender`) are planned for v0.2.

## Known limitations

- **Bekele ↔ Bikila score 0.90** — the phonetic key's single first-vowel
  class slot folds these two distinct names together. A richer vowel
  representation is planned for v0.2; until then this pair is a recorded
  `known_fail` in the golden corpus.
- Spelling rewrites inside *spaced* compound forms can misalign against
  the joined form (e.g. "Gebrie Medhin" vs "Gebremedhin"), also recorded
  as `known_fail` corpus entries.

## Data verification

The bundled lexicons (given names, titles, compound elements) and the
practical transliteration rules passed native-speaker review in July
2026 and are flagged `"verified": true`; any newly added entry starts
`false` again until reviewed. The golden test corpus remains
mechanically generated (`needs_human` markers) pending human curation,
and tuning constants are accepted for 0.1.0 as-is — to be revisited
against a human-curated corpus.

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

MIT
