"""Unicode package — ported from c/Unicode/."""

from src.unicode.core import Block, CodePoint, Unicode
from src.unicode.enums import (
    BidiClass,
    DecompositionType,
    EastAsianWidth,
    GeneralCategory,
    JoiningType,
    LineBreak,
)
from src.unicode.uca import (
    COLLATE_EQUAL,
    COLLATE_GREATER_THAN,
    COLLATE_LESS_THAN,
    Locale,
    SortOptions,
    SortType,
    UCA,
    VariableWeighting,
    collation_compare,
    collation_sort_key,
)

__all__ = [
    "Block",
    "CodePoint",
    "BidiClass",
    "Unicode",
    "UCA",
    "DecompositionType",
    "EastAsianWidth",
    "GeneralCategory",
    "JoiningType",
    "LineBreak",
    "SortOptions",
    "SortType",
    "Locale",
    "VariableWeighting",
    "COLLATE_EQUAL",
    "COLLATE_GREATER_THAN",
    "COLLATE_LESS_THAN",
    "collation_compare",
    "collation_sort_key",
]
