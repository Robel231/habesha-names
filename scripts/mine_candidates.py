"""Mine the data-lab corpus for lexicon review candidates (never auto-shipped).

Three outputs, all under ``data-lab/reports/`` (gitignored):

- ``candidates.json`` -- frequency-ranked queue of names NOT covered by any
  ``given_names.json`` entry key, shaped like schema entries so Robel can
  review, author the fidel/origin fields, and paste into the lexicon. Every
  candidate ships ``"verified": false`` plus a ``_review`` block (corpus
  counts, gender evidence, key); the ``_review`` block and the counts NEVER
  enter the shipped lexicon (schema.md forbids extra keys -- the loader
  would reject them, by design).
- ``mining_report.md`` -- variant-gap suggestions for existing entries
  (attested spellings missing from their ``variants`` lists, flagged by
  whether the rule engine already generates them), compound-form names the
  engine covers structurally, and attested slash-abbreviation evidence
  (K/MARIAM etc.) versus ``abbreviation_expansions``.

The corpus prioritizes review; it is not a source of truth. Counts are OCR-
noisy occurrence counts from one document family (40/60 housing lists), so
tier suggestions are coarse and gender evidence is weak (see corpuslab.py).

Usage:
    python scripts/mine_candidates.py [--top 150] [--candidate-floor 5] [--variant-floor 3]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date

from corpuslab import REPORTS_DIR, load_lehagere, name_case, summarize

import habesha_names
from habesha_names import phonetic_key, variants
from habesha_names._data import lexicon
from habesha_names.match.token import jaro_winkler
from habesha_names.parse.compounds import split_joined

#: Minimum Jaro-Winkler for a cluster member to count as a spelling of the
#: cluster's top name. Below it, the member seeds its own candidate: key
#: clusters can merge distinct names (ALI and AYELE share a key), and a
#: buried second name should surface as its own queue entry, not a bogus
#: "variant". Raw JW, not match(): same-key pairs always score >= the 0.9
#: phonetic floor in match(), so the full matcher cannot make this split.
#: 0.86 keeps attested respellings (Aliye 0.91, Hussien 0.97, Ahimed 0.96)
#: and separates distinct names (Ayele 0.51, Bikila 0.67, Aman 0.83);
#: same floor as eval_corpus.py --jw-floor.
_SPLIT_FLOOR = 0.86


def _split_cluster(ranked: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    """Greedily split a key cluster into spelling-coherent groups."""
    groups = []
    remaining = ranked
    while remaining:
        top, rest = remaining[0], []
        group = [top]
        for member in remaining[1:]:
            if jaro_winkler(top[0].lower(), member[0].lower()) >= _SPLIT_FLOOR:
                group.append(member)
            else:
                rest.append(member)
        groups.append(group)
        remaining = rest
    return groups


def _suggest_tier(total: int) -> int:
    """Coarse freq_tier suggestion from corpus occurrences (guess, for review)."""
    if total >= 1000:
        return 1
    if total >= 200:
        return 2
    return 3


def _known_keys() -> set[str]:
    return {
        phonetic_key(s)
        for entry in lexicon().given_names
        for s in (entry.canonical, *entry.variants)
    } - {""}


def _title_spellings() -> set[str]:
    return {
        form.upper()
        for title in lexicon().titles
        for form in (title.canonical, *title.abbreviations)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--top", type=int, default=150, help="max candidates emitted")
    parser.add_argument(
        "--candidate-floor", type=int, default=5, help="min cluster occurrences for a candidate"
    )
    parser.add_argument(
        "--variant-floor", type=int, default=3, help="min occurrences for a variant suggestion"
    )
    args = parser.parse_args()

    corpus = load_lehagere()
    clusters: dict[str, dict[str, int]] = defaultdict(dict)
    for token, count in corpus.tokens.items():
        key = phonetic_key(token)
        if key:
            clusters[key][token] = count

    known = _known_keys()
    titles = _title_spellings()

    # --- Candidate queue: clusters no lexicon entry reaches -------------------
    candidates = []
    compound_forms: list[tuple[str, int]] = []
    for key, members in clusters.items():
        if key in known:
            continue
        if sum(members.values()) < args.candidate_floor:
            continue
        ranked = sorted(members.items(), key=lambda kv: (-kv[1], kv[0]))
        for group in _split_cluster(ranked):
            total = sum(count for _, count in group)
            top_token = group[0][0]
            if total < args.candidate_floor or top_token in titles:
                continue
            if split_joined(top_token.lower()) is not None:
                compound_forms.append((top_token, total))
                continue
            gender = corpus.gender.get(top_token)
            variant_spellings = [
                name_case(token)
                for token, count in group[1:]
                if count >= max(2, args.variant_floor - 1)
            ][:8]
            candidates.append(
                {
                    "fidel": "",
                    "canonical": name_case(top_token),
                    "variants": variant_spellings,
                    "gender": {gender: 1.0} if gender else None,
                    "origin": None,
                    "freq_tier": _suggest_tier(total),
                    "verified": False,
                    "_review": {
                        "corpus_total": total,
                        "spellings": dict(group),
                        "gender_evidence": (
                            f"corpus gender file says {gender!r} (single-document, weak)"
                            if gender
                            else "none"
                        ),
                        "phonetic_key": key,
                    },
                }
            )
    candidates.sort(key=lambda c: -c["_review"]["corpus_total"])  # type: ignore[index]
    candidates = candidates[: args.top]
    compound_forms.sort(key=lambda kv: -kv[1])

    # --- Variant gaps for existing entries ------------------------------------
    all_recorded = {
        spelling.lower()
        for entry in lexicon().given_names
        for spelling in (entry.canonical, *entry.variants)
    }
    variant_gaps: list[tuple[str, str, int, bool, float]] = []
    for entry in lexicon().given_names:
        spellings = (entry.canonical, *entry.variants)
        generated_lower = {s.lower() for s in variants(entry.canonical, n=50)}
        seen: set[str] = set()
        for key in {phonetic_key(s) for s in spellings} - {""}:
            for token, count in clusters.get(key, {}).items():
                lower = token.lower()
                # all_recorded also skips spellings owned by OTHER entries:
                # a known distinct name sharing the key (Bekele in Bikila's
                # cluster) is a collision, not a variant suggestion.
                if token in seen or lower in all_recorded or count < args.variant_floor:
                    continue
                seen.add(token)
                score = max(jaro_winkler(lower, s.lower()) for s in spellings)
                variant_gaps.append(
                    (entry.canonical, name_case(token), count, lower in generated_lower, score)
                )
    variant_gaps.sort(key=lambda gap: -gap[2])

    # --- Slash-abbreviation evidence ------------------------------------------
    known_abbrevs = {expansion.abbrev.upper() for expansion in lexicon().abbreviations}
    by_letter: dict[str, dict[str, int]] = defaultdict(dict)
    for form, count in corpus.slash_forms.items():
        letter, remainder = form.split("/", 1)
        by_letter[letter][remainder] = by_letter[letter].get(remainder, 0) + count
    slash_rows = sorted(
        (
            (letter, sum(remainders.values()), remainders, letter in known_abbrevs)
            for letter, remainders in by_letter.items()
        ),
        key=lambda row: -row[1],
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = (
        f"Generated {date.today().isoformat()} by scripts/mine_candidates.py; "
        f"habesha-names {habesha_names.__version__}; top={args.top}, "
        f"candidate-floor={args.candidate_floor}, variant-floor={args.variant_floor}."
    )

    candidates_path = REPORTS_DIR / "candidates.json"
    with candidates_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "_provenance": {
                    "note": (
                        "REVIEW QUEUE, not lexicon data. Corpus-derived candidates for "
                        "given_names.json; fidel/origin/gender must be authored by the "
                        "native-speaker reviewer, counts and _review blocks must not be "
                        "copied into the lexicon, and verified stays false until review "
                        "(DATA_PROVENANCE.md 'External corpora')."
                    ),
                    "generated": stamp,
                    "cleaning": summarize(corpus),
                },
                "candidates": candidates,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
        fh.write("\n")

    lines = [
        "# Corpus mining report",
        "",
        stamp,
        "",
        f"Cleaning: {summarize(corpus)}",
        "",
        f"## Candidate queue ({len(candidates)} entries -> candidates.json)",
        "",
        "| canonical | occurrences | other attested spellings | gender evidence | tier guess |",
        "|---|---|---|---|---|",
    ]
    for candidate in candidates[:25]:
        review = candidate["_review"]
        gender_cell = next(iter(candidate["gender"])) if candidate["gender"] else "-"  # type: ignore[call-overload]
        lines.append(
            f"| {candidate['canonical']} | {review['corpus_total']} "  # type: ignore[index]
            f"| {', '.join(candidate['variants']) or '-'} "  # type: ignore[arg-type]
            f"| {gender_cell} | {candidate['freq_tier']} |"
        )
    lines += [
        "",
        "(table shows the top 25; the full ranked queue is in candidates.json)",
        "",
        "## Variant-gap suggestions for existing entries",
        "",
        "Attested spellings sharing an entry's key, missing from every entry's",
        "spelling lists. `engine` = the rule engine already generates it",
        "(lexicon addition optional, per schema.md variants are attested",
        "high-frequency spellings); `NO` = lexicon AND engine gap. `jw` is the",
        "best Jaro-Winkler against the entry's recorded spellings: a high",
        "count with a low `jw` is often not a variant at all but a DISTINCT",
        "name hiding in a covered cluster -- and even a high `jw` can be a",
        "morphological sibling (Hailu inside Haile's cluster, jw 0.92). Those",
        "are new-entry candidates the queue above cannot see, because it only",
        "looks at clusters no entry reaches. Review both ways.",
        "",
        "| entry | suggested variant | count | engine | jw |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {canonical} | {spelling} | {count} | {'yes' if generated else 'NO'} | {score:.2f} |"
        for canonical, spelling, count, generated, score in variant_gaps[:60]
    ]
    lines += [
        "",
        "## Compound-form names in uncovered clusters",
        "",
        "Structurally handled by the compounds machinery; listed for tier",
        "awareness and possible promotion to full entries.",
        "",
        "| token | occurrences |",
        "|---|---|",
    ]
    lines += [f"| {name_case(token)} | {count} |" for token, count in compound_forms[:30]]
    lines += [
        "",
        "## Slash-abbreviation evidence",
        "",
        "Attested letter/remainder forms vs `abbreviation_expansions` "
        f"(known letters: {', '.join(sorted(known_abbrevs))}).",
        "",
        "| letter | occurrences | top remainders | in lexicon |",
        "|---|---|---|---|",
    ]
    for letter, total, remainders, in_lexicon in slash_rows:
        top_remainders = ", ".join(
            f"{name_case(r)}:{c}"
            for r, c in sorted(remainders.items(), key=lambda kv: -kv[1])[:4]
        )
        lines.append(f"| {letter}/ | {total} | {top_remainders} | {'yes' if in_lexicon else 'NO'} |")
    lines.append("")

    report_path = REPORTS_DIR / "mining_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"corpus: {summarize(corpus)}")
    print(f"candidates: {len(candidates)} (floor {args.candidate_floor}) -> {candidates_path}")
    if candidates:
        preview = ", ".join(
            f"{c['canonical']}:{c['_review']['corpus_total']}" for c in candidates[:8]  # type: ignore[index]
        )
        print(f"  top: {preview}")
    engine_misses = [gap for gap in variant_gaps if not gap[3]]
    print(
        f"variant gaps: {len(variant_gaps)} suggestions "
        f"({len(engine_misses)} not generated by the engine)"
    )
    missing_letters = [row[0] for row in slash_rows if not row[3]]
    print(f"slash letters missing from lexicon: {', '.join(missing_letters) or 'none'}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
