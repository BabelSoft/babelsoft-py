"""
CJKV package — Python implementation of c/CJKV/

Provides CJK ideograph data, readings (Pinyin, Jyutping, Korean,
Vietnamese, Zhuang), and lookup infrastructure ported from the
BabelPad C++ codebase.
"""

from .cjk import CJK, CJK_BLOCK_SHORTCUTS, CJKFlags, IDS, IDSInfo, RS, Radical, SrcRef
from .lookup import Lookup
from .jyutping import Jyutping
from .korean import HangulSyllableType, Korean
from .pinyin import Pinyin
from .vietnamese import Vietnamese
from .zhuang import Zhuang

__all__ = [
    "CJK",
    "CJK_BLOCK_SHORTCUTS",
    "CJKFlags",
    "HangulSyllableType",
    "IDS",
    "IDSInfo",
    "Jyutping",
    "Korean",
    "Lookup",
    "Pinyin",
    "RS",
    "Radical",
    "SrcRef",
    "Vietnamese",
    "Zhuang",
]
