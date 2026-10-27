"""Unicode package — ported from c/Unicode/."""

from babelsoft.unicode.core import Block, CodePoint, Unicode
from babelsoft.unicode.enums import (
    BidiClass,
    DecompositionType,
    EastAsianWidth,
    GeneralCategory,
    JoiningType,
    LineBreak,
)
from babelsoft.unicode.uca import (
    COLLATE_EQUAL,
    COLLATE_GREATER_THAN,
    COLLATE_LESS_THAN,
    UCA,
    Locale,
    SortOptions,
    SortType,
    VariableWeighting,
    collation_compare,
    collation_sort_key,
)

__all__ = [
    "COLLATE_EQUAL",
    "COLLATE_GREATER_THAN",
    "COLLATE_LESS_THAN",
    "UCA",
    "BidiClass",
    "Block",
    "CodePoint",
    "DecompositionType",
    "EastAsianWidth",
    "GeneralCategory",
    "JoiningType",
    "LineBreak",
    "Locale",
    "SortOptions",
    "SortType",
    "Unicode",
    "VariableWeighting",
    "collation_compare",
    "collation_sort_key",
]
