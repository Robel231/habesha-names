# PROGRESS — `habesha-names`

> Agent: read this file FIRST every session. Update it LAST every session. A task without pasted verification output is NOT done, regardless of what any previous session claims.

## Status board

| Task | Title | Status | Verified evidence |
|---|---|---|---|
| 0 | Repo scaffold + CI | ✔ VERIFIED (evidence below) | Session 1, 2026-07-10 · human-verified by Robel 2026-07-11 |
| 1 | Fidel tables + syllables | ✔ VERIFIED (evidence below) | Session 2, 2026-07-10 · human-verified by Robel 2026-07-11 |
| 2 | Fidel normalization | ✔ VERIFIED (evidence below) | Session 3, 2026-07-11 · human-verified by Robel 2026-07-11 (41 passed, ruff/mypy clean, normalize() spot-checked on "ወይዘሮ ፀሐይ ገብረመድህን።") |
| 3 | Transliteration (practical) | ✔ VERIFIED (evidence below) | Session 4, 2026-07-11 |
| 4 | Data layer + seed lexicons | ✔ VERIFIED (evidence below) | Session 5, 2026-07-11 |
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
- [ ] `translit/schemes.py` PRACTICAL table — native-speaker review. Every default below is agent-chosen (`verified: false`), Session 4, 2026-07-11. Robel decides each:
  - [ ] **ቀ series → "k"** (as in Kenenisa, Kelemu — practical spelling merges ejective k' into k). Alternatives considered: "q" (preserves the distinction, common in Eritrean/Tigrinya contexts). Task 7's variant engine emits q↔k either way.
  - [ ] **6th-order vowel (ə)**: bare consonant when word-final or after a vowel; epenthetic **"i"** appended when word-initial or after a consonant. This is the smallest rule reproducing the plan seeds: ተስፋዬ→Tesfaye (bare after vowel), ገብረመድህን→Gebremedhin ("i" after consonant), ጸሐይ→Tsehay (bare final), ስላሴ→Silase ("i" initial). Alternatives: always "i", always "e", always dropped, cluster-counting insertion. **Known imperfection**: word-final is always bare, so word-final clusters lose the vowel (e.g. ፍቅር would come out "Fikr", not "Fikir") — decide whether final clusters should epenthesize.
  - [ ] **ጸ series → "ts" + vowel** across all orders (tse/tsu/tsi/tsa/tse/ts[+i]/tso/tswa). Alternatives: "s" (Sehay), "tz" (Tzehay). Picked "ts" because the plan's canonical form is Tsehay; variants engine covers ts↔s↔tz.
  - [ ] **ቸ and ጨ both → "ch"** (deliberate lossy collision — practical spelling doesn't distinguish them). Alternatives: ጨ → "ch'" (violates no-apostrophe practical contract), "tch", "c".
  - [ ] **ኘ → "gn"** (as in Agegnehu, "Tigrigna"). Alternative: "ny" (as in "Tigrinya"). Note: "gn" output is ambiguous with a genuine g+n letter sequence in Latin-side matching; "ny" would avoid that.
  - [ ] **Labialized romanization**: order-8 column → consonant + "wa" (ሏ→lwa, ሟ→mwa; -OA forms like ሇ also →"wa"; ኧ→"wa"). Separate labialized-velar series: ቈ qw→"kw" (follows q→k), ኰ kw→"kw", ጐ gw→"gw" (ጓ→gwa), ኈ xw→"hw" (ኋ→hwa), ዀ kxw→"hw", ቘ qhw→"qw"; Sebatbeit ᎀᎄᎈᎌ → "mw/bw/fw/pw". Alternatives: "ua"/"we" renderings (ኋላ → Huala vs Hwala).
  - [ ] **Guttural order-1 → "a"** for h and glottal series only (ሀ→"ha", አ→"a"; yields Tsehay, Haile, Abebe instead of *Tsehey, *Hey…). Question: should ኸ (kx→"h") and ኈ/ዀ (hw) also count as guttural for order 1 ("ha"/"hwa" vs current "he"/"hwe")?
  - [ ] **6th-order የ glide**: after a vowel → "i" word-medially (ኃይለ→Haile, ወይዘሮ→Weizero) but "y" word-finally (ጸሐይ→Tsehay). Alternatives: always "y" (→Hayle), "i" finally too (→Tsehai). Variant engine covers -ay↔-ai↔-aye.
  - [ ] **ወ order 1 → "we"** → ወይዘሮ comes out "Weizero", but the conventional title form is "Woizero" (Task 4 titles list). Alternative: w,1 → "wo" (fixes the title, changes every other ወ). Decide before Task 4 seeds titles.json.
  - [ ] **Order-5 é → plain "e"** (ሴ→"se"). Conventional "Selassie" spells it "ie" — not derivable from a general table, and the "ss" gemination is unmarked in fidel, so the plan's ኃይለ ሥላሴ→"Haile Selassie" round-trip is **xfail** (table yields "Haile Silase"; no silent special-case added, per kickoff). Alternatives: é→"ie" or "ee" globally.
  - [ ] **Remaining consonant defaults** (all flagged): ጠ th→"t" (Taitu), ጰ ph→"p" (Paulos), ቐ qh→"q", ኸ kx→"h" (alt "kh"), ዠ zh→"zh" (alt "j"), ዸ dd→"dh" (Oromo dh), ጘ gg→"ng", ፘ/ፙ/ፚ ry/my/fy→"rya/mya/fya", አ glottal→vowel only, ቨ v→"v", ፐ p→"p" (collides with ጰ).
- [ ] `data/titles.json` (Task 4, Session 5) — all 12 entries agent-seeded (`verified: false`). The Latin canonicals are plan-pinned (Ato, Woizero, W/ro, …); everything else needs review: fidel spellings (esp. **Sheikh → ሼህ**, alternatives ሼክ/ሸይኽ; **Haji → ሀጂ**, often written ሐጂ — normalize collapses both), fidel slash abbreviations (ወ/ሮ, ወ/ሪት, ዶ/ር, መ/ር), the Latin abbreviation lists, category assignments (**Memhir → "professional"** — could be academic or religious), and gender flags (Qes/Abba/Abune/Sheikh/Haji marked `m`; Dr/Prof/Eng/Memhir `null`).
- [ ] `data/compounds.json` (Task 4, Session 5) — prefixes and second elements are exactly the ARCHITECTURE §4.3 lists, but the fidel spellings are agent-typed (esp. Zera ዘርአ, Egziabher እግዚአብሔር, Hiwot ሕይወት, Tsadik ጻድቅ). Prefix genders: all `m` except Welete `f` — confirm. **ALL abbreviation-expansion weights are invented**: G/→Gebre 0.8 / Girma 0.2 (ratio from the ARCHITECTURE example, magnitude mine); W/→Wolde 0.6 / Welete 0.4; H/T/K/B/F/Z/A single-candidate 1.0 — are other expansions common (e.g. H/→Habte, T/→Tesfa)?
- [ ] `data/given_names.json` (Task 4, Session 5) — 56 entries, **every field agent-guessed**: fidel spelling, canonical Latin, variants list, gender distribution (all 1.0 single-gender except Tsehay 0.97/0.03 from the ARCHITECTURE example and Selam 0.9/0.1), origin tags (amharic/tigrinya/geez/arabic/biblical/oromo), freq_tier 1–3. Mechanical cross-check `transliterate(fidel)` vs canonical ran in Session 5: **39 OK, 11 = a listed variant, 6 mismatches** for Robel to adjudicate (fidel typo vs. canonical spelling vs. engine rule):
  - ኃይለማርያም → "Hailemaryam" vs canonical "Hailemariam" (ya-rendering; same for second element ማርያም → "Maryam" vs "Mariam")
  - መሐመድ → "Mehamed" vs "Mohammed" (no plain fidel form yields "Mo-"; Task 7's Arabic-origin table covers the variants)
  - ትግስት → "Tigsit", ቅድስት → "Kidsit" (6th-order epenthetic "i" lands after the wrong consonant in C₁C₂-final clusters — same family as the ፍቅር→"Fikr" issue from Session 4)
  - ዮሐንስ → "Yohans" vs "Yohannes"; ዳንኤል → "Danel" vs "Daniel"
  - Second elements not matching their Latin: ሚካኤል→"Mikael" (Michael), ጊዮርጊስ→"Giyorgis" (Giorgis), ክርስቶስ→"Kirsitos" (Kristos), እግዚአብሔር→"Igziabher" (Egziabher), ሕይወት→"Hiiwet" (Hiwot — the የ-glide-after-"i" rule doubles the i), ሃይማኖት→"Haimanot" (Haymanot), ጻድቅ→"Tsadk" (Tsadik), ሥላሴ→"Silase" (known xfail). Titles: ወይዘሮ→"Weizero" (known ወ we/wo item), ሼህ→"Sheh", and the Dr/Prof/Eng loanwords ዶክተር/ፕሮፌሰር/ኢንጂነር→"Dokter"/"Pirofeser"/"Injiner" (expected — titles are matched by lexicon lookup, not transliteration).
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

## Session 4 — 2026-07-11

Task attempted: Housekeeping (per session kickoff) + Task 3 — Transliteration (practical scheme, fidel → Latin)

What was actually done:
- Housekeeping: status board now records Robel's human verification of Tasks 0–2; AGENT_KICKOFF.md environment section documents `check.bat` as the full gate. Committed separately (`housekeeping: record human verification of tasks 0-2, adopt check.bat gate`) so the task commit stays single-purpose.
- `src/habesha_names/translit/schemes.py`: `PRACTICAL` table `(consonant label, vowel order) → Latin`, built at import by crossing `_CONSONANTS` (45 post-collapse series → Latin onset) × `_VOWELS` (order → vowel) over exactly the syllables in the generated `SYLLABLES` table — no hand-typed fidel↔Latin pair, coverage is testable. Per the kickoff hard requirement, series collapsed by `normalize()` (hh ሐ, x ኀ, sz ሠ, tz ፀ, pharyngeal ዐ) have NO rows. `verified: false` header comment; `SCHEMES` registry holds only `"practical"` in v0.1.
- `src/habesha_names/translit/to_latin.py`: `transliterate(text, scheme="practical")` — calls `normalize()` first, unconditionally; per-word rendering with three context rules (all flagged unverified): 6th-order ə bare when word-final/after-vowel else +epenthetic "i"; 6th-order የ glide "i" medial / "y" final after a vowel; guttural (h, glottal) order-1 vowel "a". Fidel-initial words are name-cased; Latin/digits/marks/Extended pass through. Unknown scheme → `ValueError`.
- `tests/test_translit_latin.py`: 21 tests — pinned invariant `transliterate("ፀሐይ") == transliterate("ጸሀይ") == "Tsehay"` (chars cross-checked via `unicodedata.name`); plan round-trips Tesfaye/Gebremedhin/Tsehay; ኃይለ ሥላሴ→"Haile Selassie" marked `xfail(strict=True)` with logged reason (see deviations) plus a behavior pin of the actual "Haile Silase" output and a passing "ኃይለ"→"Haile" check; full-table property tests (every homophone-source syllable transliterates identically to its target; table covers exactly the post-collapse syllables; no collapsed-series rows; ASCII-lowercase-only cells); normalize-first equivalence; passthrough/casing/scheme/empty/stability/doctest tests.
- Review queue: expanded the PRACTICAL-table item with 12 decision sub-items (ቀ, 6th-order ə, ጸ, ቸ/ጨ, ኘ, labialized forms, guttural order-1, የ glide, ወ "we"/"wo", order-5 é + Selassie conflict, remaining consonants), each with alternatives considered and the rationale for the default.

Verification output (paste FULL command + output, unedited):

Task 3 Verify block (cmd, after `call .venv\Scripts\activate.bat`):

    pytest tests\test_translit_latin.py -q && echo EXIT CODE: %ERRORLEVEL%

Output:

    ....x................                                                    [100%]
    20 passed, 1 xfailed in 0.57s
    EXIT CODE: 0

Full repo gate (`D:\habesha-names\check.bat` = pytest -q && ruff check . && mypy src, inside .venv):

    .............................................x................           [100%]
    61 passed, 1 xfailed in 0.44s
    All checks passed!
    Success: no issues found in 11 source files
    EXIT CODE: 0

Files touched: `src/habesha_names/translit/schemes.py` (new), `src/habesha_names/translit/to_latin.py` (new), `tests/test_translit_latin.py` (new), `PROGRESS.md`, plus housekeeping commit (`AGENT_KICKOFF.md`, `PROGRESS.md` status board, `check.bat` first tracked).

Deviations from plan (and why):
- Plan round-trip ኃይለ ሥላሴ→"Haile Selassie" is `xfail(strict=True)`, not passing: the conventional spelling needs geminated "ss" (gemination is unmarked in fidel) and "ie" for the order-5 vowel (a per-name convention). No table choice produces it without special-casing, which the kickoff forbids. Default output is "Haile Silase" ("Haile" itself matches). Review-queue item added; Robel decides (e.g. é→"ie" globally, lexicon-level exceptions in Task 4, or accept the xfail).
- The 6th-order epenthetic vowel and glide handling live as context rules in `to_latin.py` rather than as static table cells (a cell can't see word position); the table's order-6 cells hold the bare consonant and the rules are documented in both module docstrings.
- `check.bat` had to be invoked by absolute path in this session's shell harness (`cmd /c D:\habesha-names\check.bat`); relative invocation was not resolved. Contents ran unmodified.

Known issues / TODOs introduced:
- Word-final 6th-order consonants never epenthesize → word-final clusters lose their vowel (ፍቅር-style names would come out "Fikr"). Flagged in the review queue; revisit with Robel's 6th-order decision.
- "Weizero" (ወይዘሮ) vs conventional "Woizero" mismatch — must be settled before Task 4 seeds `titles.json`.

Next session should start with: Task 4 — Data layer (`data/schema.md`, `titles.json`, `compounds.json`, `given_names.json` all `"verified": false`, lazy loader `_data.py`). Check the review queue first in case Robel has decided the ወ/ኘ/ቀ defaults — titles.json spellings depend on them.

## Session 5 — 2026-07-11

Task attempted: Task 4 — Data layer + seed lexicons

What was actually done:
- `src/habesha_names/data/schema.md`: contracts for the three JSON files, the `verified` workflow (agent seeds `false`, only Robel flips), general loader-enforced rules (exact keys, Ethiopic-script fidel, NFC, ASCII Latin, weights/gender sums = 1, duplicates rejected, file order = canonical order), and a per-entry review checklist for Robel.
- `src/habesha_names/data/titles.json`: 12 entries — exactly the plan list (Ato, Woizero/W-ro, Woizerit/W-rt, Dr, Prof, Eng, Qes, Abba, Abune, Memhir, Sheikh, Haji) with fidel forms incl. slash abbreviations (ወ/ሮ etc.). Latin canonical spellings come from the plan itself, so this did NOT need the still-open ወ→we/wo transliteration decision; ወይዘሮ stays canonical "Woizero" regardless of what `transliterate` outputs.
- `src/habesha_names/data/compounds.json`: the exact ARCHITECTURE §4.3 prefix list (10, Welete marked `f`) and second-element list (12), plus 9 slash-abbreviation expansions with weights (G/→Gebre 0.8/Girma 0.2 per the architecture's example; the rest agent-invented, flagged).
- `src/habesha_names/data/given_names.json`: 56 entries in the ARCHITECTURE §4.5 contract shape (incl. the ፀሐይ/Tsehay example verbatim), covering every name the plan/architecture tests reference (Tesfaye, Gebremedhin, Tsehay, Abebe, Bikila, Wolde, Hailemariam, Desalegn, Girma, Mohammed, Hussein, Fatuma, Kebede, Alemu, Almaz, Tesfahun, Abebech, Bethlehem, …) plus high-frequency seeds. ALL `"verified": false`.
- `src/habesha_names/_data.py`: lazy singleton loader (`@cache`, `importlib.resources`), frozen dataclasses (`Title`, `CompoundPrefix`, `CompoundSecond`, `AbbreviationExpansion`, `GivenName`, `Lexicon`), strict validation raising `LexiconError` (exact-key checks, type checks, `is_ethiopic` + NFC on every fidel value, gender/weight distributions sum to 1, weights non-increasing, case-insensitive duplicate rejection, cross-file check that every abbreviation expansion resolves to a known prefix or given name).
- `tests/test_data_loader.py`: 54 tests — lazy-singleton behavior; plan/architecture pins (title list, prefix/second lists, G/-expansion ranking, Tsehay contract example, seed-name presence, ≥50 entries, ALL unverified); whole-lexicon invariants (Ethiopic fidel, gender sums, no duplicates, variants ≠ canonical, abbreviations resolve + ranked); plan-pinned translit consistency (Tesfaye/Gebremedhin/Tsehay fidel → canonical); 34 malformed-payload cases against the pure `_parse_*` functions; doctests.
- Scratchpad cross-check script (Session-2 discipline): transliterated every agent-typed fidel string and compared against intended Latin — results pasted into the Human review queue above (39 OK / 11 variant / 6 mismatch for given names; all title/compound mismatches itemized). No LexiconError on real data, i.e. every typed string is valid NFC Ethiopic.

Verification output (paste FULL command + output, unedited):

Task 4 Verify block (cmd, after `call .venv\Scripts\activate.bat`):

    pytest tests\test_data_loader.py -q && python -c "from habesha_names._data import lexicon; print(len(lexicon().given_names))" && echo EXIT CODE: %ERRORLEVEL%

Output:

    ......................................................                   [100%]
    54 passed in 0.28s
    56
    EXIT CODE: 0

Full repo gate (`D:\habesha-names\check.bat` = pytest -q && ruff check . && mypy src, inside .venv):

    ........................................................................ [ 62%]
    ...........................x................                             [100%]
    115 passed, 1 xfailed in 0.70s
    All checks passed!
    Success: no issues found in 12 source files
    EXIT CODE: 0

(The first check.bat run failed ruff with 4 UP045/UP033 findings in the new `_data.py`; fixed via `ruff check --fix --unsafe-fixes` — `Optional[str]`→`str | None`, `lru_cache(maxsize=None)`→`cache`, both 3.9-safe — then the gate above ran clean.)

Files touched: `src/habesha_names/data/schema.md` (new), `src/habesha_names/data/titles.json` (new), `src/habesha_names/data/compounds.json` (new), `src/habesha_names/data/given_names.json` (new), `src/habesha_names/_data.py` (new), `tests/test_data_loader.py` (new), `PROGRESS.md`

Deviations from plan (and why):
- Plan says "~50" given names; shipped 56 so that every name referenced by plan/architecture test cases (Tasks 3/5/6/7) exists in the lexicon alongside the high-frequency seeds.
- Data files carry a top-level `{"schema": 1, ...}` wrapper (not specified by the plan) so future contract changes are detectable at load; the entry shape itself follows ARCHITECTURE §4.5 exactly.
- `given_names.json` fidel forms are stored as conventionally written (ፀሐይ, ኃይለ), NOT pre-collapsed, per schema.md — consumers normalize at comparison time. The loader enforces NFC but deliberately not homophone-collapsedness.

Known issues / TODOs introduced:
- The 6 given-name translit mismatches + second-element mismatches (review queue above) are data-vs-engine conflicts for Robel; none block Task 5 (the parser matches lexicon strings, it does not re-transliterate).
- Two engine-rule weaknesses surfaced by the cross-check (not fixed here — out of Task 4 scope, related to open review-queue items): 6th-order epenthesis in C₁C₂-final clusters (ትግስት→"Tigsit") and የ-glide after "i" doubling the vowel (ሕይወት→"Hiiwet").
- Per the updated session protocol, nothing was committed: tree left ready for Robel. Suggested commit message: `task-4: data layer + seed lexicons (schema, titles, compounds, given names, validated lazy loader)`.

Next session should start with: Task 5 — Parser (`parse/titles.py`, `parse/compounds.py` incl. G/Medhin expansion, `parse/parser.py` → `ParsedName`). The lexicon now contains every name the Task 5 test list needs; check the review queue first in case Robel has flipped any Task 4 decisions.

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
| 2026-07-11 | `transliterate()` normalizes first, unconditionally; PRACTICAL has no rows for collapsed series | Kickoff hard requirement; homophone identity holds by construction, one source of truth |
| 2026-07-11 | PRACTICAL built at import as `_CONSONANTS` × `_VOWELS` over the generated `SYLLABLES` | No hand-typed fidel↔Latin cells; exact-coverage property test possible |
| 2026-07-11 | 6th-order ə: bare if word-final/after-vowel, else +"i"; የ glide i/y; guttural (h, glottal) order-1 "a" | Smallest context-rule set reproducing all plan round-trip seeds; all flagged for review |
| 2026-07-11 | ኃይለ ሥላሴ→"Haile Selassie" = strict xfail, no special-case | Gemination + "ie" not table-derivable; kickoff forbids silent special-casing |
| 2026-07-11 | Fidel-initial words name-cased in output; non-Ethiopic tokens byte-preserved | It's a names library; must not mangle Latin/mixed input |
| 2026-07-11 | Data files: `{"schema": 1, ...}` wrapper + exact-key validation, `LexiconError` at load | Typo safety for hand-edited linguistic data; fail loudly, never corrupt matching |
| 2026-07-11 | Loader = `@cache` lazy singleton over `importlib.resources`; the library's only stateful component | ARCHITECTURE §2; deterministic frozen dataclasses |
| 2026-07-11 | titles.json canonical Latin = plan-pinned spellings ("Woizero"), independent of the open ወ→we/wo translit default | Plan Task 4 list is the source of truth for title spellings; titles are matched by lookup, not transliteration |
| 2026-07-11 | Lexicon fidel stored as conventionally written (ፀሐይ), NFC-enforced, NOT pre-collapsed | Reviewers see real spellings; normalize() is applied by consumers at comparison time |
| 2026-07-11 | Abbreviation expansions must resolve to a known prefix or given-name canonical (cross-file check) | Catches dangling references (e.g. G/→"Girma" requires Girma in the lexicon) at load |

## Known issues

_(none yet)_
