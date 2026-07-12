"""Title/honorific detection (Ato, W/ro, Dr, ...) for name parsing.

Titles are matched by lexicon lookup against ``data/titles.json`` --
canonical Latin forms and their abbreviations case-insensitively, fidel
forms after :func:`~habesha_names.fidel.normalize.normalize` (so homophone
spellings such as ሐጂ/ሀጂ hit the same entry). A trailing ASCII period is
tolerated ("Ato." matches "Ato"). The lookup index is built lazily from the
packaged lexicon on first use; this module holds no other state.
"""

from __future__ import annotations

from functools import cache

from habesha_names._data import Title, lexicon
from habesha_names.fidel.normalize import normalize


@cache
def _index() -> dict[str, Title]:
    """Lookup key -> Title: lowercased Latin forms plus normalized fidel forms."""
    index: dict[str, Title] = {}
    for title in lexicon().titles:
        keys = [title.canonical.lower()]
        keys.extend(abbreviation.lower() for abbreviation in title.abbreviations)
        keys.extend(normalize(form) for form in title.fidel)
        for key in keys:
            index.setdefault(key, title)  # file order wins on (unexpected) collisions
    return index


def match_title(token: str) -> Title | None:
    """Return the lexicon :class:`Title` a single token denotes, or ``None``.

    >>> match_title("Ato").canonical
    'Ato'
    >>> match_title("w/ro").canonical
    'Woizero'
    >>> match_title("ወይዘሮ").canonical
    'Woizero'
    >>> match_title("Tesfaye") is None
    True
    """
    key = normalize(token).lower()
    found = _index().get(key)
    if found is None and key.endswith("."):
        found = _index().get(key[:-1])
    return found
