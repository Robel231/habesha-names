"""``match()`` throughput benchmark (Task 8 gate: >= 50,000 matches/sec).

Deterministic, dedup-shaped workload: full names are built from the seeded
lexicon canonicals plus rule-engine variant spellings, then compared in
overlapping windows -- the same names recur across many comparisons,
exactly as in batch entity resolution, so the parse/similarity memoization
caches operate at their realistic steady-state hit rates. The first pass
over the workload warms those caches and is untimed. No randomness, no
network, no file writes.

Usage:
    python scripts/benchmark.py --min-mps 50000
"""

from __future__ import annotations

import argparse
import sys
import time

from habesha_names._data import lexicon
from habesha_names.match.full import match
from habesha_names.translit.variants import variants


def build_pairs() -> list[tuple[str, str]]:
    """A fixed workload of name pairs: near-duplicates and non-matches."""
    canonicals = [entry.canonical for entry in lexicon().given_names]
    count = len(canonicals)
    names = [f"{given} {canonicals[(i * 7 + 3) % count]}" for i, given in enumerate(canonicals)]
    respelled = []
    for name in names:
        given, patronym = name.split()
        alternates = variants(given)
        respelled.append(f"{alternates[1] if len(alternates) > 1 else given} {patronym}")
    pairs: list[tuple[str, str]] = []
    for i, name in enumerate(names):
        for offset in range(1, 9):
            pairs.append((name, names[(i + offset) % count]))
        pairs.append((name, respelled[i]))
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-mps",
        type=float,
        default=0.0,
        help="exit 1 when throughput falls below this many match() calls/sec",
    )
    parser.add_argument(
        "--calls",
        type=int,
        default=100_000,
        help="minimum number of timed match() calls (default: 100000)",
    )
    args = parser.parse_args(argv)

    pairs = build_pairs()
    for a, b in pairs:  # warm-up: lexicon load + memoization caches
        match(a, b)

    calls = 0
    start = time.perf_counter()
    while calls < args.calls:
        for a, b in pairs:
            match(a, b)
        calls += len(pairs)
    elapsed = time.perf_counter() - start
    mps = calls / elapsed

    print(f"{calls} match() calls over {len(pairs)} distinct pairs in {elapsed:.3f}s")
    print(f"{mps:,.0f} matches/sec")
    if args.min_mps and mps < args.min_mps:
        print(f"FAIL: below required {args.min_mps:,.0f} matches/sec", file=sys.stderr)
        return 1
    if args.min_mps:
        print(f"OK: meets required {args.min_mps:,.0f} matches/sec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
