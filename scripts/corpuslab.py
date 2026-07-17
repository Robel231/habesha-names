"""Loader/cleaner for the local evaluation corpora in ``data-lab/`` (never shipped).

``data-lab/`` is gitignored on purpose: the corpora it holds are third-party
datasets with no license and no documented collection methodology (see
DATA_PROVENANCE.md, "External corpora"). They are used strictly to
*prioritize* native-speaker review and to *evaluate* recall -- nothing from
them enters the shipped lexicon except through Robel authoring an entry via
the normal ``verified`` workflow. This module makes no network calls; it
refuses to run (with download instructions) when the corpus files are absent.

The lehagere corpus (``lehagere/ethiopian-names`` on GitHub) is name-token ->
occurrence-count data extracted upstream from Ethiopia's published 40/60
housing-lottery winner lists. It is OCR-noisy: table words leak in (ROOM/BED
appear once per document row), digits replace letters (M0HAMMED), and 61% of
keys are count-1 hapaxes, many of them misreads. Cleaning here is therefore
part of the method and is kept explicit and inspectable (every rejected key
is returned in ``Corpus.dropped``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA_LAB = Path(__file__).resolve().parent.parent / "data-lab"
LEHAGERE_DIR = DATA_LAB / "lehagere-ethiopian-names"
REPORTS_DIR = DATA_LAB / "reports"

_DOWNLOAD_HELP = """\
Corpus file missing: {path}

data-lab/ corpora are never committed; fetch them manually:

  mkdir -p data-lab/lehagere-ethiopian-names
  curl -sL -o data-lab/lehagere-ethiopian-names/data_text.json \\
    https://raw.githubusercontent.com/lehagere/ethiopian-names/master/data_text.json
  curl -sL -o data-lab/lehagere-ethiopian-names/data.json \\
    https://raw.githubusercontent.com/lehagere/ethiopian-names/master/data.json

Then record retrieval date and sha256 in data-lab/README.md
(see DATA_PROVENANCE.md, "External corpora").
"""

#: Document artifacts from the 40/60 housing tables -- column words, not
#: names. ROOM and BED appear once per row (~158k); AND joins OCR-merged
#: cells. ADDIS is deliberately NOT listed: ABABA never occurs in the
#: corpus, so ADDIS rows are the given name (Addis), not the city header.
ARTIFACT_STOPLIST = frozenset(
    {
        "ROOM",
        "BED",
        "AND",
        "NAME",
        "GENDER",
        "FLOOR",
        "BLOCK",
        "SITE",
        "DATE",
        "CITY",
        "WOREDA",
        "BIRR",
        "WINNER",
        "TOTAL",
    }
)

#: A clean single-token name: ASCII letters only (OCR digit/punct noise is
#: dropped, not repaired -- almost all of it is count-1).
_TOKEN_RE = re.compile(r"[A-Z]{3,20}\Z")
#: An attested slash abbreviation (K/MARIAM), same shape the library parses.
_SLASH_RE = re.compile(r"[A-Z]/[A-Z]{2,20}\Z")


@dataclass(frozen=True)
class Corpus:
    """The cleaned lehagere corpus, split by token shape.

    ``tokens``/``slash_forms``/``dropped`` map UPPERCASE keys to occurrence
    counts; ``gender`` maps a subset of tokens to ``"f"``/``"m"`` (from the
    much smaller ``data.json`` file -- weak evidence, single-digit counts).
    """

    tokens: dict[str, int]
    slash_forms: dict[str, int]
    gender: dict[str, str]
    dropped: dict[str, int]


def name_case(token: str) -> str:
    """UPPERCASE corpus token -> conventional name casing (K/MARIAM -> K/Mariam)."""
    out = []
    capitalize = True
    for ch in token.lower():
        out.append(ch.upper() if capitalize else ch)
        capitalize = ch in "/.-"
    return "".join(out)


def _normalize_gender(raw: object) -> str | None:
    """Map the OCR-noisy gender strings (FEMALE, FEM.ALE, FEMA1E) to f/m."""
    if not isinstance(raw, str):
        return None
    letters = re.sub(r"[^A-Z]", "", raw.upper())
    if letters.startswith("FEM"):
        return "f"
    if letters.startswith("MAL"):
        return "m"
    return None


def load_lehagere() -> Corpus:
    """Load and clean the lehagere corpus from ``data-lab/`` (no network)."""
    counts_path = LEHAGERE_DIR / "data_text.json"
    gender_path = LEHAGERE_DIR / "data.json"
    if not counts_path.is_file():
        raise SystemExit(_DOWNLOAD_HELP.format(path=counts_path))
    with counts_path.open(encoding="utf-8") as fh:
        raw_counts = json.load(fh)

    tokens: dict[str, int] = {}
    slash_forms: dict[str, int] = {}
    dropped: dict[str, int] = {}
    for key, count in raw_counts.items():
        token = key.strip().upper()
        if token in ARTIFACT_STOPLIST:
            dropped[token] = dropped.get(token, 0) + int(count)
        elif _TOKEN_RE.match(token):
            tokens[token] = tokens.get(token, 0) + int(count)
        elif _SLASH_RE.match(token):
            slash_forms[token] = slash_forms.get(token, 0) + int(count)
        else:
            dropped[token] = dropped.get(token, 0) + int(count)

    gender: dict[str, str] = {}
    if gender_path.is_file():
        with gender_path.open(encoding="utf-8") as fh:
            raw_gender = json.load(fh)
        for key, value in raw_gender.items():
            token = key.strip().upper()
            g = _normalize_gender(value.get("gender") if isinstance(value, dict) else None)
            if g is not None and _TOKEN_RE.match(token):
                gender[token] = g

    return Corpus(tokens=tokens, slash_forms=slash_forms, gender=gender, dropped=dropped)


def summarize(corpus: Corpus) -> str:
    """One-paragraph cleaning summary for report headers."""
    kept = sum(corpus.tokens.values())
    slash = sum(corpus.slash_forms.values())
    lost = sum(corpus.dropped.values())
    top_dropped = sorted(corpus.dropped.items(), key=lambda kv: -kv[1])[:5]
    dropped_note = ", ".join(f"{k}:{v}" for k, v in top_dropped)
    return (
        f"{len(corpus.tokens)} clean name tokens ({kept} occurrences), "
        f"{len(corpus.slash_forms)} slash-abbreviation forms ({slash} occurrences), "
        f"{len(corpus.dropped)} keys dropped as artifacts/noise ({lost} occurrences; "
        f"top: {dropped_note}). Gender evidence for {len(corpus.gender)} tokens."
    )
