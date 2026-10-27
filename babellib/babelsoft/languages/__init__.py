"""
Languages package - Python implementation of c/Languages/

Provides language-specific input methods and text conversion utilities
ported from the BabelPad C++ codebase.

Modules:
    language           - Base Language class with input processing
    language_default   - Default handler for CJK conversions
    language_manchu    - Manchu script input (Latin -> Mongolian block)
    language_mongolian - Mongolian script input (Latin -> Mongolian block)
    language_phags_pa  - Phags-pa script input
    language_tibetan   - Tibetan script input (Extended Wylie)
    language_unicode   - Unicode normalization and case operations
    language_uyghur    - Uyghur Arabic script input
    language_yi        - Yi script input and conversion
    text_input         - Custom text input method manager
"""

from .class_ import (
    CASE_OFFSET,
    FF_16,
    FIRST_LANGUAGE_INDEX,
    MAX_MONGOLIAN_WORD,
    ZERO_16,
    ZERO_32,
    EInput,
    ELanguage,
    Language,
)
from .default import Default
from .input import Input, InputMethod, InputType, StatusType
from .manchu import Manchu
from .mongolian import Mongolian
from .phags_pa import PhagsPa
from .tibetan import Tibetan
from .unicode import Unicode
from .uyghur import Uyghur
from .yi import Yi

__all__ = [
    "CASE_OFFSET",
    "FF_16",
    "FIRST_LANGUAGE_INDEX",
    "MAX_MONGOLIAN_WORD",
    "ZERO_16",
    "ZERO_32",
    "Default",
    "EInput",
    "ELanguage",
    "Input",
    "InputMethod",
    "InputType",
    "Language",
    "Manchu",
    "Mongolian",
    "PhagsPa",
    "StatusType",
    "Tibetan",
    "Unicode",
    "Uyghur",
    "Yi",
]
