"""Ethiopian/Eritrean name intelligence: parsing, transliteration, variants, matching.

Habesha full names are given name + father's given name (+ grandfather's) —
there is no family name — and the same name is romanized many ways
(ጸሐይ → Tsehay / Tsehai / Sehay / Tzehay). This package parses that structure,
normalizes fidel spelling, transliterates, generates plausible Latin spelling
variants, and fuzzy-matches full names with an explanation for every score.

Alpha release: the practical transliteration defaults and bundled name lexicon
are pending native-speaker verification — match scores and variant outputs may
change in 0.1.0 final, and the API is not yet frozen.

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
from habesha_names.match.full import match
from habesha_names.match.phonetic import phonetic_key
from habesha_names.parse.parser import parse
from habesha_names.translit.to_latin import transliterate
from habesha_names.translit.variants import variants

__version__ = "0.1.0a1"

__all__ = [
    "__version__",
    "is_ethiopic",
    "match",
    "normalize",
    "parse",
    "phonetic_key",
    "transliterate",
    "variants",
]
