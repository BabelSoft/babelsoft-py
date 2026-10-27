"""Base Lookup class - shared configuration for reading lookups.

Mirrors the C++ Lookup class from Lookup.h/Lookup.cpp.
Provides global settings for upper-case readings, tone numbers, and tone conversion.
"""

from __future__ import annotations

from typing import ClassVar

from babelsoft.utils_.dirs import Dirs
from babelsoft.utils_.parser import TsvParser


class Lookup:
    """Base class with shared configuration for CJK reading lookups."""

    _upper_case_readings: bool = False
    _tone_numbers: bool = False
    _convert_tones: bool = False
    _labels: ClassVar[list[str]] = []

    @classmethod
    def _ensure_labels(cls, filename: str) -> None:
        """Load label table from a single-column TSV file."""
        if cls._labels:
            return
        cls._labels = [row[0] for row in TsvParser.get_tsv(Dirs.BABELSOFT / filename)]

    @classmethod
    def use_upper_case_readings(cls, value: bool) -> None:
        """Set whether readings should be returned in upper case."""
        cls._upper_case_readings = value

    @classmethod
    def is_upper_case_readings(cls) -> bool:
        """Check if readings should be returned in upper case."""
        return cls._upper_case_readings

    @classmethod
    def use_tone_numbers(cls, value: bool) -> None:
        """Set whether tone numbers should be included in readings."""
        cls._tone_numbers = value

    @classmethod
    def is_tone_numbers(cls) -> bool:
        """Check if tone numbers should be included."""
        return cls._tone_numbers

    @classmethod
    def convert_tones(cls, value: bool) -> None:
        """Set whether tones should be converted."""
        cls._convert_tones = value

    @classmethod
    def is_convert_tones(cls) -> bool:
        """Check if tones should be converted."""
        return cls._convert_tones

    @classmethod
    def _apply_case(cls, text: str) -> str:
        """Apply upper-case setting to text."""
        return text.upper() if cls._upper_case_readings else text
