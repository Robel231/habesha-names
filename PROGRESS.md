# PROGRESS — `habesha-names`

> Agent: read this file FIRST every session. Update it LAST every session. A task without pasted verification output is NOT done, regardless of what any previous session claims.

## Status board

| Task | Title | Status | Verified evidence |
|---|---|---|---|
| 0 | Repo scaffold + CI | ✔ VERIFIED (evidence below) | Session 1, 2026-07-10 |
| 1 | Fidel tables + syllables | ✔ VERIFIED (evidence below) | Session 2, 2026-07-10 |
| 2 | Fidel normalization | ✔ VERIFIED (evidence below) | Session 3, 2026-07-11 |
| 3 | Transliteration (practical) | ☐ not started | — |
| 4 | Data layer + seed lexicons | ☐ not started | — |
| 5 | Parser | ☐ not started | — |
| 6 | Phonetic key + token sim | ☐ not started | — |
| 7 | Variant generator | ☐ not started | — |
| 8 | Full matcher + golden corpus | ☐ not started | — |
| 9 | API polish + README | ☐ not started | — |
| 10 | Packaging + release prep | ☐ not started | — |

Status values: `☐ not started` · `◐ in progress` · `✕ blocked (reason)` · `✔ VERIFIED (evidence below)`

## Human review queue (Robel)

Items the agent must NOT resolve itself:
- [ ] PyPI name availability result (Task 0) — confirm final package name.
  Agent finding 2026-07-10: PyPI JSON API returned 404 for all of `habesha-names`, `habeshanames`, `etnames` → all three available. Proceeding with `habesha-names` pending Robel's confirmation. (Note: the HTML page `pypi.org/project/habesha-names/` returned HTTP 200, but it was a "Client Challenge" anti-bot page, not a project page — the JSON API is the authoritative check.)
- [ ] Consonant label override in `scripts/gen_fidel_tables.py` (Task 1): `TS → "ts'"` (ejective marking, pinned by the plan). All other labels are mechanical lowercased Unicode name fragments (e.g. ሐ→`hh`, ኀ→`x`, ጠ→`th`, ፀ→`tz`, አ→`glottal`, ዐ→`pharyngeal`) — internal series IDs, NOT romanizations; confirm they are acceptable as internal labels or extend the override map when Task 3 defines the PRACTICAL scheme.
- [ ] Order-8 (labialized) homophone collapses in `fidel/normalize.py` (Task 2): the plan pins "preserve vowel order", and our tables treat the labialized column as order 8, so mechanically ሗ (HHWA)→ሇ (HOA), ኇ (XOA)→ሇ (HOA), ሧ (SZWA)→ሷ (SWA), ፇ (TZOA)→ጿ (TSWA). Orders 1–7 are uncontroversial; confirm these four order-8 mappings are linguistically right (ሇ is rare).
- [ ] Labialized-velar series ኈ/ቘ/ዀ (xw/qhw/kxw) are NOT collapsed by `normalize` (Task 2) — the plan lists only ሀ/ሐ/ኀ, ሠ, ፀ, ዐ, and no "hw" target series exists in Unicode. Question for Robel: should ኋ (XWAA) collapse to anything (e.g. is ኋ/ሗ homophony worth handling), or is pass-through correct?
- [ ] `translit/schemes.py` PRACTICAL table — native-speaker review
- [ ] All `given_names.json` entries with `"verified": false`
- [ ] Golden corpus entries marked `"needs_human": true`
- [ ] Final match-score thresholds (Task 8 tuning)
- [ ] Release tag push (Task 10)

## Session log

### Session template (copy for each session)
```
## Session N — YYYY-MM-DD
Task attempted:
What was actually done:
Verification output (paste FULL command + output, unedited):
    <paste here>
Files touched:
Deviations from plan (and why):
Known issues / TODOs introduced:
Next session should start with:
```

## Session 1 — 2026-07-10

Task attempted: Task 0 — Repo scaffold + CI

