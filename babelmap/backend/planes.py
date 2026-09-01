"""Unicode Planes dialog data — per-plane stats + per-plane block lists.

Everything is reused from ``babelsoft.unicode.core.Unicode`` (the dedicated
data-parsing library) — nothing is hardcoded:

* Plane names / abbreviations / reserved status: ``Unicode.get_plane_name``,
  ``get_plane_abbreviation``, ``is_plane_reserved``.
* Block lists: ``Unicode._block_data`` (current release ``Blocks.txt``).
* Per-block character counts: ``Unicode._assigned_codepoints`` (current
  release ``UnicodeData.txt``, First/Last ranges expanded).

Character counts follow the C++ ``CDialogPlanes`` / ``GetCharactersPerPlane``
semantics: a plane's characters are the characters in its blocks, excluding
surrogates (BMP only); ``unassigned`` is
``65536 - noncharacters - surrogates - characters``.
"""

from __future__ import annotations

import bisect
import functools

from babelsoft.unicode.core import Unicode


@functools.lru_cache(maxsize=1)
def _blocks() -> list[dict]:
    """Latest-release blocks: ``[{name, start, end, chars}]``, excluding surrogates."""
    table, names = Unicode._block_data()
    cps = Unicode._assigned_codepoints()
    out: list[dict] = []
    for s, e, idx in table:
        if 0xD800 <= s <= 0xDFFF:
            continue
        chars = bisect.bisect_right(cps, e) - bisect.bisect_left(cps, s)
        out.append({"name": names[idx], "start": s, "end": e, "chars": chars})
    return out


def _plane_blocks(plane: int) -> list[dict]:
    """Blocks of a plane in the latest release."""
    return [b for b in _blocks() if (b["start"] >> 16) == plane]


@functools.lru_cache(maxsize=1)
def plane_summary() -> list[dict]:
    """One row per plane: ``{plane, name, abbreviation, reserved, blocks, chars, unassigned}``."""
    rows: list[dict] = []
    for plane in range(17):
        blks = _plane_blocks(plane)
        chars = sum(b["chars"] for b in blks)
        surrogates = 2048 if plane == 0 else 0
        nonchars = 34 if plane == 0 else 2
        unassigned = 65536 - nonchars - surrogates - chars
        reserved = Unicode.is_plane_reserved(plane)
        rows.append(
            {
                "plane": plane,
                "name": "" if reserved else Unicode.get_plane_display_name(plane),
                "abbreviation": "" if reserved else Unicode.get_plane_abbreviation(plane),
                "reserved": reserved,
                "blocks": len(blks),
                "chars": chars,
                "unassigned": unassigned,
            }
        )
    return rows


@functools.lru_cache(maxsize=17)
def plane_blocks(plane: int) -> list[dict]:
    """Blocks contained in a plane (latest release): ``{name, start, end, chars}``."""
    return _plane_blocks(plane)
