"""Unicode Scripts dialog data — ISO 15924 codes + per-block character stats.

All UCD parsing is reused from ``babelsoft.unicode.core.Unicode`` (the dedicated
data-parsing library): script ranges from ``Scripts.txt``
(``Unicode._script_data``), ages from ``DerivedAge.txt``
(``Unicode._age_table``), ISO codes from ``PropertyValueAliases.txt``
(``Unicode.get_script_iso_code``), and the latest block table from
``Blocks.txt`` (``Unicode._block_data``).  English/French names come from the
synced ISO 15924 list (``data/scripts/iso15924.tsv``).
"""

from __future__ import annotations

import bisect
import functools
from pathlib import Path

from babelsoft.unicode.core import Unicode
from babelsoft.utils_.dirs import Dirs

_ISO_FILE = Dirs.DATA / "scripts" / "iso15924.tsv"

# Standard descriptions shown in the Scripts dialog notes column.
_NOTES = {
    "Common": "Characters that are common to two or more scripts",
    "Inherited": "Combining characters that inherit the script of the character they are applied to",
    "Braille": "First defined as a script in 4.0",
    "Coptic": "Disunified from Greek in 4.1",
    "Mongolian": "Unifies the Mongolian, Todo, Manchu, and Sibe alphabets",
    "Runic": "Unifies various runic alphabets",
    "Tibetan": "Removed in 1.1 and reintroduced in 2.0",
    "Yi": "Liangshan Yi (Nuosu) syllabary",
    "Unknown": "Private use characters, as well as reserved, non-character and surrogate code points",
}


@functools.lru_cache(maxsize=1)
def _iso_15924() -> dict[str, dict]:
    """{ISO 15924 code: {code, number, name, french, alias, age, date}}."""
    result: dict[str, dict] = {}
    for raw in Path(_ISO_FILE).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        code, number, name, french, alias, age, date = line.split("\t")
        result[code] = {
            "code": code,
            "number": number,
            "name": name,
            "french": french,
            "alias": alias,
            "age": age,
            "date": date,
        }
    return result


@functools.lru_cache(maxsize=1)
def _script_ranges() -> dict[str, list[tuple[int, int]]]:
    """Script value → sorted disjoint ranges, from ``Unicode._script_data``."""
    table, names = Unicode._script_data()
    ranges: dict[str, list[tuple[int, int]]] = {}
    for s, e, idx in table:
        ranges.setdefault(names[idx], []).append((s, e))
    return ranges


def _min_age(cps: list[tuple[int, int]]) -> str | None:
    """Earliest Unicode version among a script's codepoints (from DerivedAge)."""
    ages = Unicode._age_table()
    starts = [a[0] for a in ages]
    best: tuple[int, ...] | None = None
    best_s: str | None = None
    for s, e in cps:
        i = bisect.bisect_right(starts, e) - 1
        if i < 0:
            continue
        j = i
        while j >= 0 and ages[j][1] >= s:
            ver = tuple(int(x) for x in ages[j][2].split("."))
            if best is None or ver < best:
                best = ver
                best_s = ages[j][2]
            j -= 1
    return best_s


@functools.lru_cache(maxsize=1)
def script_summary() -> list[dict]:
    """Return all scripts with characters in the latest UCD.

    One row per script: ``{code, name, script, chars, version, notes}``,
    sorted alphabetically by English name.
    """
    ranges_by_script = _script_ranges()
    iso = _iso_15924()
    alias_to_code = {v["alias"]: k for k, v in iso.items() if v["alias"]}

    rows: list[dict] = []
    for sc in sorted(ranges_by_script):
        cps = ranges_by_script[sc]
        chars = sum(e - s + 1 for s, e in cps)
        code = Unicode.get_script_iso_code(sc) or alias_to_code.get(sc) or sc
        info = iso.get(code, {})
        rows.append(
            {
                "code": code,
                "name": info.get("name") or sc,
                "french": info.get("french") or "",
                "script": sc,
                "chars": chars,
                "version": _min_age(cps) or info.get("age") or "",
                "notes": _NOTES.get(sc, ""),
            }
        )
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def _overlap(ranges: list[tuple[int, int]], qs: int, qe: int) -> tuple[int, list[tuple[int, int]]]:
    """(count, merged sub-ranges) of ``ranges`` ∩ [qs, qe]. Ranges must be sorted."""
    count = 0
    subs: list[tuple[int, int]] = []
    for s, e in ranges:
        if e < qs:
            continue
        if s > qe:
            break
        a, b = max(s, qs), min(e, qe)
        count += b - a + 1
        if subs and a <= subs[-1][1] + 1:
            subs[-1] = (subs[-1][0], max(subs[-1][1], b))
        else:
            subs.append((a, b))
    return count, subs


@functools.lru_cache(maxsize=32)
def script_blocks(code: str) -> list[dict]:
    """Per-block breakdown of a script in the latest release.

    Returns only blocks containing at least one character of the script, as
    ``{name, chars, ranges}`` where ``ranges`` is a list of ``XXXX..XXXX`` /
    ``XXXX`` strings for the contiguous runs inside that block.
    """
    ranges_by_script = _script_ranges()
    iso = _iso_15924()
    sc = (iso.get(code) or {}).get("alias") or code
    cps = ranges_by_script.get(sc, [])

    table, names = Unicode._block_data()
    out: list[dict] = []
    for s, e, idx in table:
        if 0xD800 <= s <= 0xDFFF:
            continue
        count, subs = _overlap(cps, s, e)
        if count == 0:
            continue
        out.append(
            {
                "name": names[idx],
                "chars": count,
                "ranges": [f"{a:04X}..{z:04X}" if a != z else f"{a:04X}" for a, z in subs],
            }
        )
    return out