What was actually done:
- Created `pyproject.toml` (setuptools src layout, PEP 639 license metadata, dynamic version from `habesha_names.__version__`, dev extras pytest/ruff/mypy, ruff + mypy + pytest config), MIT `LICENSE` (Robel Shemeles, 2026), `.gitignore`, `README.md` stub.
- Created `src/habesha_names/__init__.py` (`__version__ = "0.1.0.dev0"`), `py.typed`, empty subpackages `fidel/`, `translit/`, `parse/`, `match/`, `data/` (each with a docstring-only `__init__.py`).
- Created `tests/test_smoke.py` (version pin + subpackage import test).
- Created `.github/workflows/ci.yml`: ubuntu-latest, matrix Python 3.9–3.13, steps: `pip install -e .[dev]` → `ruff check .` → `mypy src` → `pytest -q`.
- Created `.venv`, installed dev deps, ran the Verify block twice (see below for why twice).
- Checked PyPI name availability (result recorded in Human review queue above): all three candidate names free; staying with `habesha-names`.
- `git init` + initial commit `task-0: repo scaffold + CI`.

Verification output (paste FULL command + output, unedited):

Command (run via cmd batch file, per Task 0 Verify block, after `cd /d D:\habesha-names && call .venv\Scripts\activate.bat`):

    pip install -e .[dev] && python -c "import habesha_names; print(habesha_names.__version__)" && pytest -q && ruff check . && mypy src

Output (final run, exit code 0):

    Obtaining file:///D:/habesha-names
      Installing build dependencies: started
      Installing build dependencies: finished with status 'done'
      Checking if build backend supports build_editable: started
      Checking if build backend supports build_editable: finished with status 'done'
      Getting requirements to build editable: started
      Getting requirements to build editable: finished with status 'done'
      Preparing editable metadata (pyproject.toml): started
      Preparing editable metadata (pyproject.toml): finished with status 'done'
    Requirement already satisfied: pytest in d:\habesha-names\.venv\lib\site-packages (from habesha-names==0.1.0.dev0) (9.1.1)
    Requirement already satisfied: ruff in d:\habesha-names\.venv\lib\site-packages (from habesha-names==0.1.0.dev0) (0.15.21)
    Requirement already satisfied: mypy in d:\habesha-names\.venv\lib\site-packages (from habesha-names==0.1.0.dev0) (2.2.0)
    Requirement already satisfied: typing_extensions>=4.6.0 in d:\habesha-names\.venv\lib\site-packages (from mypy->habesha-names==0.1.0.dev0) (4.16.0)
    Requirement already satisfied: mypy_extensions>=1.0.0 in d:\habesha-names\.venv\lib\site-packages (from mypy->habesha-names==0.1.0.dev0) (1.1.0)
    Requirement already satisfied: pathspec>=1.0.0 in d:\habesha-names\.venv\lib\site-packages (from mypy->habesha-names==0.1.0.dev0) (1.1.1)
    Requirement already satisfied: librt>=0.12.0 in d:\habesha-names\.venv\lib\site-packages (from mypy->habesha-names==0.1.0.dev0) (0.13.0)
    Requirement already satisfied: ast-serialize<1.0.0,>=0.6.0 in d:\habesha-names\.venv\lib\site-packages (from mypy->habesha-names==0.1.0.dev0) (0.6.0)
    Requirement already satisfied: colorama>=0.4 in d:\habesha-names\.venv\lib\site-packages (from pytest->habesha-names==0.1.0.dev0) (0.4.6)
    Requirement already satisfied: iniconfig>=1.0.1 in d:\habesha-names\.venv\lib\site-packages (from pytest->habesha-names==0.1.0.dev0) (2.3.0)
    Requirement already satisfied: packaging>=22 in d:\habesha-names\.venv\lib\site-packages (from pytest->habesha-names==0.1.0.dev0) (26.2)
    Requirement already satisfied: pluggy<2,>=1.5 in d:\habesha-names\.venv\lib\site-packages (from pytest->habesha-names==0.1.0.dev0) (1.6.0)
    Requirement already satisfied: pygments>=2.7.2 in d:\habesha-names\.venv\lib\site-packages (from pytest->habesha-names==0.1.0.dev0) (2.20.0)
    Building wheels for collected packages: habesha-names
      Building editable for habesha-names (pyproject.toml): started
      Building editable for habesha-names (pyproject.toml): finished with status 'done'
      Created wheel for habesha-names: filename=habesha_names-0.1.0.dev0-0.editable-py3-none-any.whl size=2843 sha256=3ed34221a349a56efe866dba3f1dfe73d8f617e44d511a465c8c6859fed3141b
      Stored in directory: C:\Users\Administrator\AppData\Local\Temp\pip-ephem-wheel-cache-9danexhv\wheels\01\7a\05\255e024fbd36bdc12b2145c8d59405d105f6568aa8fd48ad91
    Successfully built habesha-names
    Installing collected packages: habesha-names
      Attempting uninstall: habesha-names
        Found existing installation: habesha-names 0.1.0.dev0
        Uninstalling habesha-names-0.1.0.dev0:
          Successfully uninstalled habesha-names-0.1.0.dev0
    Successfully installed habesha-names-0.1.0.dev0

    [notice] A new release of pip is available: 24.3.1 -> 26.1.2
    [notice] To update, run: python.exe -m pip install --upgrade pip
    0.1.0.dev0
    ..                                                                       [100%]
    2 passed in 0.03s
    All checks passed!
    Success: no issues found in 6 source files
    EXIT CODE: 0

