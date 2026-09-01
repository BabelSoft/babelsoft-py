"""Zhuang reading lookup for CJK characters.

Mirrors the C++ Zhuang class from Zhuang.h/Zhuang.cpp.
"""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from babelsoft.cjkv.lookup import Lookup
from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TsvParser


class Zhuang(Lookup):
    """Zhuang reading lookup for CJK characters."""

    # ── Zhuang tone table (mirrors C++ TableZhuangTones) ──
    _tones: ClassVar[list[str]] = ["", "", "z", "j", "x", "q", "h"]

    # ── Cached data ──
    _data_loaded: ClassVar[bool] = False
    _readings: ClassVar[dict[int, list[tuple[str, str]]]] = {}
    _inverse: ClassVar[dict[str, list[int]]] = {}

    @classmethod
    def _load_data(cls) -> None:
        """Load Zhuang reading data from TSV file (lazy, once)."""
        if cls._data_loaded:
            return
        cls._data_loaded = True
        cls._ensure_labels("cjk_zhuang_labels.tsv")

        raw: defaultdict[int, list[tuple[str, str]]] = defaultdict(list)
        inverse: defaultdict[str, list[int]] = defaultdict(list)

        _zhuang_tones = frozenset("zjxqh")
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_readings.tsv"):
            if len(row) < 3 or row[1] != "kZhuang":
                continue
            cp = int(row[0][2:], 16)
            for item in row[2].split():
                if len(item) > 1 and item[-1] in _zhuang_tones:
                    reading = item[:-1]
                    tone_char = item[-1]
                else:
                    reading = item
                    tone_char = ""
                raw[cp].append((reading, tone_char))
                inverse[reading].append(cp)

        cls._readings = dict(raw)
        cls._inverse = dict(inverse)

    @classmethod
    def get_reading_label(cls, index: int) -> str:
        """Get the Zhuang reading label string for a given index."""
        cls._load_data()
        if 0 <= index < len(cls._labels):
            return cls._apply_case(cls._labels[index])
        return ""

    @classmethod
    def get_zhuang_for_char(
        cls,
        cp: int,
        *,
        may_strip_tones: bool = False,
        first_reading_only: bool = False,
        separator: str = ", ",
    ) -> str:
        """Get Zhuang reading(s) for a CJK character.

        Args:
            cp: Unicode codepoint of the CJK character.
            may_strip_tones: If True, strip tones.
            first_reading_only: If True, return only the first reading.
            separator: Separator string between multiple readings.

        Returns:
            Comma-separated Zhuang reading string, or empty string if not found.
        """
        cls._load_data()
        entries = cls._readings.get(cp)
        if not entries:
            return ""

        result_parts: list[str] = []
        seen: set[str] = set()

        for reading, tone_char in entries:
            if may_strip_tones:
                text = reading
            else:
                text = reading + tone_char

            if cls._upper_case_readings:
                text = text.upper()

            if text not in seen:
                result_parts.append(text)
                seen.add(text)

            if first_reading_only:
                break

        return separator.join(result_parts)

    @classmethod
    def find_zhuang(
        cls,
        reading_label: str,
        tone: int = 0,
        *,
        filter_mode: str = "all",
    ) -> list[int]:
        """Find all CJK characters with a given Zhuang reading and optional tone.

        Args:
            reading_label: The Zhuang syllable (e.g., "it").
            tone: The tone index (0-6). 0 means any tone.
            filter_mode: Filter for traditional/simplified characters.

        Returns:
            List of matching codepoints.
        """
        cls._load_data()

        candidates = cls._inverse.get(reading_label, [])
        if not candidates:
            return []

        results: list[int] = []
        from babelsoft.cjkv.cjk import CJK

        for cp in candidates:
            entries = cls._readings.get(cp, [])
            if not entries:
                continue

            tone_match = any(tone == 0 or tone == cls._tones.index(t) if t in cls._tones else False for _, t in entries)
            # Simplified tone check: just compare tone index to the label
            if tone > 0 and tone < len(cls._tones):
                expected_tone = cls._tones[tone]
                tone_match = any(t == expected_tone for _, t in entries)
            elif tone == 0:
                tone_match = True
            else:
                tone_match = False

            if not tone_match:
                continue

            cjk = CJK(cp)
            if filter_mode == "traditional" and not cjk.filter_traditional():
                continue
            if filter_mode == "simplified" and not cjk.filter_simplified():
                continue

            results.append(cp)

        return sorted(set(results))
