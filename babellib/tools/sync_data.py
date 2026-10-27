"""Fetch the Unicode / CJK data the BabelSoft libraries read at runtime.

The raw archives are not in git: a full set is ~850 MB, so a checkout only
contains the small derived TSVs.  Run this once after cloning (and again when
bumping ``Dirs.CURRENT``)::

    uv run python babellib/tools/sync_data.py            # current release (~90 MB)
    uv run python babellib/tools/sync_data.py --all      # every release (~850 MB)
    uv run python babellib/tools/sync_data.py --check    # only report what is missing

``--all`` is what the version-history / diff tools need; the app itself only
needs the current release.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BABELLIB = REPO_ROOT / "babellib"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BABELLIB))

from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.preflight import DATA_MISSING_HINT, missing_data
from babelsoft.utils_.sync import UnicodeDataDownloader
from babelsoft.utils_.versions import VERSION_DIRS

#: Remote folders needed for the current release to work at all.  The UCD
#: downloader mirrors a flat directory, so the sub-directories are listed too.
CURRENT_FOLDERS: tuple[str, ...] = (
    "{current}/ucd",
    "{current}/ucd/auxiliary",
    "{current}/ucd/extracted",
    "{current}/ucd/emoji",
    "{current}/emoji",
)


def sync_current(force: bool = False) -> None:
    """Download everything the current release needs (≈90 MB)."""
    for folder in CURRENT_FOLDERS:
        UnicodeDataDownloader.sync_unicode(folder.format(current=Dirs.CURRENT), force=force)
    # unicode.org publishes Unihan as one zip, not as a browsable folder.
    UnicodeDataDownloader.sync_unihan(force=force)
    UnicodeDataDownloader.sync_charts(force=force)  # charts/ is an HTML page, not a folder
    UnicodeDataDownloader.sync_ids(force=force)
    UnicodeDataDownloader.sync_ivd(force=force)
    UnicodeDataDownloader.sync_iso15924()


def sync_all(force: bool = False) -> None:
    """Download every release snapshot plus the current release's extras."""
    for _version, folder in VERSION_DIRS:
        UnicodeDataDownloader.sync_unicode(folder, force=force)
    sync_current(force=force)


def check() -> int:
    """Print the missing runtime data files; return 1 when anything is absent."""
    missing = missing_data()
    if not missing:
        print(f"Data OK — {Dirs.DATA}")
        historical = [folder for _v, folder in VERSION_DIRS if not (Dirs.UNICODE / folder).is_dir()]
        if historical:
            print(
                f"Note: {len(historical)} historical release snapshot(s) are not installed;"
                " the version-history/diff features need them (--all)."
            )
        return 0
    print("Missing data files:")
    for line in missing:
        print(f"  {line}")
    print(f"\nFetch them with:\n  {DATA_MISSING_HINT}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="download every release snapshot (~850 MB)")
    group.add_argument("--check", action="store_true", help="only report missing data and exit")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = parser.parse_args(argv)

    if args.check:
        return check()
    if args.all:
        sync_all(force=args.force)
    else:
        sync_current(force=args.force)
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