Files touched: `pyproject.toml`, `LICENSE`, `.gitignore`, `README.md`, `src/habesha_names/__init__.py`, `src/habesha_names/py.typed`, `src/habesha_names/{fidel,translit,parse,match,data}/__init__.py`, `tests/test_smoke.py`, `.github/workflows/ci.yml`, `PROGRESS.md`

Deviations from plan (and why):
- Local Python is 3.13.2, not 3.11 as AGENT_KICKOFF.md states. All verification ran on 3.13.2; CI matrix still covers 3.9–3.13.
- The first verify run passed (exit 0) but mypy 2.2.0 warned `python_version: Python 3.9 is not supported (must be 3.10 or higher)` — mypy 2.x dropped 3.9 as a check target, so the pin was silently ignored. Removed `python_version = "3.9"` from `[tool.mypy]`; each CI job type-checks against its own interpreter, and the 3.9 matrix job (which resolves an older mypy) covers 3.9 semantics. Re-ran the full Verify block clean (output above).
- `data/` was given a docstring-only `__init__.py` (regular package, not a bare directory) so `importlib.resources` works uniformly on Python 3.9 when Task 4 lands.
- PyPI availability was verified via the JSON API instead of the project HTML page — the HTML page serves an anti-bot challenge (HTTP 200 "Client Challenge") to curl, making its status code meaningless.

Known issues / TODOs introduced: none. CI workflow is committed but has never executed (no remote configured yet) — first push to GitHub should confirm the matrix is green.

Next session should start with: Task 1 — Fidel tables + syllable decomposition (`scripts/gen_fidel_tables.py`, generated `fidel/tables.py`, `fidel/syllable.py`).

## Session 2 — 2026-07-10

Task attempted: Task 1 — Fidel tables + syllable decomposition

What was actually done:
- Explored the real Unicode structure of U+1200–U+137F and U+1380–U+139F via a scratchpad script (`unicodedata` 15.1.0) before writing anything: 342 syllables, 42 non-syllable codepoints (marks/punct/digits/tonal). Three structural irregularities found and handled: U+131F GGWAA uses eighth-column suffix `WAA`; U+1359 MYA and U+135A FYA are standalone one-off syllables inside the RYA row; supplement block is 4-aligned groups (orders 1/3/5/6) with a `SEBATBEIT ` name prefix on each group base.
- `scripts/gen_fidel_tables.py`: derives every mapping from `unicodedata.name()` (nothing hand-typed), validates block structure (fails loudly on unknown suffixes / misaligned orders / label collisions / non-bijective reverse table), emits `src/habesha_names/fidel/tables.py` with a GENERATED header; `--check` mode diffs regenerated output against the committed file.
- Generated `fidel/tables.py`: `ETHIOPIC_RANGES`, `LABIALIZED_ORDER`, `CONSONANT_BY_BASE` (50 series), `SYLLABLES` (342 entries, codepoint → (consonant label, order 1–8)), `CODEPOINT_BY_SYLLABLE` (reverse bijection).
- `fidel/syllable.py`: `Syllable` NamedTuple, `decompose`, `compose`, `is_ethiopic` (block-range based; whitespace ignored, mixed script → False), all with runnable docstring examples using only plan-given glyphs.
- `tests/test_fidel_syllable.py`: 15 tests — the 5 plan pin glyphs each cross-checked against `unicodedata.name` inside the test; full-table roundtrip; independent unicodedata scan proving table coverage is exact; independent re-derivation of series/orders from Unicode names; error paths; `is_ethiopic` cases.
- Consonant labels are mechanical lowercased Unicode fragments except one override `TS → "ts'"` (plan-pinned, ejective) — flagged `verified: false` in the generator and generated header, added to Human review queue.

