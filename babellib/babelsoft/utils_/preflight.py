"""Check that the data sets the libraries read at runtime are installed.

The raw UCD/CJK archives are not in git (they add up to ~850 MB), so a fresh
checkout has code but no data.  Instead of failing with a bare
``FileNotFoundError`` from somewhere deep inside a parser, the backend asks this
module first and answers with an actionable message.
"""

from __future__ import annotations

from pathlib import Path

from babelsoft.utils_.dirs import Dirs

#: Where to get the data from — quoted verbatim in the error messages.
DATA_MISSING_HINT = "uv run python babellib/tools/sync_data.py"


class DataMissingError(RuntimeError):
    """One or more runtime data files (or whole data sets) are absent."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            "Unicode data is missing:\n  "
            + "\n  ".join(missing)
            + f"\n\nFetch it with:\n  {DATA_MISSING_HINT}\n"
        )


#: ``(label, file)`` pairs that must exist for the app to be usable at all.
#: Each label names the feature that breaks without the file.
REQUIRED_DATA: tuple[tuple[str, Path], ...] = (
    ("UCD properties/names", Dirs.UCD / "UnicodeData.txt"),
    ("Unicode blocks", Dirs.UCD / "Blocks.txt"),
    ("CJK radicals", Dirs.UCD / "CJKRadicals.txt"),
    ("Unihan readings", Dirs.UNIHAN / "Unihan_Readings.txt"),
    ("Unihan IRG sources", Dirs.UNIHAN / "Unihan_IRGSources.txt"),
    ("Emoji sequences", Dirs.EMOJI / "emoji-test.txt"),
    ("character charts index", Dirs.CHARTS / "RSIndex.txt"),
    ("BabelStone IDS", Dirs.BABELSTONE / "IDS.TXT"),
    ("IVD sequences", Dirs.IVD / "IVD_Sequences.txt"),
)


def missing_data() -> list[str]:
    """Human-readable ``"<feature>: <path>"`` lines for every absent file."""
    return [f"{label}: {path}" for label, path in REQUIRED_DATA if not path.is_file()]


def require_data() -> None:
    """Raise :class:`DataMissingError` when a required data file is absent."""
    missing = missing_data()
    if missing:
        raise DataMissingError(missing)
