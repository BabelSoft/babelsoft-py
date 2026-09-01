"""Pinyin (Mandarin) reading lookup for CJK characters.

Mirrors the C++ Pinyin class from Pinyin.h/Pinyin.cpp.
"""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from babelsoft.cjkv.lookup import Lookup
from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TsvParser


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
        from babelsoft.cjkv.cjk import CJK

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

    @classmethod
    def get_readings(cls, cp: int) -> list[tuple[str, int]]:
        """Return all (reading, tone) entries for a codepoint (empty list if none)."""
        cls._load_data()
        return cls._readings.get(cp, [])

    @staticmethod
    def decomp(ch: int) -> tuple[int, int, int] | None:
        """Decompose a Pinyin reading codepoint into its three constituent parts.

        Equivalent to C++ Pinyin::Decomp(CHAR32 ch, CHAR32& ch1, CHAR32& ch2, CHAR32& ch3).
        Decomposes a single Unicode character that represents a composite Pinyin
        reading into up to three base letter codepoints.

        Returns:
            Tuple of (ch1, ch2, ch3) where unused positions are 0, or None if
            the character is not decomposable.
        """
        # Look up in the decomposition table
        decomp_map = Pinyin._load_decomp_table()
        if ch in decomp_map:
            return decomp_map[ch]
        return None

    @classmethod
    def _load_decomp_table(cls) -> dict[int, tuple[int, int, int]]:
        """Load the Pinyin decomposition table."""
        if hasattr(cls, "_decomp_cache"):
            return cls._decomp_cache

        table: dict[int, tuple[int, int, int]] = {}

        # Build from the Pinyin labels and vowel position tables
        cls._load_data()
        if not cls._labels:
            return table

        # For each Pinyin label, try to decompose multi-codepoint combinations
        for label in cls._labels:
            if len(label) > 1:
                cps = [ord(c) for c in label]
                if len(cps) == 2:
                    # Store as (ch1, ch2, 0)
                    key = (cps[0] << 16) | cps[1]
                    if key not in table:
                        table[key] = (cps[0], cps[1], 0)
                elif len(cps) == 3:
                    key = (cps[0] << 32) | (cps[1] << 16) | cps[2]
                    if key not in table:
                        table[key] = (cps[0], cps[1], cps[2])

        cls._decomp_cache = table
        return table