Verification output (paste FULL command + output, unedited):

Command (cmd, per Task 1 Verify block, after `cd /d D:\habesha-names && call .venv\Scripts\activate.bat`):

    python scripts\gen_fidel_tables.py --check && pytest tests\test_fidel_syllable.py -q && mypy src && echo EXIT CODE: %ERRORLEVEL%

Output (final run):

    OK: tables.py is current (342 syllables, 50 series)
    ...............                                                          [100%]
    15 passed in 0.06s
    Success: no issues found in 8 source files
    EXIT CODE: 0

Full repo gate also run clean in the same session (`ruff check . && pytest -q && mypy src`):

    All checks passed!
    .................                                                        [100%]
    17 passed in 0.10s
    Success: no issues found in 8 source files
    EXIT CODE: 0

Files touched: `scripts/gen_fidel_tables.py` (new), `src/habesha_names/fidel/tables.py` (generated, new), `src/habesha_names/fidel/syllable.py` (new), `tests/test_fidel_syllable.py` (new), `PROGRESS.md`

Deviations from plan (and why):
- Plan says "series bases → … vowel orders, labialized forms" without prescribing shape: labialized forms are represented as vowel order 8 (`LABIALIZED_ORDER`) within their parent series rather than as separate series, because Unicode lays them out at row offset 7 (suffixes -WA/-OA/-WAA); the five labialized-velar series (qw/qhw/xw/kw/kxw/gw at their own row bases) and the four supplement series (mw/bw/fw/pw) ARE separate series, matching Unicode structure.
- `ETHIOPIC_RANGES` includes Ethiopic Extended U+2D80–U+2DDF (per ARCHITECTURE §4.1 Unicode coverage) so `is_ethiopic` recognizes it; it has no syllable table in v0.1 (Task 1 scope is the two blocks named in the plan), so `decompose` raises ValueError for it — documented and tested.

Known issues / TODOs introduced: consonant labels for non-obvious series (hh/x/sz/tz/qh/kx/dd/gg/th/ch/ph/glottal/pharyngeal…) are internal Unicode-derived IDs, not romanizations — Task 3's PRACTICAL scheme must not blindly reuse them (queued for human review above).

Next session should start with: Task 2 — Fidel normalization (`fidel/normalize.py`: homophone collapsing via decompose/compose, NFC, Ethiopic punctuation strip, whitespace normalize, idempotency property test).

## Session 3 — 2026-07-11

Task attempted: Task 2 — Fidel normalization

