"""
CJKV package — Python implementation of c/CJKV/

Provides CJK ideograph data, readings (Pinyin, Jyutping, Korean,
Vietnamese, Zhuang), and lookup infrastructure ported from the
BabelPad C++ codebase.
"""

from .cjk import CJK, CJK_BLOCK_SHORTCUTS, IDS, RS, CJKFlags, IDSInfo, Radical, SrcRef
from .jyutping import Jyutping
from .korean import HangulSyllableType, Korean
from .lookup import Lookup
from .pinyin import Pinyin
from .vietnamese import Vietnamese
from .zhuang import Zhuang

__all__ = [
    "CJK",
    "CJK_BLOCK_SHORTCUTS",
    "IDS",
    "RS",
    "CJKFlags",
    "HangulSyllableType",
    "IDSInfo",
    "Jyutping",
    "Korean",
    "Lookup",
    "Pinyin",
    "Radical",
    "SrcRef",
    "Vietnamese",
    "Zhuang",
]
