"""Native-speaker review helper. Run inside .venv: python review.py
Writes review_report.txt — open it in VS Code, NOT cmd."""
import io

from habesha_names import match, transliterate, variants
from habesha_names._data import lexicon

out = io.StringIO()
w = out.write

# ── 1. Decision cases: does the current table spell these the way people do? ──
w("=" * 60 + "\n1. TRANSLITERATION — is this how people spell it?\n" + "=" * 60 + "\n")
decision_names = [
    "ተስፋዬ", "ገብረመድህን", "ፀሐይ", "ኃይለ ሥላሴ",          # plan seeds
    "ፍቅር", "ትግስት", "ቅድስት", "ዮሐንስ",                  # 6th-order cluster cases
    "ወይዘሮ", "ወልደማርያም", "ወርቁ", "ወንድሙ",             # the ወ we/wo decision
    "ቀለሙ", "ቅዱስ", "መኮንን",                            # ቀ k/q
    "አገኘሁ",                                             # ኘ gn/ny
    "ጓደኙ", "ኋላ", "ሟሟ",                               # labialized wa/ua
    "ብርሃኑ", "ምስራቅ", "ግርማ", "ኃይለማርያም", "ዳንኤል", "መሐመድ",
]
for n in decision_names:
    w(f"  {n:<14} -> {transliterate(n)}\n")

# ── 2. Variants: would a KYC system see these spellings in the wild? ──
w("\n" + "=" * 60 + "\n2. VARIANTS — real-world spellings? junk?\n" + "=" * 60 + "\n")
for n in ["Tesfaye", "Tsehay", "Gebremedhin", "Mohammed", "Woizero" if True else ""]:
    if n:
        w(f"  {n}: {', '.join(variants(n, )[:12])}\n")

# ── 3. Match scores: same person high, different people low? ──
w("\n" + "=" * 60 + "\n3. MATCH SCORES — same>=0.85, different<=0.60, review-zone between\n" + "=" * 60 + "\n")
pairs = [
    ("ፀሐይ ገብረመድህን", "Tsehay G/Medhin"),
    ("Tesfaye Girma", "Tesfay Ghirma"),
    ("Mohammed Hussein", "Muhamed Husen"),
    ("Abebe Bikila", "Bikila Abebe"),
    ("Tesfaye Girma", "Tesfahun Girma"),     # siblings — review zone?
    ("Bekele Gerba", "Bikila Gerba"),        # known collision
    ("Alemu Kebede", "Almaz Kebede"),        # must be LOW
]
for a, b in pairs:
    w(f"  {float(match(a, b)):.2f}  {a}  <->  {b}\n")

# ── 4. The 56 lexicon entries: YOUR fidel/spelling check ──
w("\n" + "=" * 60 + "\n4. LEXICON — check fidel spelling, canonical, variants, gender\n" + "=" * 60 + "\n")
for e in lexicon().given_names:
    g = getattr(e, "gender", {})
    w(f"  {e.fidel:<12} {e.canonical:<16} variants={list(e.variants)} gender={g} origin={e.origin}\n")

with open("review_report.txt", "w", encoding="utf-8") as f:
    f.write(out.getvalue())
print("done -> open review_report.txt in VS Code")