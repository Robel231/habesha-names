"""Full-name parsing: raw string -> :class:`ParsedName` (ARCHITECTURE 4.3).

Habesha full names have no family name: the tokens are the given name, the
father's given name (patronym), and optionally the grandfather's (avonym).
:func:`parse` normalizes the input, strips a leading title, detects script,
expands slash abbreviations, joins compound given names, and assigns
positional roles. It decides nothing it cannot see: diaspora surname
semantics and low-confidence compound readings are flagged in ``notes`` and
``compound_confidence`` rather than silently resolved.

Pipeline (ARCHITECTURE 4.3 logic order; comma inversion runs during
tokenization because it changes token order for every later step):

1. ``normalize`` (NFC, homophone collapse, punctuation, whitespace).
2. Comma inversion: exactly one comma means "patronym, given" and the two
   sides are swapped; any other comma pattern is treated as whitespace.
3. Leading titles stripped; the first is recorded (as its canonical Latin
   form, even for fidel input), extras are noted.
4. Script detection over the remaining name tokens.
5. Slash-abbreviation expansion ("G/Medhin" -> "Gebremedhin", noted with
   every weighted candidate).
6. Compound joining: an already-joined token is flagged in place; an
   adjacent "prefix + second element" pair is joined into one token.
7. Roles: token 1 = given, 2 = patronym, 3 = avonym; extras are noted.
8. Single-letter initials ("B.") are kept verbatim and noted.

``compound_confidence`` is the confidence in the compound decisions taken
anywhere in the parse (minimum, if several): 1.0 when unambiguous (already
joined in the input, or no compound involved), 0.9 when a spaced pair was
joined and NOT joining would overflow the three roles, 0.65 when both
readings fit ("Haile Mariam Desalegn"), and the chosen candidate's lexicon
weight for a slash abbreviation. A spaced pair joined through the Task 15
phonetic-key fallback (a rewritten element spelling, e.g. "Gebrie Medhin")
uses the lower 0.75 / 0.5 constants and keeps the input spelling in the
joined token; the note names the phonetic-key evidence.
``given_is_compound`` refers to the given name only. The constants are
agent-chosen heuristics, not measured priors (PROGRESS.md review queue).
Note one asymmetry of input-preserving fallback joins: re-parsing the
joined output token ("Gebriemedhin") keeps the structural roles stable but
cannot re-detect the compound (the rewritten spelling is not in the
lexicon), so ``given_is_compound`` reads False on such a round-trip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from habesha_names.fidel.normalize import normalize
from habesha_names.fidel.syllable import is_ethiopic
from habesha_names.parse.compounds import expand_abbreviation, match_pair, split_joined
from habesha_names.parse.titles import match_title

Script = Literal["ethiopic", "latin", "mixed"]

_MAX_ROLES = 3
#: Compound-decision confidence defaults -- agent-chosen heuristics
#: (verified: false; PROGRESS.md review queue). The FUZZY constants apply
#: when a spaced pair joins through the phonetic-key fallback (Task 15):
#: key-level evidence is weaker than a recognized spelling, so each sits
#: below its exact counterpart while keeping overflow > ambiguous.
_CONFIDENCE_UNAMBIGUOUS = 1.0
_CONFIDENCE_SPACED_OVERFLOW = 0.9
_CONFIDENCE_SPACED_AMBIGUOUS = 0.65
_CONFIDENCE_FUZZY_OVERFLOW = 0.75
_CONFIDENCE_FUZZY_AMBIGUOUS = 0.5

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


@dataclass(frozen=True)
class ParsedName:
    """Structured reading of one Habesha full name (ARCHITECTURE 4.3)."""

    raw: str
    title: str | None
    given: str
    patronym: str | None
    avonym: str | None
    given_is_compound: bool
    compound_confidence: float
    script: Script
    has_surname: Literal["no", "unknown"]
    notes: list[str]

    def __str__(self) -> str:
        """Canonical display form: title, given, patronym, avonym.

        >>> str(parse("Bikila, Abebe"))
        'Abebe Bikila'
        """
        parts = (self.title, self.given, self.patronym, self.avonym)
        return " ".join(part for part in parts if part)


def _role_name(index: int) -> str:
    return ("given", "patronym", "avonym")[index] if index < _MAX_ROLES else f"token {index + 1}"


def _tokenize(text: str, notes: list[str]) -> list[str]:
    """Split normalized text into tokens, handling 'patronym, given' inversion."""
    if "," in text:
        left, _, right = text.partition(",")
        if "," not in right and left.strip() and right.strip():
            notes.append('comma-inverted "patronym, given" order restored')
            return right.split() + left.split()
        notes.append("unexpected comma pattern; commas treated as spaces")
        return text.replace(",", " ").split()
    return text.split()


def _strip_titles(tokens: list[str], notes: list[str]) -> tuple[str | None, list[str]]:
    """Strip leading title tokens; record the first, note any extras."""
    title: str | None = None
    while len(tokens) > 1:
        matched = match_title(tokens[0])
        if matched is None:
            break
        if title is None:
            title = matched.canonical
        else:
            notes.append(f"additional title {tokens[0]!r} ({matched.canonical}) dropped")
        tokens = tokens[1:]
    if title is None and len(tokens) == 1 and match_title(tokens[0]) is not None:
        notes.append(f"single token {tokens[0]!r} matches a title; treated as a name")
    return title, tokens


def _detect_script(tokens: list[str]) -> Script:
    if all(is_ethiopic(token) for token in tokens):
        return "ethiopic"
    if not any(is_ethiopic(char) for token in tokens for char in token):
        return "latin"
    return "mixed"


def _resolve_compounds(tokens: list[str], notes: list[str]) -> tuple[list[str], bool, float]:
    """Expand abbreviations and join compounds; report given-compound flag + confidence."""
    resolved: list[str] = []
    given_is_compound = False
    confidence = _CONFIDENCE_UNAMBIGUOUS
    i = 0
    while i < len(tokens):
        token = tokens[i]
        at_given = not resolved
        expansion = expand_abbreviation(token)
        if expansion is not None:
            notes.append(expansion.note)
            confidence = min(confidence, expansion.confidence)
            if at_given:
                given_is_compound = expansion.is_compound
            resolved.extend(expansion.tokens)
            i += 1
            continue
        joined = split_joined(token)
        if joined is not None:
            notes.append(
                f"{_role_name(len(resolved))} {token!r} is a joined compound"
                f" ({joined.prefix.latin} + {joined.second.latin})"
            )
            if at_given:
                given_is_compound = True
            resolved.append(token)
            i += 1
            continue
        if i + 1 < len(tokens):
            pair = match_pair(token, tokens[i + 1])
            if pair is not None:
                unjoined_total = len(resolved) + len(tokens) - i
                overflow = unjoined_total > _MAX_ROLES
                if pair.exact:
                    spaced = (
                        _CONFIDENCE_SPACED_OVERFLOW if overflow else _CONFIDENCE_SPACED_AMBIGUOUS
                    )
                    evidence = ""
                else:
                    spaced = _CONFIDENCE_FUZZY_OVERFLOW if overflow else _CONFIDENCE_FUZZY_AMBIGUOUS
                    evidence = (
                        f"phonetic-key element match, {pair.prefix.latin} + {pair.second.latin}; "
                    )
                notes.append(
                    f"{_role_name(len(resolved))} '{token} {tokens[i + 1]}' read as compound"
                    f" {pair.joined!r} ({evidence}confidence {spaced:g};"
                    " the two-token reading is also possible)"
                )
                confidence = min(confidence, spaced)
                if at_given:
                    given_is_compound = True
                resolved.append(pair.joined)
                i += 2
                continue
        resolved.append(token)
        i += 1
    return resolved, given_is_compound, confidence


def parse(raw: str, *, assume_diaspora: bool = False) -> ParsedName:
    """Parse one Habesha full name into its structural roles.

    Raises ``ValueError`` when no name tokens remain after normalization.
    Never guesses silently: every non-obvious decision (comma inversion,
    abbreviation expansion, compound joins, initials, extra tokens,
    diaspora mode) is recorded in ``notes``. With ``assume_diaspora`` the
    patronym may be an inherited legal surname; the parser flags this via
    ``has_surname="unknown"`` rather than deciding.

    >>> parsed = parse("Ato Abebe Bikila")
    >>> parsed.title, parsed.given, parsed.patronym
    ('Ato', 'Abebe', 'Bikila')
    >>> parse("Hailemariam Desalegn").given_is_compound
    True
    >>> parse("G/Medhin Tesfaye").given
    'Gebremedhin'
    >>> parse("Bikila, Abebe").given
    'Abebe'
    >>> parse("ወይዘሮ ጸሐይ ገብረመድህን").title
    'Weizero'
    >>> parse("Abebe Bikila", assume_diaspora=True).has_surname
    'unknown'
    """
    notes: list[str] = []
    tokens = _tokenize(normalize(raw), notes)
    if not tokens:
        raise ValueError(f"no name tokens in {raw!r}")
    title, tokens = _strip_titles(tokens, notes)
    script = _detect_script(tokens)
    tokens, given_is_compound, confidence = _resolve_compounds(tokens, notes)
    given = tokens[0]
    patronym = tokens[1] if len(tokens) > 1 else None
    avonym = tokens[2] if len(tokens) > 2 else None
    if len(tokens) > _MAX_ROLES:
        extra = " ".join(tokens[_MAX_ROLES:])
        notes.append(f"tokens beyond avonym not assigned a role: {extra!r}")
    for index, value in enumerate((given, patronym, avonym)):
        if value is not None and _INITIAL_RE.match(value):
            notes.append(f"{_role_name(index)} {value!r} is an initial")
    if assume_diaspora:
        notes.append("diaspora mode: patronym may be an inherited family surname")
    return ParsedName(
        raw=raw,
        title=title,
        given=given,
        patronym=patronym,
        avonym=avonym,
        given_is_compound=given_is_compound,
        compound_confidence=confidence,
        script=script,
        has_surname="unknown" if assume_diaspora else "no",
        notes=notes,
    )
