"""Smoke tests: the package and its subpackages import, version is set."""

import habesha_names


def test_version() -> None:
    assert habesha_names.__version__ == "0.2.0"


def test_subpackages_importable() -> None:
    import habesha_names.data
    import habesha_names.fidel
    import habesha_names.match
    import habesha_names.parse
    import habesha_names.translit  # noqa: F401
