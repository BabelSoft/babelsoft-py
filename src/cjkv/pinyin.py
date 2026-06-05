"""Pinyin (Mandarin) reading lookup for CJK characters.

Mirrors the C++ Pinyin class from Pinyin.h/Pinyin.cpp.
"""

from __future__ import annotations

import functools
from collections import defaultdict
from typing import ClassVar

from src.cjkv.lookup import Lookup
from src.utils_.dirs import Dirs
from src.utils_.parser import TsvParser


class Pinyin(Lookup):
    """Pinyin (Mandarin romanization) lookup for CJK characters."""

    # ── Cached data ──
    # ── Cached data ──
    _data_loaded: ClassVar[bool] = False
    _readings: ClassVar[dict[int, list[tuple[str, int]]]] = {}
    _inverse: ClassVar[dict[str, list[int]]] = {}

    @classmethod
    def _load_data(cls) -> None:
        """Load Pinyin reading data from TSV file (lazy, once)."""
        if cls._data_loaded:
            return
        cls._data_loaded = True
        cls._ensure_labels("cjk_pinyin_labels.tsv")

        raw: defaultdict[int, list[tuple[str, int]]] = defaultdict(list)
        inverse: defaultdict[str, list[int]] = defaultdict(list)

        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_readings.tsv"):
            if len(row) < 3 or row[1] != "kMandarin":
                continue
            cp = int(row[0][2:], 16)
            for item in row[2].split():
                reading = item.rstrip("0123456789")
                tone = int(item[len(reading) :])
                raw[cp].append((reading, tone))
                inverse[reading].append(cp)

        cls._readings = dict(raw)
        cls._inverse = dict(inverse)

    @classmethod
    def get_reading_label(cls, index: int) -> str:
        """Get the Pinyin reading label string for a given index."""
        cls._load_data()
        if 0 <= index < len(cls._labels):
            return cls._labels[index]
        return ""

    @classmethod
    def get_pinyin_for_char(
        cls,
        cp: int,
        *,
        may_strip_tones: bool = False,
        first_reading_only: bool = False,
        separator: str = ", ",
    ) -> str:
        """Get Pinyin reading(s) for a CJK character.

        Args:
            cp: Unicode codepoint of the CJK character.
            may_strip_tones: If True, strip tones when _convert_tones is True.
            first_reading_only: If True, return only the first reading.
            separator: Separator string between multiple readings.

        Returns:
            Comma-separated Pinyin reading string, or empty string if not found.
        """
        cls._load_data()
        entries = cls._readings.get(cp)
        if not entries:
            return ""

        include_tones = True
        if may_strip_tones and cls._convert_tones:
            include_tones = False

        result_parts: list[str] = []
        seen: set[str] = set()

        for reading, tone in entries:
            if include_tones:
                text = f"{reading}{tone}"
            else:
                text = reading

            if cls._upper_case_readings:
                text = text.upper()

            if text not in seen:
                result_parts.append(text)
                seen.add(text)

            if first_reading_only:
                break

        return separator.join(result_parts)

    @classmethod
    def find_pinyin(
        cls,
        reading_label: str,
        tone: int = 0,
        *,
        filter_mode: str = "all",
    ) -> list[int]:
        """Find all CJK characters with a given Pinyin reading and optional tone.

        Args:
            reading_label: The Pinyin syllable (e.g., "yi").
            tone: The tone number (1-5). 0 means any tone.
            filter_mode: Filter for traditional/simplified characters.

        Returns:
            List of matching codepoints.
        """
        cls._load_data()

        candidates = cls._inverse.get(reading_label, [])
        if not candidates:
            return []

        results: list[int] = []
        from src.cjkv.cjk import CJK

        for cp in candidates:
            entries = cls._readings.get(cp, [])
            if not entries:
                continue

            tone_match = any(tone == 0 or tone == t for _, t in entries)
            if not tone_match:
                continue

            cjk = CJK(cp)
            if filter_mode == "traditional" and not cjk.filter_traditional():
                continue
            if filter_mode == "simplified" and not cjk.filter_simplified():
                continue

            results.append(cp)

        return sorted(set(results))
