"""
UCA — Unicode Collation Algorithm (ported from c/Unicode/UCA.cpp)

Implements the full UCA with DUCET/CLDR tables, contractions,
implicit weights for CJK and unassigned characters, and
locale-specific tailoring.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import ClassVar

from babelsoft.main_.babel_string import BabelString
from babelsoft.unicode.core import Unicode

# ─── Constants ────────────────────────────────────────────────────────

MAX_COLLATION_ELEMENTS = 18  # U+FDFA
COLLATE_LESS_THAN = -1
COLLATE_GREATER_THAN = 1
COLLATE_EQUAL = 0

DEFAULT_BASE_WEIGHT = 0xFBC0
CJK_URO_BASE_WEIGHT = 0xFB40
CJK_COMPAT_BASE_WEIGHT = 0xFB41
CJK_EXTS_BASE_WEIGHT = 0xFB80
TANGUT_IDS_BASE_WEIGHT = 0xFB00
TANGUT_COMPONENTS_BASE_WEIGHT = 0xFB01
NUSHU_BASE_WEIGHT = 0xFB02
KHITAN_SMALL_SCRIPT_BASE_WEIGHT = 0xFB03
MIN_VARIABLE_WEIGHT_DUCET = 0x0200
MAX_VARIABLE_WEIGHT_DUCET = 0x2191
MIN_VARIABLE_WEIGHT_CLDR = 0x00FF
MAX_VARIABLE_WEIGHT_CLDR = 0x04DF


class SortType(IntEnum):
    UCA = 0
    CLDR = 1


class VariableWeighting(IntEnum):
    NON_IGNORABLE = 0
    BLANKED = 1
    SHIFTED = 2


class Locale(IntEnum):
    NEUTRAL = 0
    OLD_ENGLISH_RUNES = 1
    OLD_ENGLISH_LATIN = 2
    SPANISH = 3
    TIBETAN = 4
    WELSH = 5


# ─── Data structures ─────────────────────────────────────────────────


@dataclass
class CollationEntry:
    """Single collation element range (chFirst..chLast with weights)."""

    ch_first: int = 0
    ch_last: int = 0
    l1: int = 0
    l2: int = 0
    l3: int = 0

    def get_element(self, offset: int = 0) -> tuple[int, int, int]:
        w1 = self.l1 + offset if self.l1 else 0
        return (w1, self.l2, self.l3)


@dataclass
class ContractionEntry:
    """Contraction entry (up to 3 chars → weights)."""

    ch: tuple[int, int, int] = (0, 0, 0)
    l1: int = 0
    l2: int = 0
    l3: int = 0

    def get_element(self) -> tuple[int, int, int]:
        return (self.l1, self.l2, self.l3)


@dataclass
class ContractionBase:
    """Base entry for contraction lookup."""

    ch_start: int = 0
    n_count: int = 0


@dataclass
class SortOptions:
    """Sort configuration options."""

    sort_type: SortType = SortType.UCA
    locale: Locale = Locale.NEUTRAL
    variable_weighting: VariableWeighting = VariableWeighting.NON_IGNORABLE
    ignore_level2: bool = False
    ignore_level3: bool = False
    backwards_level2: bool = False
    upper_before_lower: bool = False
    semi_stable_sort: bool = False
    iteration_marks: bool = False
    max_chars: int = 0
    custom_list: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
#  UCA class
# ═══════════════════════════════════════════════════════════════════════


class UCA:
    """Unicode Collation Algorithm using the bundled DUCET and CLDR tables."""

    _DUCET_TABLE: ClassVar[dict[int, list[tuple[int, int, int]]]] = {}
    _CLDR_TABLE: ClassVar[dict[int, list[tuple[int, int, int]]]] = {}
    _DUCET_CONTRACTIONS: ClassVar[dict[int, dict[tuple[int, int, int], list[tuple[int, int, int]]]]] = {}
    _CLDR_CONTRACTIONS: ClassVar[dict[int, dict[tuple[int, int, int], list[tuple[int, int, int]]]]] = {}
    _LOCALE_CONTRACTIONS: ClassVar[
        dict[Locale, dict[SortType, dict[int, dict[tuple[int, int, int], list[tuple[int, int, int]]]]]]
    ] = {}
    _TIBETAN_TABLE: ClassVar[dict[int, list[tuple[int, int, int]]]] = {}
    _TIBETAN_PUNCTUATION: ClassVar[dict[int, tuple[int, int, int]]] = {}
    _TIBETAN_INITIALS: ClassVar[dict[tuple[int, int, int], list[tuple[int, int, int]]]] = {}

    def __init__(self, sort_options: SortOptions | None = None) -> None:
        self._so = sort_options or SortOptions()
        self._collation_elements: list[tuple[int, ...]] = []
        self._sort_key: list[int] = []
        self._str_nfd: str = ""
        self._collation_levels = 3
        self._blanking = False

        if self._so.variable_weighting == VariableWeighting.SHIFTED:
            self._collation_levels = 4

        self._min_variable = MIN_VARIABLE_WEIGHT_DUCET
        self._max_variable = MAX_VARIABLE_WEIGHT_DUCET

        if self._so.sort_type == SortType.CLDR:
            self._min_variable = MIN_VARIABLE_WEIGHT_CLDR
            self._max_variable = MAX_VARIABLE_WEIGHT_CLDR

        self._init_tables()

    def _init_tables(self) -> None:
        """Expand the reference tables from data/scripts for fast per-codepoint lookup."""
        if UCA._DUCET_TABLE:
            return
        # Imported here: utils_.loader pulls in unicode.core, which imports this module.
        from babelsoft.utils_.loader import ScriptsLoader

        uca = ScriptsLoader.load_uca()
        UCA._DUCET_TABLE = self._expand_collation_table(uca["ducet"])
        UCA._CLDR_TABLE = self._expand_collation_table(uca["cldr"])
        UCA._DUCET_CONTRACTIONS = self._group_contractions(uca["ducet_contraction"])
        UCA._CLDR_CONTRACTIONS = self._group_contractions(uca["cldr_contraction"])
        UCA._LOCALE_CONTRACTIONS = {
            Locale.OLD_ENGLISH_RUNES: {
                sort_type: self._group_contractions(uca["old_english_runes"]) for sort_type in SortType
            },
            Locale.OLD_ENGLISH_LATIN: {
                SortType.UCA: self._group_contractions(uca["old_english_latin_ducet"]),
                SortType.CLDR: self._group_contractions(uca["old_english_latin_cldr"]),
            },
            Locale.SPANISH: {
                SortType.UCA: self._group_contractions(uca["spanish_ducet"]),
                SortType.CLDR: self._group_contractions(uca["spanish_cldr"]),
            },
            Locale.WELSH: {
                SortType.UCA: self._group_contractions(uca["welsh_ducet"]),
                SortType.CLDR: self._group_contractions(uca["welsh_cldr"]),
            },
        }
        UCA._TIBETAN_TABLE = self._expand_collation_table(uca["tibetan_collation"])
        UCA._TIBETAN_PUNCTUATION = {
            cp: (l1, l2, l3)
            for first, last, l1, l2, l3 in uca["tibetan_punctuation"]
            for cp in range(first, last + 1)
        }
        UCA._TIBETAN_INITIALS = {}
        for ch1, ch2, ch3, l1, l2, l3 in uca["tibetan_initial"]:
            UCA._TIBETAN_INITIALS.setdefault((ch1, ch2, ch3), []).append((l1, l2, l3))

    @classmethod
    def _expand_collation_table(cls, rows: Iterable[tuple[int, int, int, int, int]]) -> dict[int, list[tuple[int, int, int]]]:
        table: dict[int, list[tuple[int, int, int]]] = {}
        for first, last, l1, l2, l3 in rows:
            for cp in range(first, last + 1):
                table.setdefault(cp, []).append((l1 + cp - first if l1 else 0, l2, l3))
        return table

    @staticmethod
    def _group_contractions(
        rows: Iterable[tuple[int, int, int, int, int, int]],
    ) -> dict[int, dict[tuple[int, int, int], list[tuple[int, int, int]]]]:
        table: dict[int, dict[tuple[int, int, int], list[tuple[int, int, int]]]] = {}
        for ch1, ch2, ch3, l1, l2, l3 in rows:
            table.setdefault(ch1, {}).setdefault((ch1, ch2, ch3), []).append((l1, l2, l3))
        return table

    # ─── Public API ──────────────────────────────────────────────────

    def set_string(self, source: str) -> None:
        """Set the string to be collated and build its multilevel sort key."""
        for source_text, replacement in self._so.custom_list:
            source = source.replace(source_text, replacement)
        self._str_nfd = Unicode.get_nfd(source)
        if self._so.iteration_marks:
            for index in range(Unicode.get_iteration_mark_count()):
                mark, script = Unicode.get_iteration_mark(index)
                if mark and chr(mark) in self._str_nfd:
                    self._str_nfd = BabelString.substitute_iteration_marks(self._str_nfd, mark, script, True)

        cps = [ord(char) for char in self._str_nfd]
        if self._so.max_chars > 0:
            cps = cps[: self._so.max_chars]
        cccs = [Unicode.get_canonical_combining_class(cp) for cp in cps]

        # Reorder
        self._reorder_split_contractions(cps, [self._get_block(cp) for cp in cps], cccs)

        # Build elements
        self._blanking = False
        elements: list[tuple[int, ...]] = []
        i = 0
        while i < len(cps):
            matched, adv, contraction_elements = self._find_contraction(cps, i)
            if matched:
                elements.extend(self._modify_weights(weights, 0xFFFFFFFF) for weights in contraction_elements)
                i += adv
            else:
                els = self._get_collation_elements(cps[i])
                elements.extend(els)
                i += 1

        self._collation_elements = elements
        self._create_sort_key()

    def compare(self, other: UCA) -> int:
        """Compare this to other. Returns COLLATE_LESS_THAN / EQUAL / GREATER_THAN."""
        sk1, sk2 = self._sort_key, other._sort_key
        n1, n2 = len(sk1), len(sk2)
        for i in range(min(n1, n2)):
            if sk1[i] < sk2[i]:
                return COLLATE_LESS_THAN
            if sk1[i] > sk2[i]:
                return COLLATE_GREATER_THAN
        if n1 < n2:
            return COLLATE_LESS_THAN
        if n1 > n2:
            return COLLATE_GREATER_THAN
        if self._so.semi_stable_sort:
            if self._str_nfd < other._str_nfd:
                return COLLATE_GREATER_THAN
            if self._str_nfd > other._str_nfd:
                return COLLATE_LESS_THAN
        return COLLATE_EQUAL

    def get_sort_key(self) -> str:
        """Return a human-readable sort key string like '[0020 004A 0002]'."""
        parts = ["["]
        for i, w in enumerate(self._sort_key):
            if i > 0:
                parts.append(" ")
            if w == 0:
                parts.append("|")
            else:
                parts.append(f"{w:04X}")
        parts.append("]")
        return "".join(parts)

    def get_sort_key_bytes(self) -> bytes:
        """Return sort key as bytes."""
        return struct.pack(f">{len(self._sort_key)}H", *self._sort_key)

    # ─── Internal: collation element building ────────────────────────

    def _create_sort_key(self) -> None:
        """Build sort key from collation elements."""
        sk: list[int] = []

        for level in range(self._collation_levels):
            if level == 1 and self._so.ignore_level2:
                continue
            if level == 2 and self._so.ignore_level3:
                continue

            weights = self._collation_elements
            if self._so.backwards_level2 and level == 1:
                weights = list(reversed(weights))
            for element in weights:
                w = element[level]
                if w:
                    sk.append(w)
            sk.append(0)  # level separator

        self._sort_key = sk

    def _get_collation_elements(self, cp: int) -> list[tuple[int, ...]]:
        """Get collation elements for a single codepoint."""
        if (
            0x3400 <= cp <= 0x4DBF
            or 0x4E00 <= cp <= 0x9FFF
            or 0x20000 <= cp <= 0x323AF
            or cp in (0xFA0E, 0xFA0F, 0xFA11, 0xFA13, 0xFA14, 0xFA1F, 0xFA21, 0xFA23, 0xFA24, 0xFA27, 0xFA28, 0xFA29)
        ):
            return [self._modify_weights(weights, cp) for weights in self._create_implicit_weights(cp)]
        table = UCA._CLDR_TABLE if self._so.sort_type == SortType.CLDR else UCA._DUCET_TABLE
        if 0x0F00 <= cp <= 0x0FFF and self._so.locale == Locale.TIBETAN:
            rows = UCA._TIBETAN_TABLE.get(cp)
        else:
            rows = table.get(cp)
        if rows is not None:
            return [self._modify_weights(weights, cp) for weights in rows]
        return [self._modify_weights(weights, cp) for weights in self._create_implicit_weights(cp)]

    def _create_implicit_weights(self, cp: int) -> list[tuple[int, int, int]]:
        """Create the UCA implicit weights for CJK and unlisted codepoints."""
        base = DEFAULT_BASE_WEIGHT
        if 0x4E00 <= cp <= 0x9FFF:  # CJK URO
            base = CJK_URO_BASE_WEIGHT
        elif 0x3400 <= cp <= 0x4DBF or cp >= 0x20000:
            base = CJK_EXTS_BASE_WEIGHT
        if 0x18800 <= cp <= 0x18AFF:
            base = TANGUT_COMPONENTS_BASE_WEIGHT
        elif 0x17000 <= cp <= 0x187FF:
            base = TANGUT_IDS_BASE_WEIGHT
        elif 0x1B170 <= cp <= 0x1B2FF:
            base = NUSHU_BASE_WEIGHT
        elif 0x18B00 <= cp <= 0x18CFF:
            base = KHITAN_SMALL_SCRIPT_BASE_WEIGHT

        if base in (TANGUT_IDS_BASE_WEIGHT, TANGUT_COMPONENTS_BASE_WEIGHT, NUSHU_BASE_WEIGHT, KHITAN_SMALL_SCRIPT_BASE_WEIGHT):
            first = base
            if base == TANGUT_IDS_BASE_WEIGHT:
                second = (cp - 0x17000) | 0x8000
            elif base == TANGUT_COMPONENTS_BASE_WEIGHT:
                second = (cp - 0x18800) | 0x8000
            elif base == NUSHU_BASE_WEIGHT:
                second = (cp - 0x1B170) | 0x8000
            else:
                second = (cp - 0x18B00) | 0x8000
        else:
            first = base + (cp >> 15)
            second = (cp & 0x7FFF) | 0x8000
        return [(first, 0x0020, 0x0002), (second, 0, 0)]

    def _find_contraction(self, cps: list[int], pos: int) -> tuple[bool, int, list[tuple[int, int, int]]]:
        """Return whether a contraction matched, consumed characters, and its weights."""
        cp = cps[pos]
        if self._so.locale == Locale.TIBETAN:
            result = self._process_tibetan(cps, pos)
            if result is not None:
                return True, result[0], result[1]

        locale = UCA._LOCALE_CONTRACTIONS.get(self._so.locale, {}).get(self._so.sort_type)
        candidates = [locale] if locale else []
        candidates.append(UCA._CLDR_CONTRACTIONS if self._so.sort_type == SortType.CLDR else UCA._DUCET_CONTRACTIONS)
        for table in candidates:
            if table is None:
                continue
            by_sequence = table.get(cp)
            if not by_sequence:
                continue
            matches = []
            for sequence, weights in by_sequence.items():
                length = 1 + (sequence[1] != 0) + (sequence[2] != 0)
                if cps[pos : pos + length] == list(sequence[:length]):
                    matches.append((length, weights))
            if matches:
                length, weights = max(matches, key=lambda match: match[0])
                return True, length, weights
        return False, 0, []

    def _process_tibetan(self, cps: list[int], pos: int) -> tuple[int, list[tuple[int, int, int]]] | None:
        cp = cps[pos]
        if 0x0F0B <= cp <= 0x0F11 or cp == 0x0F14 or 0x0F00 <= cp <= 0x0F34:
            if cp in UCA._TIBETAN_PUNCTUATION:
                return 1, [UCA._TIBETAN_PUNCTUATION[cp]]
            return None

        starter = cp == 0x0F00 or 0x0F40 <= cp <= 0x0F47 or 0x0F49 <= cp <= 0x0F6C or 0x0F88 <= cp <= 0x0F8C
        nonstarter = (
            0x0F71 < cp < 0x0F7F
            or 0x0F7F < cp < 0x0F84
            or 0x0F8D <= cp < 0x0F98
            or 0x0F98 < cp < 0x0FBD
        )
        if nonstarter:
            initial = UCA._TIBETAN_INITIALS.get((0, 0, 0))
            return (1, initial) if initial else None
        if not starter:
            return None

        lookahead = cps[pos : pos + 3]
        best: tuple[int, tuple[int, int, int]] | None = None
        for length in range(min(3, len(lookahead)), 0, -1):
            sequence = tuple(lookahead[:length]) + (0,) * (3 - length)
            if sequence in UCA._TIBETAN_INITIALS:
                best = length, sequence
                break
        if best is None:
            return None
        length, sequence = best
        remaining = pos + length
        while remaining < len(cps) and cps[remaining] in UCA._TIBETAN_TABLE:
            remaining += 1
        weights = list(UCA._TIBETAN_INITIALS[sequence])
        for codepoint in cps[pos + length : remaining]:
            weights.extend(UCA._TIBETAN_TABLE[codepoint])
        return remaining - pos, weights

    def _modify_weights(self, source_weights: tuple[int, int, int], cp: int) -> tuple[int, ...]:
        """Apply UCA variable weighting and case/decomposition options."""
        l1, l2, l3 = source_weights
        l4 = 0
        weights = [l1, l2, l3]
        if l1 == 0 and l2 == 0:
            return (*weights, l4) if self._collation_levels == 4 else tuple(weights)

        if cp != 0xFFFFFFFF:
            decomp = Unicode.get_decomposition_type(cp)
            if decomp.name not in ("None_", "Canon"):
                l3 = self._modify_tertiary(l3, decomp.name, cp)
                weights[2] = l3
        if self._so.upper_before_lower:
            if l3 in (2, 3, 5, 6):
                l3 += 6
            elif l3 == 0x1C:
                l3 += 1
            elif l3 in (8, 9, 10, 11, 12):
                l3 -= 6
            elif l3 == 0x1D:
                l3 -= 1
            weights[2] = l3

        if self._so.variable_weighting in (VariableWeighting.BLANKED, VariableWeighting.SHIFTED):
            if self._min_variable < l1 <= self._max_variable:
                l4 = l1
                weights = [0, 0, 0]
                self._blanking = True
            elif l1 == 0:
                if self._blanking:
                    weights = [0, 0, 0]
                elif l2 or l3:
                    l4 = 0xFFFF
            else:
                self._blanking = False
                l4 = l1 if self._so.sort_type == SortType.CLDR and cp == 0xFFFE else 0xFFFF
            if self._collation_levels == 4:
                weights.append(l4)
        elif self._collation_levels == 4:
            weights.append(0)
        return tuple(weights)

    @staticmethod
    def _modify_tertiary(weight: int, decomposition_type: str, cp: int) -> int:
        adjustments = {
            "Font": 3,
            "NoBreak": 0x1B,
            "Initial": 0x17,
            "Medial": 0x18,
            "Final": 0x19,
            "Isolated": 0x1A,
            "Vertical": 0x16,
            "Small": 0x0F,
            "Fraction": 0x1E,
        }
        if decomposition_type in adjustments:
            return weight + adjustments[decomposition_type] if decomposition_type == "Font" else adjustments[decomposition_type]
        if decomposition_type == "Circle":
            return 0x13 if 0x30A2 <= cp <= 0x30F2 else weight + 4
        if decomposition_type == "Wide":
            return weight + 1
        if decomposition_type == "Narrow":
            return weight + 1 if weight in (0x0F, 0x11) else 0x12
        if decomposition_type == "Super" or decomposition_type == "Sub":
            return 0x1D if weight == 8 else (0x14 if decomposition_type == "Super" else 0x15)
        if decomposition_type == "Square":
            return 0x1D if weight == 8 else 0x1C
        if decomposition_type == "Compat":
            return (2 if weight == 0x19 else weight) + 2
        return weight

    def _reorder_split_contractions(self, cps: list[int], blocks: list[int], cccs: list[int]) -> None:
        """Reorder combining marks for proper contraction matching."""
        n = len(cps)
        start = -1
        end = -1

        for i in range(n):
            if cccs[i] == 0:
                if start != end and start >= 0:
                    self._reorder_range(cps, blocks, cccs, start, end)
                start = i
                end = i
            else:
                if start >= 0:
                    end = i

        if start != end and start >= 0:
            self._reorder_range(cps, blocks, cccs, start, end)

    def _reorder_range(
        self,
        cps: list[int],
        blocks: list[int],
        cccs: list[int],
        start: int,
        end: int,
    ) -> None:
        """Reorder a range by CCC values (stable sort)."""
        if end <= start + 1:
            return
        # Simple insertion sort by CCC (stable)
        for i in range(start + 1, end + 1):
            key_cp = cps[i]
            key_block = blocks[i]
            key_ccc = cccs[i]
            j = i - 1
            while j >= start and cccs[j] > key_ccc:
                cps[j + 1] = cps[j]
                blocks[j + 1] = blocks[j]
                cccs[j + 1] = cccs[j]
                j -= 1
            cps[j + 1] = key_cp
            blocks[j + 1] = key_block
            cccs[j + 1] = key_ccc

    @staticmethod
    def _get_block(cp: int) -> int:
        """Get a simplified block number for a codepoint."""
        if cp < 0x10000:
            return cp >> 8
        return 0x100 + (cp >> 8)


# ─── Convenience functions ────────────────────────────────────────────


def collation_sort_key(text: str, options: SortOptions | None = None) -> bytes:
    """Return a binary sort key for the given text."""
    uca = UCA(options)
    uca.set_string(text)
    return uca.get_sort_key_bytes()


def collation_compare(a: str, b: str, options: SortOptions | None = None) -> int:
    """Compare two strings using UCA."""
    uca_a = UCA(options)
    uca_b = UCA(options)
    uca_a.set_string(a)
    uca_b.set_string(b)
    return uca_a.compare(uca_b)
