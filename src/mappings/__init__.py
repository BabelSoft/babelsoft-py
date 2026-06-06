"""
Mappings package — character encoding conversion (ported from c/Mappings/).

Provides Mapper class with Unicode ↔ legacy encoding conversion,
plus encoding-specific helper classes for Big5, GB18030, CP932/936/949.
"""

from src.mappings.mapper import (
    Big5,
    CP932,
    CP936,
    CP949,
    Encoding,
    GB18030,
    Mapper,
)

__all__ = [
    "Big5",
    "CP932",
    "CP936",
    "CP949",
    "Encoding",
    "GB18030",
    "Mapper",
]
