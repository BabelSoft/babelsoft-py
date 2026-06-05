from pathlib import Path


class Dirs:
    REPO = Path(__file__).parent.parent.parent
    SRC = REPO / "src"
    DATA = REPO / "data"
    BABELSTONE = DATA / "babelstone"
    BABELSOFT = DATA / "babelsoft"
    UCD = DATA / "ucd"
    UNIHAN = DATA / "unihan"
    CHARTS = DATA / "charts"
    IVD = DATA / "ivd"
