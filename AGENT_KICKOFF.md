# AGENT_KICKOFF — `habesha-names`

You are the implementation agent for **habesha-names**, an open-source Python library for Ethiopian/Eritrean name intelligence: fidel script handling, transliteration, spelling-variant generation, name parsing, and patronymic-aware fuzzy matching. Target users are global KYC/AML, remittance, HR, and entity-resolution systems. This library must be boring, correct, and dependency-free — think `phonenumbers`, not a demo.

## Ground truth documents (read in this order, every session)
1. `PROGRESS.md` — current state. Trust ONLY tasks marked `✔ VERIFIED` with pasted evidence.
2. `IMPLEMENTATION_PLAN.md` — your task list with per-task Verify commands.
3. `ARCHITECTURE.md` — module contracts, data schemas, design principles.

## Environment (do not deviate)
- Windows, **cmd shell — NOT PowerShell**. Use `\` paths, `&&` chaining, `venv\Scripts\activate.bat`.
- Repo: `D:\habesha-names`. Python 3.11 local, CI matrix 3.9–3.13.
- Runtime dependencies: **stdlib only. Zero exceptions.** Dev deps limited to pytest, ruff, mypy.
- All verification commands run inside `.venv` — use `check.bat` at repo root (pytest -q && ruff check . && mypy src) as the full gate.

## Session protocol
1. Read PROGRESS.md. Pick the FIRST task that is not `✔ VERIFIED`. Work ONE task per session.
2. Implement per IMPLEMENTATION_PLAN.md. If the plan and ARCHITECTURE.md conflict, stop and log the conflict in PROGRESS.md instead of guessing.
3. Run the task's **Verify** block. All commands must pass.
4. Update PROGRESS.md: status board, session log entry with the FULL unedited verification output pasted in, files touched, deviations, next step.
5. leave the pushing for me just give the commit message suggestion

## Honesty rules (violations are the #1 historical failure mode)
- **Never mark a task done without pasting passing verification output.** "Should work", "implemented as specified", or describing code you didn't run counts as NOT done.
- If a Verify command fails, the task stays `◐ in progress` or `✕ blocked` — say so plainly.
- If you cannot complete something, write exactly what is missing. Partial + honest beats complete + fictional.
- Never edit or delete previous sessions' log entries.

## Linguistic-data rules (the #2 failure mode: hallucinated Amharic)
- You are NOT a native speaker. The repo owner (Robel) is. Every linguistic data item you produce — lexicon entries, transliteration table cells, variant rules, golden-corpus pairs — ships flagged `"verified": false` or `"needs_human": true` and gets listed in PROGRESS.md → Human review queue.
- Ethiopic Unicode tables must be **generated programmatically** (`scripts/gen_fidel_tables.py`, cross-checked with `unicodedata.name`). Never hand-type fidel↔codepoint mappings from memory.
- Never invent example names for tests beyond those already given in the plan/architecture without flagging them for review.
- When uncertain about a linguistic fact, add a `TODO(human)` and move on — do not fabricate.

## Engineering rules
- src layout, full type hints, `mypy src` clean (Task 9 onward: `--strict`), `ruff check` clean.
- Every public function: docstring with a runnable example.
- Deterministic outputs everywhere — stable sort orders, no randomness, no network calls, no file writes outside the repo.
- Pure functions in `fidel/`, `translit/`, `match/`; state only in the lazy data loader.
- Small commits, meaningful test names, property tests where the plan specifies them.
SESSION START — housekeeping first, then Task 3.

HOUSEKEEPING (do before Task 3, include in the same session):
1. Human verification complete: Tasks 0, 1, and 2 are confirmed VERIFIED by Robel
   (repo-level check: 41 passed, ruff clean, mypy clean, normalize() spot-checked
   on "ወይዘሮ ፀሐይ ገብረመድህን።" → correct collapse, 3 tokens). Update PROGRESS.md
   status board to reflect human verification of Tasks 0–2.
2. A check.bat now exists at repo root (activates .venv, runs pytest -q && ruff
   check . && mypy src). Add to AGENT_KICKOFF.md environment section: "All
   verification commands run inside .venv — use check.bat at repo root."
   Use check.bat as the full gate from now on.

TASK 3 — Practical transliteration scheme (fidel → Latin), per
IMPLEMENTATION_PLAN.md, with these HARD REQUIREMENTS on top of the plan:

1. transliterate() MUST call normalize() first, unconditionally. Consequence:
   the PRACTICAL table only defines cells for post-collapse series (no rows for
   ሐ/ኀ/ሠ/ፀ/ዐ — they can never reach the table).
2. Pinned invariant test required:
   transliterate("ፀሐይ") == transliterate("ጸሀይ")
3. The PRACTICAL table in schemes.py ships with a "verified: false" header
   comment. You are not a native speaker — every non-obvious cell choice must
   be listed in PROGRESS.md → Human review queue WITH the alternatives you
   considered and why you picked your default. At minimum I expect entries for:
   - ቀ series: q vs k
   - 6th-order vowel: rendered "e", "i", or dropped — word-medial vs word-final
   - ጸ series: ts vs tse handling across vowel orders
   - ቸ/ጨ: ch collision handling
   - ኘ: ny/gn choice
   - Any labialized-form romanization
   I decide these, not you. Pick sensible defaults so tests pass, flag them all.
4. Round-trip sanity tests from the plan are mandatory:
   ተስፋዬ→Tesfaye, ገብረመድህን→Gebremedhin, ጸሐይ→Tsehay, ኃይለ ሥላሴ→Haile Selassie.
   If your default table choices can't produce one of these exactly, do NOT
   silently special-case it — log the conflict in PROGRESS.md and mark the test
   xfail with a reason. Table-vs-expected conflicts are review-queue items.

Protocol reminders: one task, run check.bat plus the Task 3 Verify block, paste
full unedited output into PROGRESS.md Session log, commit as
"task-3: practical transliteration (fidel → Latin)". Report which review-queue
items you added.

Read PROGRESS.md first, confirm Task 3 is the first open task, then begin.
## Scope discipline
- v0.1 scope = Tasks 0–10 exactly. v0.2/v0.3 backlog items in IMPLEMENTATION_PLAN.md are forbidden without explicit instruction — do not "improve" ahead.
- Do not add dependencies, CLI entry points, async, plugins, or config files not in the architecture.

## Start now
Read `PROGRESS.md`, report which task you are picking up and why, then begin.
