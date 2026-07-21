"""Task 9 — public API surface (ARCHITECTURE §5), package docstring, README doctests."""

from __future__ import annotations

import doctest
from pathlib import Path

import habesha_names

# The full ARCHITECTURE §5 surface (completed by to_fidel, Task 21).
PUBLIC_CALLABLES = [
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


def test_all_is_exactly_the_architecture_surface() -> None:
    assert sorted(habesha_names.__all__) == sorted(["__version__", *PUBLIC_CALLABLES])


def test_every_public_callable_has_a_doctested_docstring() -> None:
    for name in PUBLIC_CALLABLES:
        obj = getattr(habesha_names, name)
        assert callable(obj), name
        assert obj.__doc__ is not None and ">>>" in obj.__doc__, name


def test_version() -> None:
    assert habesha_names.__version__ == "0.2.0"


def test_package_docstring_examples() -> None:
    results = doctest.testmod(habesha_names)
    assert results.attempted > 0
    assert results.failed == 0


def test_readme_doctests() -> None:
    readme = Path(__file__).resolve().parents[1] / "README.md"
    results = doctest.testfile(str(readme), module_relative=False, encoding="utf-8")
    assert results.attempted >= 20
    assert results.failed == 0
