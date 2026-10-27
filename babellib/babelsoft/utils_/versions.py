"""Unicode release → raw data folder mapping.

``data/unicode/<folder>`` holds the downloaded UCD snapshot for every release
the version-history features can compare against.  The folders are not in git
(they add up to ~850 MB); :mod:`babellib.tools.sync_data` walks this table to
fetch them.

The table is ordered oldest-first and mirrors the release list in
``data/scripts/unicode_version_stats.tsv``.
"""

from __future__ import annotations

#: ``(release, folder under data/unicode/)`` pairs.
VERSION_DIRS: list[tuple[str, str]] = [
    ("1.0.0", "reconstructed/1.0.0"),
    ("1.0.1", "reconstructed/1.0.1"),
    ("1.1.5", "1.1-Update"),
    ("2.0.14", "2.0-Update"),
    ("2.1.2", "2.1-Update"),
    ("2.1.5", "2.1-Update2"),
    ("2.1.8", "2.1-Update3"),
    ("2.1.9", "2.1-Update4"),
    ("3.0.0", "3.0-Update"),
    ("3.0.1", "3.0-Update1"),
    ("3.1.0", "3.1-Update"),
    ("3.1.1", "3.1-Update1"),
    ("3.2.0", "3.2-Update"),
    ("4.0.0", "4.0-Update"),
    ("4.0.1", "4.0-Update1"),
    ("4.1.0", "4.1.0/ucd"),
    ("5.0.0", "5.0.0/ucd"),
    ("5.1.0", "5.1.0/ucd"),
    ("5.2.0", "5.2.0/ucd"),
    ("6.0.0", "6.0.0/ucd"),
    ("6.1.0", "6.1.0/ucd"),
    ("6.2.0", "6.2.0/ucd"),
    ("6.3.0", "6.3.0/ucd"),
    ("7.0.0", "7.0.0/ucd"),
    ("8.0.0", "8.0.0/ucd"),
    ("9.0.0", "9.0.0/ucd"),
    ("10.0.0", "10.0.0/ucd"),
    ("11.0.0", "11.0.0/ucd"),
    ("12.0.0", "12.0.0/ucd"),
    ("12.1.0", "12.1.0/ucd"),
    ("13.0.0", "13.0.0/ucd"),
    ("14.0.0", "14.0.0/ucd"),
    ("15.0.0", "15.0.0/ucd"),
    ("15.1.0", "15.1.0/ucd"),
    ("16.0.0", "16.0.0/ucd"),
    ("17.0.0", "17.0.0/ucd"),
]
