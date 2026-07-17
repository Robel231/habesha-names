"""Evaluate lexicon + variant-engine recall against the data-lab corpus.

For every ``given_names.json`` entry, all corpus tokens sharing a HabeshaKey
with the entry's spellings are treated as candidate attested spellings and
bucketed:

- **recorded**  -- already in the entry (canonical or ``variants``)
- **generated** -- produced by ``habesha_names.variants(canonical)``
- **collision** -- recorded under a DIFFERENT entry (Bekele inside Bikila's
  cluster): a known distinct name sharing the key; excluded from recall
- **gap**       -- none of the above, but Jaro-Winkler >= ``--jw-floor``
  against some recorded spelling: a plausible attested spelling the engine
  misses (review queue)
- **ambiguous** -- none of the above, spelling-far from every recorded
  spelling: likely an *unrecorded* distinct name sharing the key (or OCR
  wreckage); human-eyeball list

The gap/ambiguous split deliberately uses raw Jaro-Winkler, not ``match()``:
two same-key tokens always score at least the 0.9 phonetic floor in
``match()``, so the full matcher cannot separate same-key distinct names --
that is precisely the split needed here, and only a key-independent string
signal can make it. Morphological siblings (Haile/Hailu, Alemu/Alem) defeat
any string metric and land in **gap**; deciding those is native-speaker work.

Headline recall counts recorded+generated over everything except ambiguous;
the strict figure includes ambiguous too. Both appear in the report, because
the clustering step assumes the phonetic key -- the very hypothesis the
matcher encodes -- so spellings whose key drifted are invisible to it. The
edit-distance probe at the end partially compensates: it lists corpus tokens
within small edit distance of an entry that do NOT share its key.

Usage:
    python scripts/eval_corpus.py [--min-count 2] [--n 25] [--jw-floor 0.86]

Writes ``data-lab/reports/eval_report.md`` (gitignored) and prints a summary.
Requires the corpus in ``data-lab/`` (see scripts/corpuslab.py for fetching).
"""

from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from corpuslab import LEHAGERE_DIR, REPORTS_DIR, Corpus, load_lehagere, name_case, summarize

import habesha_names
from habesha_names import phonetic_key, variants
from habesha_names._data import lexicon
from habesha_names.match.token import jaro_winkler
from habesha_names.parse.compounds import split_joined


