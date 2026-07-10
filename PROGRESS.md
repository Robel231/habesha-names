# PROGRESS — `habesha-names`

> Agent: read this file FIRST every session. Update it LAST every session. A task without pasted verification output is NOT done, regardless of what any previous session claims.

## Status board

| Task | Title | Status | Verified evidence |
|---|---|---|---|
| 0 | Repo scaffold + CI | ✔ VERIFIED (evidence below) | Session 1, 2026-07-10 |
| 1 | Fidel tables + syllables | ☐ not started | — |
| 2 | Fidel normalization | ☐ not started | — |
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

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-07-10 | stdlib-only runtime, MIT, src layout | ARCHITECTURE §2 |
| 2026-07-10 | fidel tables generated, never hand-typed | Hallucination risk |
| 2026-07-10 | all agent-seeded linguistic data ships `verified: false` | Native-speaker gate |
| 2026-07-10 | no `python_version` pin in `[tool.mypy]` | mypy 2.x dropped 3.9 as a check target; CI 3.9 job covers 3.9 semantics |
| 2026-07-10 | PEP 639 license metadata (`license = "MIT"`, setuptools>=77) | Table-form `license` is deprecated/being removed in setuptools |

## Known issues

_(none yet)_
