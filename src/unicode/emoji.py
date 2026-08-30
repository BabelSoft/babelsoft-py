"""Emoji data and Emojipedia-style search.

Parses the UTS #51 ``emoji-test.txt`` shipped with the UCD so every RGI emoji
has its CLDR short name, group/subgroup, emoji version and codepoints.

``search()`` matches the way emojipedia.org does:
  * by codepoint (``1f600``, ``U+1F600``, ``1F600 FE0F`` …),
  * by CLDR short name (whole query, word prefix, or token substring —
    ``grin`` matches *grinning face*),
  * plus a small English synonym expansion (``smile`` → smiling/grinning…).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass

from src.utils_.dirs import Dirs
from src.utils_.parser import TsvParser, TxtParser


@dataclass(frozen=True)
class Emoji:
    """A single RGI emoji (single codepoint or sequence)."""

    codepoints: tuple[int, ...]
    status: str  # fully-qualified / minimally-qualified / unqualified / component
    version: str  # e.g. "0.6" (from E0.6)
    name: str  # CLDR short name, e.g. "grinning face"
    group: str  # e.g. "Smileys & Emotion"
    subgroup: str  # e.g. "face-smiling"

    @property
    def text(self) -> str:
        """The emoji as a display string (joined codepoints)."""
        return "".join(chr(cp) for cp in self.codepoints)

    @property
    def display_name(self) -> str:
        """Name shown in pickers: country flags use the ISO 3166 registered
        official name (e.g. "flag: Korea, Republic of"); otherwise the CLDR
        short name."""
        if self.subgroup == "country-flag":
            iso = _iso3166_names().get(_flag_code(self.codepoints) or "")
            if iso:
                return f"flag: {iso}"
        return self.name

    def to_dict(self) -> dict:
        return {
            "codepoints": list(self.codepoints),
            "string": self.text,
            "status": self.status,
            "version": self.version,
            "name": self.display_name,
            "group": self.group,
            "subgroup": self.subgroup,
        }


_GROUP_RE = re.compile(r"^#\s*group:\s*(.+)$")
_SUBGROUP_RE = re.compile(r"^#\s*subgroup:\s*(.+)$")
# comment part after '#': "<glyph> E<version> <CLDR short name>"
_VER_NAME_RE = re.compile(r"\sE(\d+\.\d+)\s+(.+)$")


def _parse_entry(line: str, group: str, subgroup: str) -> Emoji | None:
    code_part, sep, tail = line.partition(";")
    if not sep:
        return None
    status = tail.split("#", 1)[0].strip()
    comment = tail.partition("#")[2]
    m = _VER_NAME_RE.search(comment)
    if not m:
        return None
    try:
        cps = tuple(int(x, 16) for x in code_part.split())
    except ValueError:
        return None
    if not cps:
        return None
    name = m.group(2).strip()
    return Emoji(cps, status, m.group(1), name, group, subgroup)


@functools.lru_cache(maxsize=1)
def _load() -> list[Emoji]:
    """Parse emoji-test.txt into a list in CLDR (browse) order."""
    entries: list[Emoji] = []
    group = subgroup = ""
    for line in TxtParser.get_txt(Dirs.EMOJI / "emoji-test.txt"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            mg = _GROUP_RE.match(s)
            if mg:
                group = mg.group(1).strip()
                continue
            ms = _SUBGROUP_RE.match(s)
            if ms:
                subgroup = ms.group(1).strip()
                continue
            continue
        e = _parse_entry(s, group, subgroup)
        if e is not None:
            entries.append(e)
    return entries


def all_emoji() -> list[Emoji]:
    """All RGI emoji in CLDR order (fully-qualified + components only)."""
    return _display_entries()


@functools.lru_cache(maxsize=1)
def _display_entries() -> list[Emoji]:
    """RGI emoji shown in a picker/search: fully-qualified + components only
    (Emojipedia shows these; minimally-qualified / unqualified are dupes),
    with country flags restricted to valid ISO 3166 codes plus EU/UN."""
    iso = _iso3166_names()
    out: list[Emoji] = []
    for e in _load():
        if e.status not in ("fully-qualified", "component"):
            continue
        if e.subgroup == "country-flag":
            code = _flag_code(e.codepoints)
            if not code or code not in iso:
                continue  # drop non-ISO codes (e.g. AC, CQ, TA, XK)
        out.append(e)
    return out


def _flag_code(cps: tuple[int, ...]) -> str | None:
    """Two-letter code of a regional-indicator flag sequence, else None."""
    if len(cps) != 2:
        return None
    letters: list[str] = []
    for cp in cps:
        if 0x1F1E6 <= cp <= 0x1F1FF:
            letters.append(chr(ord("A") + cp - 0x1F1E6))
        else:
            return None
    return "".join(letters)


@functools.lru_cache(maxsize=1)
def _iso3166_names() -> dict[str, str]:
    """alpha-2 code -> ISO 3166-1 English short name (registered official
    name), from data/scripts/iso3166.tsv. Includes EU/UN (not in ISO 3166-1
    but valid flag codes per UTS #51 Annex B)."""
    mapping: dict[str, str] = {}
    for row in TsvParser.get_tsv(Dirs.DATA / "scripts" / "iso3166.tsv"):
        if len(row) >= 2 and row[0] != "code":
            mapping[row[0]] = row[1]
    return mapping


# ── Search ────────────────────────────────────────────────────────────

# Small English synonym expansion for common queries whose words are not
# literal CLDR name substrings (e.g. "smile" → smiling / grinning).
_SYNONYMS: dict[str, str] = {
    "smile": "smiling grin laughing joy",
    "smiley": "smiling grin",
    "happy": "smiling grinning beaming joy laugh",
    "laugh": "laughing grinning joy",
    "sad": "crying frowning tear pensive weary disappointed",
    "cry": "crying tear sob",
    "angry": "angry rage pouting",
    "mad": "angry rage",
    "love": "heart kiss",
    "kiss": "kiss heart",
    "cool": "sunglasses",
    "shy": "blush",
    "surprise": "astonished amazed shocked",
    "shock": "astonished",
    "wow": "astonished amazed",
    "sleep": "sleeping yawning tired",
    "tired": "tired yawning sleeping",
    "money": "money dollar banknote coin",
    "fire": "fire",
    "star": "star",
    "food": "pizza burger taco sandwich salad",
    "drink": "coffee beer wine tea cocktail",
    "flag": "flag",
    "cat": "cat",
    "dog": "dog",
    "heart": "heart",
    "weather": "sun cloud rain snow wind tornado",
}


def _codepoint_query(q: str) -> tuple[int, ...] | None:
    """Parse a hex codepoint query like ``1f600`` / ``U+1F600`` / ``1F600 FE0F``."""
    m = re.fullmatch(r"(?:u\+)?([0-9a-f]{2,6}(?:\s+[0-9a-f]{2,6})*)", q)
    if not m:
        return None
    try:
        return tuple(int(x, 16) for x in m.group(1).split())
    except ValueError:
        return None


def _token_in(name: str, tok: str) -> bool:
    """True if tok starts any word of name or is a substring of name."""
    return any(w.startswith(tok) for w in name.split()) or tok in name


def search(query: str, limit: int = 80) -> list[Emoji]:
    """Emojipedia-style search over names, codepoints and synonyms.

    Empty query returns the beginning of the CLDR browse order.
    """
    q = query.strip().lower()
    if not q:
        return _display_entries()[:limit]

    cps = _codepoint_query(q)
    if cps is not None:
        return [e for e in _display_entries() if set(cps) <= set(e.codepoints)][:limit]

    tokens = [t for t in re.split(r"[^0-9a-z]+", q) if t]
    syn_words = _SYNONYMS.get(q, "").split()

    scored: list[tuple[int, Emoji]] = []
    for e in _display_entries():
        # Match against both the CLDR short name and the displayed name
        # (country flags show the ISO 3166 official name).
        names = {e.name.lower(), e.display_name.lower()}
        score = 0
        for n in names:
            if n == q:
                score = max(score, 500)
            elif n.startswith(q):
                score = max(score, 300)
            elif any(w.startswith(q) for w in n.split()):
                score = max(score, 200)
            elif q in n:
                score = max(score, 100)
        if tokens and any(all(_token_in(n, t) for t in tokens) for n in names):
            score += 120
        if syn_words and any(any(w in n for w in syn_words) for n in names):
            score += 60
        if score:
            scored.append((score, e))

    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [e for _, e in scored[:limit]]
