"""Ethiopian/Eritrean name intelligence: parsing, transliteration, variants, matching.

Habesha full names are given name + father's given name (+ grandfather's) —
there is no family name — and the same name is romanized many ways
(ጸሐይ → Tsehay / Tsehai / Sehay / Tzehay). This package parses that structure,
normalizes fidel spelling, transliterates, generates plausible Latin spelling
variants, and fuzzy-matches full names with an explanation for every score.

>>> from habesha_names import match, parse, variants
>>> parse("Ato Abebe Bikila").given
'Abebe'
>>> "Tesfay" in variants("Tesfaye")
True
>>> match("G/Medhin Tesfaye", "Gebremedhin Tesfaye") > 0.9
True

The public API is exactly the names in ``__all__`` (ARCHITECTURE §5);
everything else, including the submodules, is internal and may change.
"""

from habesha_names.fidel.normalize import normalize
from habesha_names.fidel.syllable import is_ethiopic
from habesha_names.gender import guess_gender
from habesha_names.match.full import match
from habesha_names.match.phonetic import phonetic_key
from habesha_names.parse.parser import parse
from habesha_names.translit.to_fidel import to_fidel
from habesha_names.translit.to_latin import transliterate
from habesha_names.translit.variants import variants

__version__ = "0.2.0.dev0"

__all__ = [
    "__version__",
    "guess_gender",
    "is_ethiopic",
    "match",
    "normalize",
    "parse",
    "phonetic_key",
    "to_fidel",
    "transliterate",
    "variants",
]