What was actually done:
- Scratchpad exploration first (same discipline as Session 2): confirmed via `unicodedata` 15.1.0 that every vowel order of the four collapse sources (hh, x, sz, tz, pharyngeal — orders 1–8, pharyngeal 1–7) has a same-order target in its destination series, so the collapse is total and `compose` can never fail; Ethiopic punctuation is exactly U+1360–U+1368 (all category Po); both tabled blocks are NFC-stable.
- `src/habesha_names/fidel/normalize.py`: `normalize(text)` = NFC → homophone collapse → Ethiopic punctuation handling → whitespace collapse/trim. Collapse map (`HOMOPHONE_SERIES`: hh→h, x→h, sz→s, tz→ts', pharyngeal→glottal) is applied per-character via a `str.translate` table built at import from the generated tables (`SYLLABLES` + `CODEPOINT_BY_SYLLABLE`) — no fidel↔codepoint pair hand-typed in source. Wordspace ፡ becomes an ASCII space; the other eight punctuation marks are stripped. Digits, tonal marks, combining marks, Extended block, and non-Ethiopic text pass through (documented in module docstring).
- `tests/test_fidel_normalize.py`: 24 tests — plan-pinned collapses cross-checked against `unicodedata.name`; full-table property tests (order preserved for every collapsed syllable, non-homophones byte-identical, no homophone source survives in output); punctuation set re-derived independently from `unicodedata.category`; idempotency over every assigned Ethiopic codepoint and over plan-given strings; NFC, whitespace, Latin/mixed pass-through, and docstring-example tests. All fidel test strings come from the plan/architecture documents (ኃይለ ሥላሴ, ወይዘሮ ጸሐይ ገብረመድህን, ፀሐይ) — no invented names.

Verification output (paste FULL command + output, unedited):

Command (cmd, per Task 2 Verify block, after `cd /d D:\habesha-names && call .venv\Scripts\activate.bat`):

    pytest tests\test_fidel_normalize.py -q && echo EXIT CODE: %ERRORLEVEL%

Output:

    ........................                                                 [100%]
    24 passed in 0.14s
    EXIT CODE: 0

Full repo gate also run clean in the same session (`ruff check . && pytest -q && mypy src`):

    All checks passed!
    .........................................                                [100%]
    41 passed in 0.17s
    Success: no issues found in 9 source files
    EXIT CODE: 0

Files touched: `src/habesha_names/fidel/normalize.py` (new), `tests/test_fidel_normalize.py` (new), `PROGRESS.md`

Deviations from plan (and why):
- Plan says "Ethiopic punctuation strip"; U+1361 ETHIOPIC WORDSPACE ፡ is converted to an ASCII space instead of deleted, because it is a word separator — deleting it would merge two name tokens into one (e.g. ወይዘሮ፡ጸሐይ would become one token). The other eight marks (U+1360, U+1362–U+1368) are stripped as specified.
- The labialized (order-8) members of the collapsed series map mechanically along with orders 1–7 (ሗ→ሇ etc.) since the plan pins "preserving vowel order"; queued for human review above because ሇ is a rare character and I cannot verify the homophony as a non-speaker.

Known issues / TODOs introduced:
- Combining gemination/vowel-length marks (U+135D–U+135F) pass through `normalize` untouched; whether matching should strip them is a Task 6/8 (or human) decision, not taken here.
- Labialized-velar series ኈ/ቘ/ዀ not collapsed (queued for Robel above).

Next session should start with: Task 3 — Transliteration practical scheme (`translit/schemes.py` PRACTICAL table seeded from generated consonant labels + marked `verified: false`, `translit/to_latin.py` `transliterate()`; round-trip sanity on ተስፋዬ→Tesfaye, ገብረመድህን→Gebremedhin, ጸሐይ→Tsehay, ኃይለ ሥላሴ→Haile Selassie). Note for Task 3: `normalize` collapses ፀ→ጸ and ኃ→ሃ first, so the PRACTICAL table only needs Latin values for the canonical (post-collapse) series if transliteration normalizes first — decide and document.

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-07-10 | stdlib-only runtime, MIT, src layout | ARCHITECTURE §2 |
| 2026-07-10 | fidel tables generated, never hand-typed | Hallucination risk |
| 2026-07-10 | all agent-seeded linguistic data ships `verified: false` | Native-speaker gate |
| 2026-07-10 | no `python_version` pin in `[tool.mypy]` | mypy 2.x dropped 3.9 as a check target; CI 3.9 job covers 3.9 semantics |
| 2026-07-10 | PEP 639 license metadata (`license = "MIT"`, setuptools>=77) | Table-form `license` is deprecated/being removed in setuptools |
| 2026-07-10 | Labialized fidel = vowel order 8 within its series (`LABIALIZED_ORDER`) | Matches Unicode row layout (offset 7, -WA/-OA/-WAA names); keeps decompose/compose a clean bijection |
| 2026-07-10 | Consonant labels = lowercased Unicode name fragments + minimal override map (`TS→ts'`) | Mechanical derivation carries zero hallucination risk; overrides are flagged linguistic data |
| 2026-07-10 | `is_ethiopic` is block-range based (incl. Extended, punct, digits, marks); all-non-whitespace-chars semantics | Simple, deterministic; parser does finer-grained script detection in Task 5 |
| 2026-07-11 | Homophone collapse = series-label map applied via `str.translate` table built at import from generated tables | Mechanical derivation, zero hand-typed fidel; O(1) per char |
| 2026-07-11 | ፡ wordspace → ASCII space; other Ethiopic punct (U+1360, U+1362–U+1368) stripped; punct set derived from `unicodedata.category` | ፡ is a word separator — stripping it would merge name tokens |
| 2026-07-11 | `normalize` passes through digits/tonal/combining marks/Extended block and never raises | Task 2 scope is exactly the plan's four collapses + punct + whitespace; safety on arbitrary input |

## Known issues

_(none yet)_