def _levenshtein_capped(a: str, b: str, cap: int) -> int:
    """Levenshtein distance, early-exiting with cap+1 when it exceeds cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    previous = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, start=1):
        current = [i]
        best = i
        for j, ch_b in enumerate(b, start=1):
            cost = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ch_a != ch_b),
            )
            current.append(cost)
            best = min(best, cost)
        if best > cap:
            return cap + 1
        previous = current
    return previous[-1]


@dataclass
class EntryReport:
    canonical: str
    recorded: dict[str, int] = field(default_factory=dict)
    generated: dict[str, int] = field(default_factory=dict)
    collisions: dict[str, int] = field(default_factory=dict)
    gaps: dict[str, int] = field(default_factory=dict)
    ambiguous: dict[str, int] = field(default_factory=dict)

    def attested_occurrences(self) -> int:
        return sum(
            sum(bucket.values())
            for bucket in (self.recorded, self.generated, self.gaps, self.ambiguous)
        )

    def recall(self, *, strict: bool) -> float | None:
        covered = sum(self.recorded.values()) + sum(self.generated.values())
        total = covered + sum(self.gaps.values())
        if strict:
            total += sum(self.ambiguous.values())
        return covered / total if total else None


def _cluster(corpus: Corpus, min_count: int) -> dict[str, dict[str, int]]:
    clusters: dict[str, dict[str, int]] = defaultdict(dict)
    for token, count in corpus.tokens.items():
        if count < min_count:
            continue
        key = phonetic_key(token)
        if key:
            clusters[key][token] = count
    return clusters


def _entry_reports(
    clusters: dict[str, dict[str, int]], n: int, jw_floor: float
) -> list[EntryReport]:
    all_recorded: dict[str, str] = {}  # spelling lower -> owning canonical
    for entry in lexicon().given_names:
        for spelling in (entry.canonical, *entry.variants):
            all_recorded.setdefault(spelling.lower(), entry.canonical)
    reports = []
    for entry in lexicon().given_names:
        spellings = (entry.canonical, *entry.variants)
        recorded_lower = {s.lower() for s in spellings}
        generated_lower = {s.lower() for s in variants(entry.canonical, n=n)}
        report = EntryReport(canonical=entry.canonical)
        seen: set[str] = set()
        for key in {phonetic_key(s) for s in spellings} - {""}:
            for token, count in clusters.get(key, {}).items():
                if token in seen:
                    continue
                seen.add(token)
                lower = token.lower()
                if lower in recorded_lower:
                    report.recorded[token] = count
                elif lower in all_recorded:
                    report.collisions[token] = count
                elif lower in generated_lower:
                    report.generated[token] = count
                elif max(jaro_winkler(lower, s) for s in recorded_lower) >= jw_floor:
                    report.gaps[token] = count
                else:
                    report.ambiguous[token] = count
        reports.append(report)
    return reports


def _corpus_coverage(corpus: Corpus, clusters: dict[str, dict[str, int]]) -> tuple[int, int, int]:
    """Occurrences (lexicon-key-covered, compound-parsed, uncovered)."""
    entry_keys = {
        phonetic_key(s)
        for entry in lexicon().given_names
        for s in (entry.canonical, *entry.variants)
    } - {""}
    covered = compound = uncovered = 0
    for token, count in corpus.tokens.items():
        if phonetic_key(token) in entry_keys:
            covered += count
        elif split_joined(token.lower()) is not None:
            compound += count
        else:
            uncovered += count
    return covered, compound, uncovered


def _edit_probe(
    corpus: Corpus, min_count: int, limit: int = 30
) -> list[tuple[str, int, str, int]]:
    """Corpus tokens near an entry spelling but keyed differently.

    Returns (token, count, nearest canonical, distance), highest counts first.
    These are the key's blind spots: real variants here are invisible to
    key-based clustering, so they never even reach the gap/ambiguous buckets.
    """
    refs: list[tuple[str, str, str]] = []  # (spelling lower, its key, canonical)
    for entry in lexicon().given_names:
        for spelling in (entry.canonical, *entry.variants):
            refs.append((spelling.lower(), phonetic_key(spelling), entry.canonical))
    hits: list[tuple[str, int, str, int]] = []
    for token, count in corpus.tokens.items():
        if count < min_count:
            continue
        lower = token.lower()
        token_key = phonetic_key(token)
        best: tuple[int, str] | None = None
        for ref_lower, ref_key, canonical in refs:
            if token_key == ref_key:
                best = None
                break  # key-clustered already; not a blind spot
            cap = 1 if len(ref_lower) <= 5 else 2
            distance = _levenshtein_capped(lower, ref_lower, cap)
            if distance <= cap and (best is None or distance < best[0]):
                best = (distance, canonical)
        if best is not None:
            hits.append((token, count, best[1], best[0]))
    hits.sort(key=lambda hit: (-hit[1], hit[0]))
    return hits[:limit]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _top(bucket: dict[str, int], limit: int = 3) -> str:
    items = sorted(bucket.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return ", ".join(f"{name_case(token)}:{count}" for token, count in items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min-count", type=int, default=2, help="ignore rarer corpus tokens")
    parser.add_argument("--n", type=int, default=25, help="variants() budget (library default 25)")
    parser.add_argument(
        "--jw-floor", type=float, default=0.86, help="gap-vs-ambiguous Jaro-Winkler floor"
    )
    args = parser.parse_args()

    corpus = load_lehagere()
    clusters = _cluster(corpus, args.min_count)
    reports = _entry_reports(clusters, args.n, args.jw_floor)
    covered, compound, uncovered = _corpus_coverage(corpus, clusters)
    probe = _edit_probe(corpus, max(args.min_count, 3))

    def totals(pick: str) -> int:
        return sum(sum(getattr(r, pick).values()) for r in reports)

    recorded_t, generated_t = totals("recorded"), totals("generated")
    gaps_t, ambiguous_t = totals("gaps"), totals("ambiguous")
    collisions_t = totals("collisions")
    covered_t = recorded_t + generated_t
    headline = covered_t / (covered_t + gaps_t) if covered_t + gaps_t else 0.0
    strict = (
        covered_t / (covered_t + gaps_t + ambiguous_t)
        if covered_t + gaps_t + ambiguous_t
        else 0.0
    )
    total_occurrences = sum(corpus.tokens.values())

    lines = [
        "# Corpus evaluation report",
        "",
        f"Generated {date.today().isoformat()} by scripts/eval_corpus.py; "
        f"habesha-names {habesha_names.__version__}; "
        f"min-count={args.min_count}, n={args.n}, jw-floor={args.jw_floor}.",
        "",
        "Corpus: lehagere/ethiopian-names (40/60 housing-lottery extraction; "
        "unlicensed, local-analysis only -- DATA_PROVENANCE.md 'External corpora').",
        f"data_text.json sha256 {_sha256(LEHAGERE_DIR / 'data_text.json')}",
        "",
        f"Cleaning: {summarize(corpus)}",
        "",
        "## Aggregates (occurrence-weighted)",
        "",
        f"- Attested-variant recall (recorded+generated over non-ambiguous): "
        f"**{headline:.1%}** ({covered_t} of {covered_t + gaps_t} occurrences)",
        f"- Strict recall (ambiguous counted as misses): {strict:.1%}",
        f"- Buckets: recorded {recorded_t}, generated {generated_t}, "
        f"gaps {gaps_t}, ambiguous {ambiguous_t}; "
        f"cross-entry key collisions (excluded): {collisions_t}",
        f"- Corpus coverage: {covered / total_occurrences:.1%} of occurrences share a key "
        f"with a lexicon entry; {compound / total_occurrences:.1%} more parse as compounds; "
        f"{uncovered / total_occurrences:.1%} uncovered "
        f"(mining queue -- see scripts/mine_candidates.py)",
        "",
        "## Per-entry breakdown",
        "",
        "| entry | attested occ. | recall | top gaps | top ambiguous | key collisions |",
        "|---|---|---|---|---|---|",
    ]
    for report in sorted(reports, key=lambda r: -r.attested_occurrences()):
        recall = report.recall(strict=False)
        lines.append(
            f"| {report.canonical} | {report.attested_occurrences()} "
            f"| {'-' if recall is None else f'{recall:.0%}'} "
            f"| {_top(report.gaps)} | {_top(report.ambiguous)} | {_top(report.collisions)} |"
        )
    lines += [
        "",
        "## Edit-distance probe (key blind spots)",
        "",
        "Corpus tokens within small edit distance of a lexicon spelling whose",
        "HabeshaKey nonetheless differs. Real variants in this list are invisible",
        "to key-based clustering AND to the matcher's phonetic component.",
        "",
        "| token | count | near entry | distance |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {name_case(token)} | {count} | {canonical} | {distance} |"
        for token, count, canonical, distance in probe
    ]
    lines.append("")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "eval_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"corpus: {summarize(corpus)}")
    print(f"attested-variant recall (headline): {headline:.1%}   strict: {strict:.1%}")
    print(
        f"buckets: recorded {recorded_t} / generated {generated_t} / "
        f"gaps {gaps_t} / ambiguous {ambiguous_t} / collisions {collisions_t} (excluded)"
    )
    print(
        f"corpus coverage: lexicon {covered / total_occurrences:.1%}, "
        f"compounds {compound / total_occurrences:.1%}, "
        f"uncovered {uncovered / total_occurrences:.1%}"
    )
    worst = sorted(
        (r for r in reports if r.gaps), key=lambda r: -sum(r.gaps.values())
    )[:8]
    for report in worst:
        print(f"  gap-heavy: {report.canonical} -> {_top(report.gaps, 4)}")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
