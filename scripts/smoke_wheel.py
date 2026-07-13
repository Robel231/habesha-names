"""Smoke-test an INSTALLED habesha-names distribution (wheel or sdist).

Run from a directory outside the source tree, with the built artifact
installed into the running interpreter's environment::

    python -m venv smoke-venv
    smoke-venv\\Scripts\\pip install dist\\habesha_names-0.1.0-py3-none-any.whl
    cd <anywhere-outside-the-repo>
    smoke-venv\\Scripts\\python <repo>\\scripts\\smoke_wheel.py 0.1.0

Exercises exactly what an editable install masks: that the packaged
``data/*.json`` lexicons ship inside the artifact and the engine works
end-to-end from them. Exits non-zero (AssertionError) on any failure.

Usage: ``python smoke_wheel.py [expected_version]``
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    import habesha_names

    # Guard: we must be testing the installed distribution, not the repo.
    pkg_file = Path(habesha_names.__file__).resolve()
    repo_src = Path(__file__).resolve().parent.parent / "src"
    assert not pkg_file.is_relative_to(repo_src), (
        f"habesha_names imported from the source tree ({pkg_file}), "
        "not from an installed artifact"
    )

    if len(sys.argv) > 1:
        expected = sys.argv[1]
        assert habesha_names.__version__ == expected, (
            f"version mismatch: package {habesha_names.__version__!r} "
            f"!= expected {expected!r} (tag)"
        )

    # The lexicons must load from the installed package data.
    from habesha_names._data import lexicon

    lex = lexicon()
    assert len(lex.given_names) >= 50, len(lex.given_names)
    assert len(lex.titles) == 12, len(lex.titles)

    # End-to-end engine checks (plan-pinned behaviors).
    assert habesha_names.transliterate("ጸሐይ") == "Tsehay"  # ጸሐይ
    parsed = habesha_names.parse("Ato Abebe Bikila")
    assert parsed.title == "Ato" and parsed.given == "Abebe"
    assert "Tesfay" in habesha_names.variants("Tesfaye", n=10)
    score = habesha_names.match(
        "ወይዘሮ ጸሐይ ገብረመድህን",
        "Tsehay G/Medhin",
    )  # ወይዘሮ ጸሐይ ገብረመድህን
    assert float(score) >= 0.85, float(score)

    print(
        f"wheel smoke OK: version={habesha_names.__version__} "
        f"given_names={len(lex.given_names)} match={float(score):.2f}"
    )


if __name__ == "__main__":
    main()
