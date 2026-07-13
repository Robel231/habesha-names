# habesha-names

Ethiopian/Eritrean name intelligence for Python: fidel script handling,
transliteration, spelling-variant generation, name parsing, and
patronymic-aware fuzzy matching.

**Status: pre-alpha (v0.1 in development).** APIs are settling and the
bundled linguistic data has not yet passed native-speaker review — see
[Data verification](#data-verification) below.

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
pip install habesha-names
```

(Not yet on PyPI; v0.1.0 is the first planned release. Until then:
`pip install -e .` from a checkout.)

## Quick tour

Every snippet below is a doctest and runs in CI.

### Parse — name structure, not first/last fields

```python
>>> from habesha_names import parse
>>> p = parse("ወይዘሮ ጸሐይ ገብረመድህን")
>>> (p.title, p.given, p.patronym)
('Woizero', 'ጸሀይ', 'ገብረመድህን')
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

## Data verification

All bundled linguistic data (lexicons, transliteration tables, variant
rules, golden test pairs) was seeded programmatically or by a non-native
speaker and ships flagged `"verified": false` until it passes
native-speaker review. Match scores are deterministic and explainable,
but treat linguistic defaults as provisional until v0.1.0.

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
