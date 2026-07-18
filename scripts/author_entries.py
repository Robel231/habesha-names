"""Lexicon authoring pipeline: mined candidates -> filled worksheet -> entries.

Task 17 (IMPLEMENTATION_PLAN_V02). Robel's review hours are the v0.2
bottleneck; this tool packages the mining queue into a file-driven worksheet
(the task-3b ``review_report.txt`` pattern -- no interactive prompts) and
turns the filled worksheet into loader-valid ``given_names.json`` entries.

Flow:

1. ``--emit-worksheet`` reads ``data-lab/reports/candidates.json`` (from
   ``scripts/mine_candidates.py``) and writes
   ``data-lab/reports/authoring_worksheet.json``: per candidate the corpus
   evidence for Robel's eyes (attested spellings, occurrence counts, gender
   evidence) plus blank ``fidel``/``origin`` fields and cross-checks against
   the current lexicon (phonetic-key collisions, near-duplicate spellings).
2. Robel edits the worksheet in his editor: decision accept/reject, fidel,
   origin, gender, tier, pruned variants. His knowledge -- not the corpus --
   is the source of truth (DATA_PROVENANCE.md, "External corpora").
3. ``--validate`` checks the filled worksheet (item shape, loader-valid
   values incl. NFC Ethiopic fidel via the real ``_data`` parser, duplicates
   against the shipped lexicon, ``transliterate(fidel)`` vs canonical
   cross-check with mismatches surfaced) and writes
   ``data-lab/reports/authoring_report.txt`` (open in an editor, not cmd).
   When nothing fatal remains it also writes
   ``data-lab/reports/authored_entries.json``: entries with
   ``"verified": false`` and NO corpus counts, ``_review`` blocks, or
   corpus-derived keys (the provenance firewall). Integration into
   ``src/habesha_names/data/given_names.json`` is a separate agent session
   (Task 18); Robel flips ``verified`` in-repo after final review.

``--selfcheck`` runs the whole pipeline on in-script fixture candidates
under ``data-lab/reports/selfcheck/`` -- no corpus files, no human input.
Fixture fidel/gender/origin values are pulled from the already-verified
packaged lexicon at runtime, because the agent must never hand-type fidel
(AGENT_KICKOFF linguistic-data rules); fixture corpus counts are synthetic.

Deterministic (identical inputs -> byte-identical outputs; provenance lines
are carried from the input files, never re-stamped), stdlib + habesha-names
only, writes only under ``data-lab/reports/``.

Usage:
    python scripts/author_entries.py --emit-worksheet [--top N] [--force]
    python scripts/author_entries.py --validate
    python scripts/author_entries.py --selfcheck
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from corpuslab import REPORTS_DIR

from habesha_names import phonetic_key, transliterate
from habesha_names._data import _ORIGINS, LexiconError, _parse_given_names, _read
from habesha_names.match.token import jaro_winkler

CANDIDATES_PATH = REPORTS_DIR / "candidates.json"
WORKSHEET_PATH = REPORTS_DIR / "authoring_worksheet.json"
REPORT_PATH = REPORTS_DIR / "authoring_report.txt"
ENTRIES_PATH = REPORTS_DIR / "authored_entries.json"
SELFCHECK_DIR = REPORTS_DIR / "selfcheck"

#: Jaro-Winkler floor for the "close to an existing entry" advisory warning.
#: Chosen to catch the mining report's morphological-sibling trap (Hailu
#: inside Haile's cluster, jw 0.92) while staying quiet on unrelated names.
#: A report-ordering heuristic for Robel's eyes only -- it ships nothing and
#: gates nothing.
NEAR_DUP_FLOOR = 0.90

_DECISIONS = ("", "accept", "reject")
_ITEM_KEYS = frozenset(
    {"decision", "fidel", "canonical", "variants", "gender", "origin", "freq_tier", "notes"}
)
_ENTRY_KEYS = ("fidel", "canonical", "variants", "gender", "origin", "freq_tier")
_ORIGIN_LIST = ", ".join(sorted(_ORIGINS))

_INSTRUCTIONS = [
    "For each worksheet item set 'decision' to 'accept' or 'reject' (leave '' to decide "
    "later; pending items are skipped at validation, so partial batches work).",
    "For accepted items author: 'fidel' (the conventional Ethiopic spelling -- your "
    f"knowledge, not the corpus), 'origin' (one of: {_ORIGIN_LIST}), 'gender' (e.g. "
    '{"m": 1.0} or {"f": 0.97, "m": 0.03}; weights sum to 1.0), \'freq_tier\' (1 very '
    "common / 2 common / 3 notable), and prune 'variants' to real attested spellings "
    "(drop OCR junk; must not repeat the canonical).",
    "'canonical' may be corrected if the mined spelling is not the most common Latin form.",
    "The '_review' block (corpus counts, attested spellings, cross_checks) is read-only "
    "context; it never enters the lexicon (DATA_PROVENANCE.md, 'External corpora').",
    "Optional 'notes' flow into the validation report for the integration session. "
    "Keep every field present, even on rejected items.",
    "Then run: python scripts\\author_entries.py --validate  and open "
    "data-lab\\reports\\authoring_report.txt in an editor (not cmd).",
    "When nothing fatal remains, entries are written to "
    'data-lab\\reports\\authored_entries.json with "verified": false; integration into '
    "src/ is an agent session (Task 18) and the final verified flip happens in-repo, "
    "by you (data/schema.md workflow).",
]


# --- shared plumbing ----------------------------------------------------------


def _load_json(path: Path, what: str, hint: str) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"{what} missing: {path}\n{hint}")
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path}: invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected a top-level JSON object")
    return data


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _existing_entries() -> list[dict[str, Any]]:
    """Raw given_names.json entries, read exactly as the loader reads them."""
    entries = _read("given_names.json")["entries"]
    if not isinstance(entries, list):
        raise SystemExit("given_names.json: expected an 'entries' list")
    return entries


@dataclass(frozen=True)
class ExistingIndex:
    """Lookup snapshot of the lexicon a batch is cross-checked against."""

    spelling_owner: dict[str, str]  # lowercased Latin spelling -> owning canonical
    canonicals: dict[str, str]  # lowercased canonical -> canonical
    fidel_owner: dict[str, str]  # fidel string -> owning canonical
    key_owner: dict[str, tuple[str, ...]]  # phonetic key -> owning canonicals


def build_index(entries: list[dict[str, Any]]) -> ExistingIndex:
    spelling_owner: dict[str, str] = {}
    canonicals: dict[str, str] = {}
    fidel_owner: dict[str, str] = {}
    key_owner: dict[str, list[str]] = {}
    for entry in entries:
        canonical = entry["canonical"]
        canonicals[canonical.lower()] = canonical
        fidel_owner[entry["fidel"]] = canonical
        for spelling in (canonical, *entry["variants"]):
            spelling_owner.setdefault(spelling.lower(), canonical)
            key = phonetic_key(spelling)
            if key:
                owners = key_owner.setdefault(key, [])
                if canonical not in owners:
                    owners.append(canonical)
    return ExistingIndex(
        spelling_owner=spelling_owner,
        canonicals=canonicals,
        fidel_owner=fidel_owner,
        key_owner={key: tuple(owners) for key, owners in key_owner.items()},
    )


def _cross_checks(
    canonical: str,
    variants: list[str],
    index: ExistingIndex,
    batch_keys: dict[str, list[str]],
) -> list[str]:
    """Advisory findings for one candidate vs the lexicon and its own batch."""
    notes: list[str] = []
    for spelling in (canonical, *variants):
        owner = index.spelling_owner.get(spelling.lower())
        if owner is not None:
            notes.append(
                f"spelling {spelling!r} is already recorded under lexicon entry {owner!r}"
                " (stale candidates.json? re-run mine_candidates.py, or reconcile at"
                " integration)"
            )
    key = phonetic_key(canonical)
    for owner in index.key_owner.get(key, ()):
        notes.append(
            f"phonetic key {key!r} collides with existing entry {owner!r}"
            " (distinct names may share a key -- check this is not a duplicate)"
        )
    for fellow in batch_keys.get(key, []):
        if fellow != canonical:
            notes.append(f"shares phonetic key {key!r} with fellow candidate {fellow!r}")
    near = [
        (score, spelling, owner)
        for spelling, owner in index.spelling_owner.items()
        if spelling != canonical.lower()
        and (score := jaro_winkler(canonical.lower(), spelling)) >= NEAR_DUP_FLOOR
    ]
    for score, spelling, owner in sorted(near, key=lambda row: (-row[0], row[1])):
        notes.append(
            f"close to existing spelling {spelling!r} of entry {owner!r} (jw {score:.2f})"
            " -- possible duplicate or morphological sibling"
        )
    return notes


# --- step 1: emit the worksheet -----------------------------------------------


def build_worksheet(
    candidates_doc: dict[str, Any],
    index: ExistingIndex,
    top: int | None,
) -> dict[str, Any]:
    """Worksheet document from a mined candidates queue (pure)."""
    candidates = candidates_doc.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise SystemExit("candidates queue: expected a non-empty 'candidates' list")
    if top is not None:
        if top < 1:
            raise SystemExit("--top must be a positive integer")
        candidates = candidates[:top]
    batch_keys: dict[str, list[str]] = {}
    for candidate in candidates:
        batch_keys.setdefault(phonetic_key(candidate["canonical"]), []).append(
            candidate["canonical"]
        )
    items = []
    for candidate in candidates:
        review = dict(candidate.get("_review") or {})
        review["cross_checks"] = _cross_checks(
            candidate["canonical"], list(candidate.get("variants", [])), index, batch_keys
        )
        items.append(
            {
                "decision": "",
                "fidel": "",
                "canonical": candidate["canonical"],
                "variants": list(candidate.get("variants", [])),
                "gender": candidate.get("gender"),
                "origin": candidate.get("origin"),
                "freq_tier": candidate.get("freq_tier", 3),
                "notes": "",
                "_review": review,
            }
        )
    provenance = candidates_doc.get("_provenance", {})
    source = provenance.get("generated", "unknown") if isinstance(provenance, dict) else "unknown"
    return {
        "_instructions": _INSTRUCTIONS,
        "_provenance": {
            "source": source,
            "note": (
                "Worksheet for native-speaker authoring. _review blocks are corpus-derived"
                " context and never enter the repo (DATA_PROVENANCE.md, 'External corpora')."
            ),
        },
        "worksheet": items,
    }


def run_emit(
    top: int | None,
    force: bool,
    candidates_path: Path = CANDIDATES_PATH,
    worksheet_path: Path = WORKSHEET_PATH,
    existing_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if worksheet_path.exists() and not force:
        raise SystemExit(
            f"refusing to overwrite {worksheet_path} (it may contain in-progress"
            " authoring); pass --force to replace it"
        )
    if existing_entries is None:
        existing_entries = _existing_entries()
    candidates_doc = _load_json(
        candidates_path,
        "candidates queue",
        "run: python scripts\\mine_candidates.py (needs the data-lab corpus; see"
        " scripts\\corpuslab.py for download instructions)",
    )
    doc = build_worksheet(candidates_doc, build_index(existing_entries), top)
    _write_json(worksheet_path, doc)
    flagged = sum(1 for item in doc["worksheet"] if item["_review"]["cross_checks"])
    print(f"worksheet: {len(doc['worksheet'])} candidates -> {worksheet_path}")
    print(f"cross-checks flagged {flagged} candidates (see each item's _review.cross_checks)")
    print("fill decisions/fidel/origin, then run: python scripts\\author_entries.py --validate")
    return doc


# --- step 3: validate the filled worksheet, emit entries ----------------------


@dataclass
class Validation:
    """Everything --validate learned about one worksheet."""

    fatals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    accepted: list[dict[str, Any]] = field(default_factory=list)  # loader-shape entries
    accepted_names: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    translit_rows: list[tuple[str, str, str, str]] = field(default_factory=list)
    notes: list[tuple[str, str, str]] = field(default_factory=list)


def validate_worksheet(
    doc: dict[str, Any], existing_entries: list[dict[str, Any]]
) -> Validation:
    """Validate a filled worksheet against the given lexicon entries (pure)."""
    result = Validation()
    items = doc.get("worksheet")
    if not isinstance(items, list) or not items:
        raise SystemExit("worksheet: expected a non-empty top-level 'worksheet' list")
    index = build_index(existing_entries)

    filled: list[tuple[dict[str, Any], str]] = []
    for position, item in enumerate(items, start=1):
        where = f"item {position}"
        if not isinstance(item, dict):
            result.fatals.append(f"{where}: expected an object")
            continue
        canonical = item.get("canonical")
        if isinstance(canonical, str) and canonical:
            where = f"item {position} ({canonical})"
        missing = sorted(_ITEM_KEYS - item.keys())
        extra = sorted(key for key in item.keys() - _ITEM_KEYS if not key.startswith("_"))
        if missing or extra:
            result.fatals.append(f"{where}: missing keys {missing}, unexpected keys {extra}")
            continue
        raw_decision = item["decision"]
        if not isinstance(raw_decision, str):
            result.fatals.append(f"{where}: 'decision' must be a string")
            continue
        decision = raw_decision.strip().lower()
        if decision not in _DECISIONS:
            result.fatals.append(
                f"{where}: 'decision' must be '', 'accept', or 'reject', got {raw_decision!r}"
            )
            continue
        note = item["notes"]
        if not isinstance(note, str):
            result.fatals.append(f"{where}: 'notes' must be a string")
            continue
        if note:
            result.notes.append((str(canonical), decision or "pending", note))
        if decision == "":
            result.pending.append(str(canonical))
            continue
        if decision == "reject":
            result.rejected.append(str(canonical))
            continue
        result.accepted_names.append(str(canonical))
        fidel = item["fidel"]
        if not isinstance(fidel, str) or not fidel.strip():
            result.fatals.append(
                f"{where}: accepted but 'fidel' is empty -- author the conventional"
                " Ethiopic spelling"
            )
            continue
        if item["origin"] is None:
            result.fatals.append(
                f"{where}: accepted but 'origin' is null -- one of: {_ORIGIN_LIST}"
            )
            continue
        if item["gender"] is None:
            result.fatals.append(
                f'{where}: accepted but \'gender\' is null -- e.g. {{"m": 1.0}} or'
                ' {"f": 0.97, "m": 0.03}'
            )
            continue
        tier = item["freq_tier"]
        if isinstance(tier, bool) or not isinstance(tier, int):
            result.fatals.append(f"{where}: 'freq_tier' must be the integer 1, 2, or 3")
            continue
        entry: dict[str, Any] = {key: item[key] for key in _ENTRY_KEYS}
        entry["verified"] = False
        try:
            _parse_given_names(
                {"schema": 1, "entries": [entry]}, filename="authoring_worksheet.json"
            )
        except LexiconError as error:
            result.fatals.append(str(error))
            continue
        filled.append((entry, where))

    # Duplicate checks vs the shipped lexicon and within the batch (fatal).
    seen_canonical: dict[str, str] = {}
    seen_fidel: dict[str, str] = {}
    accepted: list[tuple[dict[str, Any], str]] = []
    for entry, where in filled:
        canonical, fidel = entry["canonical"], entry["fidel"]
        lower = canonical.lower()
        clean = True
        if lower in index.canonicals:
            result.fatals.append(
                f"{where}: canonical duplicates existing lexicon entry"
                f" {index.canonicals[lower]!r}"
            )
            clean = False
        if fidel in index.fidel_owner:
            result.fatals.append(
                f"{where}: fidel {fidel!r} duplicates existing entry"
                f" {index.fidel_owner[fidel]!r}"
            )
            clean = False
        if lower in seen_canonical:
            result.fatals.append(
                f"{where}: canonical duplicates accepted candidate {seen_canonical[lower]!r}"
            )
            clean = False
        if fidel in seen_fidel:
            result.fatals.append(
                f"{where}: fidel duplicates accepted candidate {seen_fidel[fidel]!r}"
            )
            clean = False
        seen_canonical.setdefault(lower, canonical)
        seen_fidel.setdefault(fidel, canonical)
        if clean:
            accepted.append((entry, where))

    # Advisory cross-checks on the filled values (warnings, never blocking:
    # Robel's knowledge outranks the tool -- surface, don't veto).
    batch_keys: dict[str, list[str]] = {}
    for entry, _ in accepted:
        batch_keys.setdefault(phonetic_key(entry["canonical"]), []).append(entry["canonical"])
    batch_spellings: dict[str, str] = {}
    for entry, where in accepted:
        for finding in _cross_checks(
            entry["canonical"], list(entry["variants"]), index, batch_keys
        ):
            result.warnings.append(f"{where}: {finding}")
        for spelling in (entry["canonical"], *entry["variants"]):
            owner = batch_spellings.get(spelling.lower())
            if owner is not None and owner != entry["canonical"]:
                result.warnings.append(
                    f"{where}: spelling {spelling!r} is also listed under accepted"
                    f" candidate {owner!r}"
                )
            batch_spellings.setdefault(spelling.lower(), entry["canonical"])

    # D2-style cross-check: does the engine's transliteration of the authored
    # fidel reach a recorded spelling? Mismatches are surfaced, not fatal --
    # conventional canonicals may differ from raw table output (task-3b
    # precedent: keep the conventional canonical, record the raw output as a
    # variant when it is a real spelling).
    for entry, where in accepted:
        latin = transliterate(entry["fidel"])
        if latin.lower() == entry["canonical"].lower():
            verdict = "OK: matches canonical"
        elif latin.lower() in {variant.lower() for variant in entry["variants"]}:
            verdict = "VARIANT: matches a recorded variant"
        else:
            verdict = "MISMATCH: neither the canonical nor a recorded variant"
            result.warnings.append(
                f"{where}: transliterate(fidel) = {latin!r} is neither the canonical nor"
                " a recorded variant -- confirm the fidel spelling, or record the raw"
                " output as a variant if the conventional spelling simply differs"
            )
        result.translit_rows.append((entry["fidel"], latin, entry["canonical"], verdict))

    # Belt-and-braces: the merged lexicon must parse with the real loader.
    if not result.fatals and accepted:
        merged = list(existing_entries) + [entry for entry, _ in accepted]
        try:
            _parse_given_names(
                {"schema": 1, "entries": merged}, filename="merged(lexicon+authored)"
            )
        except LexiconError as error:
            result.fatals.append(f"merged-lexicon gate: {error}")

    if not result.fatals:
        result.accepted = [entry for entry, _ in accepted]
    return result


def render_report(result: Validation, worksheet_path: Path, entries_path: Path) -> str:
    lines = [
        "AUTHORING VALIDATION REPORT (scripts/author_entries.py --validate)",
        f"worksheet: {worksheet_path}",
        f"decisions: {len(result.accepted_names)} accepted / {len(result.rejected)} rejected"
        f" / {len(result.pending)} pending",
        "",
        f"== FATAL ({len(result.fatals)}) -- entries are written only when this section"
        " is empty ==",
    ]
    lines += [f"  {message}" for message in result.fatals] or ["  none"]
    lines += ["", f"== WARNINGS ({len(result.warnings)}) -- advisory, for your review =="]
    lines += [f"  {message}" for message in result.warnings] or ["  none"]
    lines += ["", "== TRANSLITERATION CROSS-CHECK (accepted entries) =="]
    lines += [
        f"  {fidel}  ->  {latin}   [{verdict}]   canonical: {canonical}"
        for fidel, latin, canonical, verdict in result.translit_rows
    ] or ["  none"]
    if result.pending:
        lines += ["", "== PENDING (undecided, skipped) ==", "  " + ", ".join(result.pending)]
    if result.notes:
        lines += ["", "== WORKSHEET NOTES (for the integration session) =="]
        lines += [
            f"  {canonical} [{decision}]: {note}" for canonical, decision, note in result.notes
        ]
    lines += ["", "== RESULT =="]
    if result.fatals:
        lines.append("  FAILED: fix the fatal items above and re-run --validate."
                     "  No entries were written.")
    elif not result.accepted:
        lines.append("  no accepted entries yet -- nothing to write.")
    else:
        lines.append(f"  wrote {len(result.accepted)} entries -> {entries_path}")
        lines.append(
            '  all entries carry "verified": false; integration into given_names.json is'
            " Task 18, and the final verified flip happens in-repo after your review"
            " (data/schema.md workflow)."
        )
    return "\n".join(lines) + "\n"


def write_entries(entries: list[dict[str, Any]], source: str, path: Path) -> None:
    """Loader-shape entries, one line each (given_names.json paste style)."""
    lines = ["    { " + json.dumps(entry, ensure_ascii=False)[1:-1] + " }" for entry in entries]
    note = (
        "Authored given-name entries, loader-shape, for integration into"
        " src/habesha_names/data/given_names.json (Task 18). verified stays false until"
        " Robel flips it in-repo. No corpus counts, _review blocks, or corpus-derived"
        " keys here, by design (DATA_PROVENANCE.md, 'External corpora')."
    )
    text = (
        "{\n"
        f'  "_note": {json.dumps(note)},\n'
        f'  "source": {json.dumps(source, ensure_ascii=False)},\n'
        '  "entries": [\n' + ",\n".join(lines) + "\n  ]\n}\n"
    )
    if json.loads(text)["entries"] != entries:
        raise SystemExit("internal error: authored_entries.json formatting did not round-trip")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_validate(
    worksheet_path: Path = WORKSHEET_PATH,
    report_path: Path = REPORT_PATH,
    entries_path: Path = ENTRIES_PATH,
    existing_entries: list[dict[str, Any]] | None = None,
) -> Validation:
    if existing_entries is None:
        existing_entries = _existing_entries()
    doc = _load_json(
        worksheet_path,
        "worksheet",
        "run: python scripts\\author_entries.py --emit-worksheet  first",
    )
    result = validate_worksheet(doc, existing_entries)
    if not result.fatals and result.accepted:
        provenance = doc.get("_provenance", {})
        source = (
            provenance.get("source", "unknown") if isinstance(provenance, dict) else "unknown"
        )
        write_entries(result.accepted, source, entries_path)
    elif entries_path.exists():
        # The entries file must always reflect the LATEST validate run; a
        # stale one from an earlier pass must not sit around looking current.
        entries_path.unlink()
        print(f"removed stale {entries_path} (this run wrote no entries)")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result, worksheet_path, entries_path), encoding="utf-8")
    print(
        f"decisions: {len(result.accepted_names)} accepted / {len(result.rejected)} rejected"
        f" / {len(result.pending)} pending"
    )
    print(f"fatal errors: {len(result.fatals)}   warnings: {len(result.warnings)}")
    print(f"report: {report_path}  (open in an editor, not cmd)")
    if result.fatals:
        print("FAILED: fix the fatal items in the report and re-run --validate")
        raise SystemExit(1)
    if result.accepted:
        print(
            f"entries: {len(result.accepted)} -> {entries_path}"
            "  (verified: false; integration = Task 18)"
        )
    else:
        print("no accepted entries yet -- nothing written")
    return result


# --- selfcheck ----------------------------------------------------------------


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"selfcheck FAILED: {message}")


def run_selfcheck() -> None:
    """Full pipeline on fixture candidates; asserts every stage. No human input."""
    by_name = {entry["canonical"]: entry for entry in _existing_entries()}
    for needed in ("Abebe", "Haile", "Tsehay", "Kebede", "Bikila"):
        _expect(needed in by_name, f"packaged lexicon lost entry {needed}")
    # Fixture "existing lexicon" is deliberately tiny and disjoint from the
    # fixture candidates, so accept paths validate cleanly.
    existing = [by_name["Abebe"], by_name["Haile"]]

    if SELFCHECK_DIR.exists():
        shutil.rmtree(SELFCHECK_DIR)
    SELFCHECK_DIR.mkdir(parents=True)
    candidates_path = SELFCHECK_DIR / "candidates.json"
    worksheet_path = SELFCHECK_DIR / "worksheet.json"
    report_path = SELFCHECK_DIR / "report.txt"
    entries_path = SELFCHECK_DIR / "entries.json"

    def fixture_candidate(canonical: str) -> dict[str, Any]:
        entry = by_name[canonical]
        return {
            "fidel": "",
            "canonical": canonical,
            "variants": list(entry["variants"]),
            "gender": None,
            "origin": None,
            "freq_tier": entry["freq_tier"],
            "verified": False,
            "_review": {
                "corpus_total": 42,  # synthetic fixture count, not corpus data
                "spellings": {canonical.upper(): 42},
                "gender_evidence": "none (fixture)",
                "phonetic_key": phonetic_key(canonical),
            },
        }

    _write_json(
        candidates_path,
        {
            "_provenance": {
                "generated": "selfcheck fixtures (synthetic counts, real lexicon names)"
            },
            "candidates": [fixture_candidate(name) for name in ("Tsehay", "Kebede", "Bikila")],
        },
    )

    # 1. emit: structure of the blank worksheet.
    doc = run_emit(
        top=None,
        force=False,
        candidates_path=candidates_path,
        worksheet_path=worksheet_path,
        existing_entries=existing,
    )
    _expect(len(doc["worksheet"]) == 3, "worksheet should hold the 3 fixture candidates")
    _expect(
        all(item["fidel"] == "" and item["decision"] == "" for item in doc["worksheet"]),
        "emitted worksheet must have blank fidel and decision",
    )
    _expect(
        all("verified" not in item for item in doc["worksheet"]),
        "worksheet items must not carry a verified flag",
    )
    _expect(
        all("cross_checks" in item["_review"] for item in doc["worksheet"]),
        "every worksheet item must carry cross_checks",
    )

    # 2. overwrite protection.
    try:
        run_emit(
            top=None,
            force=False,
            candidates_path=candidates_path,
            worksheet_path=worksheet_path,
            existing_entries=existing,
        )
    except SystemExit as error:
        _expect("refusing to overwrite" in str(error), "expected the overwrite refusal")
    else:
        _expect(False, "second emit without --force must refuse")

    # 3. deterministic emission (byte-identical re-emit) and --top slicing.
    first_bytes = worksheet_path.read_bytes()
    run_emit(
        top=None,
        force=True,
        candidates_path=candidates_path,
        worksheet_path=worksheet_path,
        existing_entries=existing,
    )
    _expect(worksheet_path.read_bytes() == first_bytes, "worksheet emission must be deterministic")
    top_doc = run_emit(
        top=2,
        force=True,
        candidates_path=candidates_path,
        worksheet_path=SELFCHECK_DIR / "worksheet_top2.json",
        existing_entries=existing,
    )
    _expect(len(top_doc["worksheet"]) == 2, "--top must slice the queue")

    # 4. fill like Robel would. Fidel/gender/origin come from the verified
    #    packaged lexicon at runtime -- the agent never hand-types fidel.
    filled = json.loads(worksheet_path.read_text(encoding="utf-8"))
    for item in filled["worksheet"]:
        source = by_name[item["canonical"]]
        if item["canonical"] == "Bikila":
            item["decision"] = "reject"
            item["notes"] = "fixture: rejected candidate"
        else:
            item["decision"] = "accept"
            for key in _ENTRY_KEYS:
                item[key] = source[key]
    worksheet_path.write_text(
        json.dumps(filled, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # 5. validate the clean fill end to end.
    result = run_validate(
        worksheet_path=worksheet_path,
        report_path=report_path,
        entries_path=entries_path,
        existing_entries=existing,
    )
    _expect(not result.fatals, f"clean fill must have no fatals, got {result.fatals}")
    _expect(not result.warnings, f"clean fill must have no warnings, got {result.warnings}")
    _expect(
        result.rejected == ["Bikila"] and not result.pending,
        "decision bookkeeping is wrong",
    )
    expected = [
        {**{key: by_name[name][key] for key in _ENTRY_KEYS}, "verified": False}
        for name in ("Tsehay", "Kebede")
    ]
    emitted_doc = json.loads(entries_path.read_text(encoding="utf-8"))
    _expect(
        emitted_doc["entries"] == expected,
        "emitted entries must equal the source lexicon fields plus verified false",
    )
    _expect(
        [list(entry) for entry in emitted_doc["entries"]]
        == [[*_ENTRY_KEYS, "verified"]] * len(expected),
        "emitted entries must use the loader key order",
    )
    entries_dump = json.dumps(emitted_doc["entries"], ensure_ascii=False)
    _expect(
        "_review" not in entries_dump and "corpus_total" not in entries_dump,
        "corpus-derived data must not leak into the emitted entries",
    )
    _expect(
        all(row[3].startswith("OK") for row in result.translit_rows),
        "fixture transliteration cross-check should be all OK",
    )
    report_text = report_path.read_text(encoding="utf-8")
    _expect(
        "FATAL" in report_text and "TRANSLITERATION" in report_text and "Bikila" in report_text,
        "report is missing expected sections",
    )
    first_entries = entries_path.read_bytes()
    run_validate(
        worksheet_path=worksheet_path,
        report_path=report_path,
        entries_path=entries_path,
        existing_entries=existing,
    )
    _expect(entries_path.read_bytes() == first_entries, "entries emission must be deterministic")

    # 6. negative cases: every guard must actually fire.
    def base_item() -> dict[str, Any]:
        source = by_name["Tsehay"]
        item: dict[str, Any] = {key: source[key] for key in _ENTRY_KEYS}
        item.update({"decision": "accept", "notes": ""})
        return item

    def check_fatal(overrides: dict[str, Any], needle: str) -> None:
        item = base_item()
        item.update(overrides)
        outcome = validate_worksheet({"worksheet": [item]}, existing)
        _expect(
            any(needle in fatal for fatal in outcome.fatals),
            f"expected a fatal containing {needle!r} for {overrides!r},"
            f" got {outcome.fatals}",
        )

    check_fatal({"fidel": ""}, "'fidel' is empty")
    check_fatal({"fidel": "NotFidel"}, "not Ethiopic")
    check_fatal({"origin": None}, "'origin' is null")
    check_fatal({"origin": "klingon"}, "unknown origin")
    check_fatal({"gender": None}, "'gender' is null")
    check_fatal({"gender": {"f": 0.4}}, "sum")
    check_fatal({"decision": "maybe"}, "'decision' must be")
    check_fatal({"variants": ["Tsehay"]}, "repeats the canonical")
    check_fatal({"freq_tier": 7}, "'freq_tier'")
    check_fatal({"freq_tier": 1.5}, "integer")
    check_fatal({"unexpected_key": 1}, "unexpected keys")
    check_fatal(
        {key: by_name["Abebe"][key] for key in _ENTRY_KEYS}, "duplicates existing"
    )
    broken = base_item()
    del broken["origin"]
    outcome = validate_worksheet({"worksheet": [broken]}, existing)
    _expect(
        any("missing keys" in fatal for fatal in outcome.fatals),
        f"expected a missing-keys fatal, got {outcome.fatals}",
    )
    negatives = 13

    # 7. pending items are skipped, not failed.
    pending_item = base_item()
    pending_item["decision"] = ""
    outcome = validate_worksheet({"worksheet": [pending_item]}, existing)
    _expect(
        not outcome.fatals and outcome.pending == ["Tsehay"] and not outcome.accepted,
        "pending items must be skipped without fatals",
    )

    # 8. in-batch duplicates are fatal.
    outcome = validate_worksheet({"worksheet": [base_item(), base_item()]}, existing)
    _expect(
        any("duplicates accepted candidate" in fatal for fatal in outcome.fatals),
        f"expected an in-batch duplicate fatal, got {outcome.fatals}",
    )

    # 9. advisory warnings fire without blocking. Hayle vs existing Haile:
    #    recorded-spelling overlap + translit mismatch. Hailu vs Haile: the
    #    mining report's morphological-sibling trap (jw 0.92) -- exactly what
    #    NEAR_DUP_FLOOR exists to catch (Hayle/Haile at 0.89 sits below it).
    hayle = base_item()
    hayle["canonical"] = "Hayle"
    hayle["variants"] = []
    hailu = base_item()
    hailu["canonical"] = "Hailu"
    hailu["variants"] = []
    hailu["fidel"] = by_name["Kebede"]["fidel"]  # distinct fidel, no in-batch dup
    outcome = validate_worksheet({"worksheet": [hayle, hailu]}, [by_name["Haile"]])
    _expect(not outcome.fatals, f"warning case must not be fatal, got {outcome.fatals}")
    _expect(
        any("already recorded under lexicon entry 'Haile'" in w for w in outcome.warnings),
        f"expected a recorded-spelling overlap warning, got {outcome.warnings}",
    )
    _expect(
        any(
            "(Hailu)" in w and "possible duplicate or morphological sibling" in w
            for w in outcome.warnings
        ),
        f"expected a near-duplicate warning for Hailu, got {outcome.warnings}",
    )
    _expect(
        any("neither the canonical nor" in w for w in outcome.warnings),
        f"expected a transliteration-mismatch warning, got {outcome.warnings}",
    )

    # 10. CLI behavior on a fatal worksheet: exit 1, report written, no entries.
    bad_worksheet = SELFCHECK_DIR / "bad_worksheet.json"
    bad_report = SELFCHECK_DIR / "bad_report.txt"
    bad_entries = SELFCHECK_DIR / "bad_entries.json"
    bad_item = base_item()
    bad_item["fidel"] = ""
    _write_json(bad_worksheet, {"worksheet": [bad_item]})
    try:
        run_validate(
            worksheet_path=bad_worksheet,
            report_path=bad_report,
            entries_path=bad_entries,
            existing_entries=existing,
        )
    except SystemExit as error:
        _expect(error.code == 1, "validate must exit 1 on fatal errors")
    else:
        _expect(False, "validate on a fatal worksheet must raise SystemExit")
    _expect(not bad_entries.exists(), "no entries file may be written on fatal errors")
    _expect(bad_report.exists(), "the report must still be written on fatal errors")

    print(
        "selfcheck PASSED: emit -> fill -> validate -> entries pipeline, deterministic"
        f" outputs, {negatives} guard cases, pending/in-batch/warning/CLI-failure paths"
        f" (fixtures under {SELFCHECK_DIR})"
    )


# --- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--emit-worksheet",
        action="store_true",
        help="write the authoring worksheet from data-lab/reports/candidates.json",
    )
    mode.add_argument(
        "--validate",
        action="store_true",
        help="validate the filled worksheet; write report + entries when clean",
    )
    mode.add_argument(
        "--selfcheck",
        action="store_true",
        help="run the full pipeline on in-script fixtures (no corpus, no human input)",
    )
    parser.add_argument(
        "--top", type=int, default=None, help="emit only the top N candidates"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow --emit-worksheet to overwrite an existing worksheet",
    )
    args = parser.parse_args()
    if args.emit_worksheet:
        run_emit(top=args.top, force=args.force)
    elif args.validate:
        run_validate()
    else:
        run_selfcheck()


if __name__ == "__main__":
    main()
