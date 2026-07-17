"""Empirical check of the LinkedIn-reply claims against the public matcher.

Run: python verify_claims.py
Score policy (README / CHANGELOG): >=0.85 likely same, 0.60-0.85 review zone,
<=0.60 likely different.
"""

from habesha_names import match

PAIRS = [
    ("Abebe Kebede Tadesse", "Abebe Kebede",          "truncation, tail (avonym) dropped"),
    ("Abebe Kebede Tadesse", "Abebe Tadesse",         "skip-generation - COMMENTER'S CASE"),
    ("Abebe Kebede Tadesse", "Abebe Tadesse Kebede",  "father/grandfather swapped - COMMENTER'S CASE"),
    ("Abebe Kebede Tadesse", "Kebede Tadesse",         "given name dropped"),
    ("Abebe Kebede Tadesse", "Abebe Kebede Tadese",    "spelling variant in tail"),
    ("Abebe Kebede Tadesse", "አበበ ከበደ ታደሰ", "script variant (fidel)"),
    ("Abebe Kebede Tadesse", "Girma Alemu Bekele",     "true-negative baseline"),
]


def band(score: float) -> str:
    if score >= 0.85:
        return "SAME (>=0.85)"
    if score >= 0.60:
        return "REVIEW (0.60-0.85)"
    return "DIFFERENT (<=0.60)"


print(f"{'score':>7}  {'band':<20}  swapped  case")
print("-" * 90)
for a, b, label in PAIRS:
    r = match(a, b)
    print(f"{r.score:7.4f}  {band(r.score):<20}  {str(r.swapped):<7}  {label}")
    print(f"{'':>7}  a={a!r}  b={b!r}")
    for p in r.pairs:
        print(f"{'':>9}pair {p.role_a}->{p.role_b}: {p.token_a!r}/{p.token_b!r} "
              f"sim={p.sim:.4f} via {p.method}")
    for n in r.notes:
        print(f"{'':>9}note: {n}")
    print()
