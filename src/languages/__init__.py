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
    Language,
    EInput,
    ELanguage,
    FIRST_LANGUAGE_INDEX,
    CASE_OFFSET,
    MAX_MONGOLIAN_WORD,
    FF_16,
    ZERO_16,
    ZERO_32,
)

from .default import Default
from .manchu import Manchu
from .mongolian import Mongolian
from .phagsPa import PhagsPa
from .tibetan import Tibetan
from .unicode import Unicode
from .uyghur import Uyghur
from .yi import Yi
from .input import Input, InputType, StatusType, InputMethod

__all__ = [
    "Language",
    "InputType",
    "ELanguage",
    "Default",
    "Manchu",
    "Mongolian",
    "PhagsPa",
    "Tibetan",
    "Unicode",
    "Uyghur",
    "Yi",
    "Input",
    "InputType",
    "StatusType",
    "InputMethod",
    "FIRST_LANGUAGE_INDEX",
    "CASE_OFFSET",
    "MAX_MONGOLIAN_WORD",
    "FF_16",
    "ZERO_16",
    "ZERO_32",
]
