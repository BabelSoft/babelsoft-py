"""Korean (Yale) reading lookup for CJK characters, with Hangul utilities.

Mirrors the C++ Korean class from Korean.h/Korean.cpp.
Includes Hangul decomposition, composition, and Yale Korean reading lookup.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from typing import ClassVar

from src.cjkv.lookup import Lookup
from src.utils_.dirs import Dirs
from src.utils_.parser import TsvParser

# ── Hangul Constants ──
HANGUL_S_FIRST = 0xAC00
HANGUL_S_LAST = 0xD7A3
HANGUL_JAMO_FIRST = 0x1100
HANGUL_JAMO_LAST = 0x11FF
HANGUL_LETTER_FIRST = 0x3131
HANGUL_LETTER_LAST = 0x318E
HANGUL_S_BASE = 0xAC00
HANGUL_J_BASE = 0x1100
HANGUL_L_BASE = 0x1100
HANGUL_V_BASE = 0x1161
HANGUL_T_BASE = 0x11A7
HANGUL_S_COUNT = 11172
HANGUL_L_COUNT = 19
HANGUL_V_COUNT = 21
HANGUL_T_COUNT = 28
HANGUL_N_COUNT = HANGUL_V_COUNT * HANGUL_T_COUNT  # 588


class HangulSyllableType(enum.Enum):
    """Hangul syllable type (mirrors C++ EHangulSyllableType)."""

    L = "L"  # Leading consonant only
    LV = "LV"  # Leading + vowel
    LVT = "LVT"  # Leading + vowel + trailing
    T = "T"  # Trailing consonant only
    V = "V"  # Vowel only
    NA = "NA"  # Not applicable


# Jamo-to-Letter mapping: index is offset from HANGUL_JAMO_FIRST, value is Hangul letter
_JAMO_TO_LETTER: list[int] = [
    0x3131,  # ㄱ  (0x1100 → 0x3131)
    0x3132,  # ㄲ
    0x3134,  # ㄴ
    0x3137,  # ㄷ
    0x3138,  # ㄸ
    0x3139,  # ㄹ
    0x3141,  # ㅁ
    0x3142,  # ㅂ
    0x3143,  # ㅃ
    0x3145,  # ㅅ
    0x3146,  # ㅆ
    0x3147,  # ㅇ
    0x3148,  # ㅈ
    0x3149,  # ㅉ
    0x314A,  # ㅊ
    0x314B,  # ㅋ
    0x314C,  # ㅌ
    0x314D,  # ㅍ
    0x314E,  # ㅎ
    0x314F,  # ㅏ (vowel: 0x1161 → 0x314F)
    0x3150,  # ㅐ
    0x3151,  # ㅑ
    0x3152,  # ㅒ
    0x3153,  # ㅓ
    0x3154,  # ㅔ
    0x3155,  # ㅕ
    0x3156,  # ㅖ
    0x3157,  # ㅗ
    0x3158,  # ㅘ
    0x3159,  # ㅙ
    0x315A,  # ㅚ
    0x315B,  # ㅛ
    0x315C,  # ㅜ
    0x315D,  # ㅝ
    0x315E,  # ㅞ
    0x315F,  # ㅟ
    0x3160,  # ㅠ
    0x3161,  # ㅡ
    0x3162,  # ㅢ
    0x3163,  # ㅣ
    0x3131,  # ㄱ (trailing: 0x11A8 → same letters)
    0x3132,  # ㄲ
    0x3134,  # ㄳ (note: some combos differ)
    0x3137,  # ㄴ
    0x3138,  # ㄵ
    0x3139,  # ㄶ
    0x3141,  # ㄷ
    0x3142,  # ㄹ
    0x3143,  # ㄺ
    0x3145,  # ㄻ
    0x3146,  # ㄼ
    0x3147,  # ㄽ
    0x3148,  # ㄾ
    0x3149,  # ㄿ
    0x314A,  # ㅀ
    0x314B,  # ㅁ
    0x314C,  # ㅂ
    0x314D,  # ㅄ
    0x314E,  # ㅅ
    0x314F,  # ㅆ
    0x3150,  # ㅇ
    0x3151,  # ㅈ
    0x3152,  # ㅊ
    0x3153,  # ㅋ
    0x3154,  # ㅌ
    0x3155,  # ㅍ
    0x3156,  # ㅎ
]


class Korean(Lookup):
    """Korean (Yale) reading lookup with Hangul utilities."""

    # ── Jamo short names ──
    _jamo_short_names_leading: ClassVar[list[str]] = [
        "G",
        "GG",
        "N",
        "D",
        "DD",
        "R",
        "M",
        "B",
        "BB",
        "S",
        "SS",
        "",
        "J",
        "JJ",
        "C",
        "K",
        "T",
        "P",
        "H",
    ]
    _jamo_short_names_vowel: ClassVar[list[str]] = [
        "A",
        "AE",
        "YA",
        "YAE",
        "EO",
        "E",
        "YEO",
        "YE",
        "O",
        "WA",
        "WAE",
        "OE",
        "YO",
        "U",
        "WEO",
        "WE",
        "WI",
        "YU",
        "EU",
        "YI",
        "I",
    ]
    _jamo_short_names_trailing: ClassVar[list[str]] = [
        "G",
        "GG",
        "GS",
        "N",
        "NJ",
        "NH",
        "D",
        "L",
        "LG",
        "LM",
        "LB",
        "LS",
        "LT",
        "LP",
        "LH",
        "M",
        "B",
        "BS",
        "S",
        "SS",
        "NG",
        "J",
        "C",
        "K",
        "T",
        "P",
        "H",
    ]

    # ── Cached reading data ──
    _data_loaded: ClassVar[bool] = False
    _readings: ClassVar[dict[int, list[str]]] = {}

    @classmethod
    def _load_data(cls) -> None:
        """Load Korean reading data from TSV file (lazy, once)."""
        if cls._data_loaded:
            return
        cls._data_loaded = True
        cls._ensure_labels("cjk_korean_labels.tsv")

        raw: defaultdict[int, list[str]] = defaultdict(list)

        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_readings.tsv"):
            if len(row) < 3 or row[1] != "kKorean":
                continue
            cp = int(row[0][2:], 16)
            for reading in row[2].split():
                raw[cp].append(reading)

        cls._readings = dict(raw)

    # ── Hangul Utility Methods ──

    @staticmethod
    def is_lead_jamo(cp: int) -> bool:
        """Check if a codepoint is a Hangul leading consonant jamo."""
        if HANGUL_L_BASE <= cp < HANGUL_L_BASE + HANGUL_L_COUNT:
            return True
        if 0xA960 <= cp < 0xA97D:
            return True
        return False

    @staticmethod
    def is_vowel_jamo(cp: int) -> bool:
        """Check if a codepoint is a Hangul vowel jamo."""
        if HANGUL_V_BASE <= cp < HANGUL_V_BASE + HANGUL_V_COUNT:
            return True
        if 0xD7B0 <= cp < 0xD7C7:
            return True
        return False

    @staticmethod
    def is_trail_jamo(cp: int) -> bool:
        """Check if a codepoint is a Hangul trailing consonant jamo."""
        if HANGUL_T_BASE < cp < HANGUL_T_BASE + HANGUL_T_COUNT:
            return True
        if 0xD7CB <= cp < 0xD7FC:
            return True
        return False

    @classmethod
    def get_hangul_syllable_type(cls, cp: int) -> HangulSyllableType:
        """Get the Hangul syllable type for a given codepoint."""
        # Hangul Jamo block
        if 0x1100 <= cp <= 0x115F:
            return HangulSyllableType.L
        if 0x1160 <= cp <= 0x11A7:
            return HangulSyllableType.V
        if 0x11A8 <= cp <= 0x11FF:
            return HangulSyllableType.T

        # Hangul Jamo Extended-A
        if 0xA960 <= cp <= 0xA97C:
            return HangulSyllableType.L

        # Hangul Jamo Extended-B
        if 0xD7B0 <= cp <= 0xD7C6:
            return HangulSyllableType.V
        if 0xD7CB <= cp <= 0xD7FB:
            return HangulSyllableType.T

        # Hangul Syllables
        if HANGUL_S_FIRST <= cp <= HANGUL_S_LAST:
            if cls.is_hangul_open_syllable(cp):
                return HangulSyllableType.LV
            return HangulSyllableType.LVT

        return HangulSyllableType.NA

    @staticmethod
    def is_hangul_open_syllable(ch: int) -> bool:
        """Check if a Hangul syllable has no trailing consonant (open/LV type)."""
        if not (HANGUL_S_FIRST <= ch <= HANGUL_S_LAST):
            return False
        return (ch - HANGUL_S_BASE) % HANGUL_T_COUNT == 0

    @staticmethod
    def get_hangul_decomposition(ch: int) -> tuple[int, int, int]:
        """Decompose a Hangul syllable into leading, vowel, and trailing jamo.

        Returns:
            Tuple of (leading_cp, vowel_cp, trailing_cp). Unused slots are 0.
        """
        if not (HANGUL_S_FIRST <= ch <= HANGUL_S_LAST):
            return (0, 0, 0)

        n_index = ch - HANGUL_S_BASE
        if not (0 <= n_index < HANGUL_S_COUNT):
            return (0, 0, 0)

        leading = HANGUL_L_BASE + n_index // HANGUL_N_COUNT
        vowel = HANGUL_V_BASE + (n_index % HANGUL_N_COUNT) // HANGUL_T_COUNT
        trailing = HANGUL_T_BASE + n_index % HANGUL_T_COUNT

        if trailing == HANGUL_T_BASE:
            trailing = 0

        return (leading, vowel, trailing)

    @staticmethod
    def compose_hangul(leading: int, vowel: int, trailing: int) -> int:
        """Compose a Hangul syllable from leading, vowel, and trailing jamo.

        Returns:
            The composed Hangul syllable codepoint, or 0 if invalid.
        """
        if leading == 0 or vowel == 0:
            return 0

        l_idx = leading - HANGUL_L_BASE
        v_idx = vowel - HANGUL_V_BASE
        if trailing == 0:
            t_idx = 0
        else:
            t_idx = trailing - HANGUL_T_BASE

        if not (0 <= l_idx < HANGUL_L_COUNT):
            return 0
        if not (0 <= v_idx < HANGUL_V_COUNT):
            return 0
        if not (0 <= t_idx < HANGUL_T_COUNT):
            return 0

        return ((l_idx * HANGUL_V_COUNT + v_idx) * HANGUL_T_COUNT + t_idx) + HANGUL_S_BASE

    @classmethod
    def get_first_jamo_for_letter(cls, letter: int) -> int:
        """Get the first (leading) jamo for a Hangul compatibility letter.

        Maps letter codepoints (0x3131+) to jamo codepoints (0x1100+).
        """
        for i, lt in enumerate(_JAMO_TO_LETTER):
            if lt == letter:
                return HANGUL_JAMO_FIRST + i
        return letter

    @classmethod
    def get_last_jamo_for_letter(cls, letter: int) -> int:
        """Get the last (trailing) jamo for a Hangul compatibility letter."""
        result = letter
        for i, lt in enumerate(_JAMO_TO_LETTER):
            if lt == letter:
                result = HANGUL_JAMO_FIRST + i
        return result

    @classmethod
    def get_jamo_short_name(cls, jamo_cp: int) -> str:
        """Get the short name for a Hangul jamo character."""
        if cls.is_lead_jamo(jamo_cp):
            idx = jamo_cp - HANGUL_L_BASE
            if 0 <= idx < len(cls._jamo_short_names_leading):
                return cls._jamo_short_names_leading[idx]
        elif cls.is_vowel_jamo(jamo_cp):
            idx = jamo_cp - HANGUL_V_BASE
            if 0 <= idx < len(cls._jamo_short_names_vowel):
                return cls._jamo_short_names_vowel[idx]
        elif cls.is_trail_jamo(jamo_cp):
            idx = jamo_cp - HANGUL_T_BASE
            if 0 <= idx < len(cls._jamo_short_names_trailing):
                return cls._jamo_short_names_trailing[idx]
        return ""

    @classmethod
    def get_hangul_name(cls, cp: int, full_name: bool = True) -> str:
        """Get the Unicode name for a Hangul syllable."""
        if not (HANGUL_S_FIRST <= cp <= HANGUL_S_LAST):
            return ""

        leading, vowel, trailing = cls.get_hangul_decomposition(cp)
        if leading == 0:
            return ""

        parts = []
        if full_name:
            parts.append("HANGUL SYLLABLE")

        # Leading consonant
        l_idx = leading - HANGUL_L_BASE
        if 0 <= l_idx < len(cls._jamo_short_names_leading):
            parts.append(cls._jamo_short_names_leading[l_idx])

        # Vowel
        v_idx = vowel - HANGUL_V_BASE
        if 0 <= v_idx < len(cls._jamo_short_names_vowel):
            parts.append(cls._jamo_short_names_vowel[v_idx])

        # Trailing consonant
        if trailing:
            t_idx = trailing - HANGUL_T_BASE
            if 0 <= t_idx < len(cls._jamo_short_names_trailing):
                parts.append(cls._jamo_short_names_trailing[t_idx])

        return " ".join(parts)

    @classmethod
    def get_character_for_short_name(cls, short_name: str) -> int:
        """Get the jamo character for a given short name."""
        for i, name in enumerate(cls._jamo_short_names_leading):
            if name.upper() == short_name.upper():
                return HANGUL_L_BASE + i
        for i, name in enumerate(cls._jamo_short_names_vowel):
            if name.upper() == short_name.upper():
                return HANGUL_V_BASE + i
        for i, name in enumerate(cls._jamo_short_names_trailing):
            if name.upper() == short_name.upper():
                return HANGUL_T_BASE + i
        return 0

    # ── Reading Lookup Methods ──

    @classmethod
    def get_korean_for_char(
        cls,
        cp: int,
        *,
        first_reading_only: bool = False,
        separator: str = ", ",
    ) -> str:
        """Get Yale Korean reading(s) for a CJK character.

        Args:
            cp: Unicode codepoint of the CJK character.
            first_reading_only: If True, return only the first reading.
            separator: Separator string between multiple readings.

        Returns:
            Comma-separated Yale Korean reading string, or empty string if not found.
        """
        cls._load_data()
        entries = cls._readings.get(cp)
        if not entries:
            return ""

        result_parts: list[str] = []

        for reading in entries:
            text = cls._apply_case(reading)
            result_parts.append(text)

            if first_reading_only:
                break

        return separator.join(result_parts)
