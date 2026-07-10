# IMPLEMENTATION_PLAN — `habesha-names`

Environment: **Windows, cmd (NOT PowerShell)**, repo at `D:\habesha-names`, Python 3.11+.
Protocol: one task per agent session. A task is DONE only when its **Verify** block passes and output is pasted into `PROGRESS.md`.

Setup once:
```cmd
cd /d D:\habesha-names
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .[dev]
```

---

## Task 0 — Repo scaffold
- `pyproject.toml` (setuptools, src layout, `[project.optional-dependencies] dev = ["pytest","ruff","mypy"]`), MIT LICENSE, `.gitignore`, `README.md` stub, `src/habesha_names/__init__.py` with `__version__ = "0.1.0.dev0"`, `py.typed`, empty subpackages per ARCHITECTURE §3, `tests/test_smoke.py`.
- `.github/workflows/ci.yml`: matrix py 3.9–3.13 → ruff check, mypy, pytest.
- Check name availability: open `https://pypi.org/project/habesha-names/` — expect 404. Fallback names: `habeshanames`, `etnames`. Record result in PROGRESS.md.

**Verify:**
```cmd
pip install -e .[dev] && python -c "import habesha_names; print(habesha_names.__version__)" && pytest -q && ruff check . && mypy src
```

## Task 1 — Fidel tables + syllable decomposition
- `scripts/gen_fidel_tables.py` → generates `src/habesha_names/fidel/tables.py` (series bases → consonant labels, vowel orders, labialized forms; blocks U+1200–U+137F, U+1380–U+139F).
- `fidel/syllable.py`: `decompose(char) -> Syllable(consonant, order)`, `compose(consonant, order) -> str`, `is_ethiopic(text) -> bool`.
- Pin tests for known glyphs: ሀ (U+1200, h, order 1), ለ (U+1208, l, 1), ቤ (U+1264, b, 5), ጽ (U+133D, ts', 6), ኙ (U+1299, ny, 2). **Agent: derive expectations from Unicode charts programmatically (`unicodedata.name`), do NOT hand-type from memory.**

**Verify:**
```cmd
python scripts\gen_fidel_tables.py --check && pytest tests\test_fidel_syllable.py -q && mypy src
```

## Task 2 — Fidel normalization
- `fidel/normalize.py`: homophone collapsing (ሀ/ሐ/ኀ→ሀ, ሠ→ሰ, ፀ→ጸ, ዐ→አ — preserving vowel order via decompose/compose), NFC, Ethiopic punctuation strip, whitespace normalize. Idempotency property test.

**Verify:**
```cmd
pytest tests\test_fidel_normalize.py -q
```

## Task 3 — Transliteration (practical scheme, fidel → Latin)
- `translit/schemes.py`: `PRACTICAL` table (consonant label × vowel order → Latin). Seed from generated consonant labels; mark table `verified: false` in a header comment until human review.
- `translit/to_latin.py`: `transliterate(text, scheme="practical")`. Round-trip sanity on lexicon seeds: ተስፋዬ→Tesfaye, ገብረመድህን→Gebremedhin, ጸሐይ→Tsehay, ኃይለ ሥላሴ→Haile Selassie.

**Verify:**
```cmd
pytest tests\test_translit_latin.py -q
```

## Task 4 — Data layer
- `data/schema.md` documenting contracts + `verified` workflow.
- `data/titles.json` (Ato, Woizero/W-ro, Woizerit/W-rt, Dr, Prof, Eng, Qes, Abba, Abune, Memhir, Sheikh, Haji + fidel forms). `data/compounds.json` (prefixes + second elements per ARCHITECTURE §4.3, with slash-abbreviation frequency weights). `data/given_names.json` seeded with ~50 highest-frequency names, ALL `"verified": false`.
- Loader `_data.py`: lazy singleton, `importlib.resources`, schema-validated at load (raise on malformed).

**Verify:**
```cmd
pytest tests\test_data_loader.py -q && python -c "from habesha_names._data import lexicon; print(len(lexicon().given_names))"
```

## Task 5 — Parser
- `parse/titles.py`, `parse/compounds.py` (incl. `G/Medhin`-style expansion), `parse/parser.py` returning `ParsedName` per ARCHITECTURE §4.3.
- Test cases must include: "Abebe Bikila Wolde", "Ato Abebe Bikila", "Hailemariam Desalegn", "Haile Mariam Desalegn" (ambiguous → compound_confidence in (0,1)), "G/Medhin Tesfaye", "Bikila, Abebe", "Abebe B.", "ወይዘሮ ጸሐይ ገብረመድህን", diaspora mode.

**Verify:**
```cmd
pytest tests\test_parse.py -q
```

## Task 6 — Phonetic key + token similarity
- `match/phonetic.py` HabeshaKey per ARCHITECTURE §4.4; `match/token.py` with in-repo Jaro-Winkler (property-test against known JW values).
- Key equality required for: Tsehay/Sehay/Tsehai, Tesfaye/Tesfay/Tesfai, Mohammed/Mohamed/Muhammed, Kebede/Kebbede. Key inequality required for: Alemu/Almaz, Tesfaye/Tesfahun, Abebe/Abebech.

**Verify:**
```cmd
pytest tests\test_match_phonetic.py tests\test_match_token.py -q
```

## Task 7 — Variant generator
- `translit/variants.py`: weighted rewrite-rule engine per ARCHITECTURE §4.2, top-N output, deterministic ordering.
- Property test: `all(match_token(x, v) >= 0.8 for v in variants(x))` once Task 6 lands (wire in Task 8 if circular).

**Verify:**
```cmd
pytest tests\test_variants.py -q
```

## Task 8 — Full-name matcher + golden corpus
- `match/full.py` per ARCHITECTURE §4.4 (alignment, swap tolerance, truncation tolerance, weights config, `MatchResult` with explanation).
- `tests/golden/pairs.json`: ≥150 pairs. Agent seeds ~60 mechanically-derivable pairs (variant-generated); leave `"needs_human": true` markers for Robel to extend with real-world confusables.
- Tune HabeshaKey/weights against corpus; record final thresholds in PROGRESS.md decisions log.

**Verify:**
```cmd
pytest tests\test_match_full.py tests\test_golden.py -q && python scripts\benchmark.py --min-mps 50000
```

## Task 9 — Public API polish + README
- `__init__.py` exports per ARCHITECTURE §5, docstrings with examples on every public callable, README with the 6-snippet pitch (parse/variants/match/normalize/transliterate/explainability), CHANGELOG.md.

**Verify:**
```cmd
pytest -q && mypy src --strict && ruff check . && python -m doctest README.md -v
```

## Task 10 — Packaging + release
- Build sdist/wheel, `twine check`, GitHub Actions release workflow with PyPI Trusted Publishing, tag `v0.1.0`. **Agent prepares everything; Robel pushes the tag** (release is human-triggered, always).

**Verify:**
```cmd
python -m build && twine check dist\*
```

---

## v0.2 backlog (do not start without instruction)
Reverse transliteration (`to_fidel`), `guess_gender`, lexicon → 2,000 entries, academic/BGN schemes, abbreviation-expansion confidence scores, explanation i18n (Amharic notes).

## v0.3 backlog
Oromo qubee rules, Somali-orthography bridge, Tigrinya specifics, CLI, pandas helpers.
