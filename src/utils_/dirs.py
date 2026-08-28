import os
from pathlib import Path


class Dirs:
    REPO = Path(__file__).parent.parent.parent
    SRC = REPO / "src"
    DATA = REPO / "data"
    BABELSTONE = DATA / "babelstone"
    BABELSOFT = DATA / "cjkv"
    IVD = DATA / "ivd"

    # ── Unicode data (all under data/unicode/) ──────────────────────────────
    # data/unicode/ mirrors unicode.org/Public: one subdir per release
    # (1.1-Update, 2.0-Update, …, 4.1.0, …, 18.0.0) plus reconstructed/.
    UNICODE = DATA / "unicode"

    # Current release used for day-to-day property lookups.
    # Overridable via the UNICODE_VERSION env var (or set Dirs.CURRENT at runtime),
    # e.g. UNICODE_VERSION=18.0.0 once Unicode 18 is released.
    CURRENT = os.environ.get("UNICODE_VERSION", "17.0.0")

    # UCD data files of the current release (data/unicode/17.0.0/ucd/).
    UCD = UNICODE / CURRENT / "ucd"

    # Charts of the current release (data/unicode/17.0.0/charts/).
    CHARTS = UNICODE / CURRENT / "charts"

    # Unihan split files of the current release (data/unicode/17.0.0/ucd/unihan/).
    UNIHAN = UCD / "unihan"

    # Reconstructed Unicode 1.0.0 / 1.0.1 files.
    RECONSTRUCTED = UNICODE / "reconstructed"
