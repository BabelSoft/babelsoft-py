"""
Tangut script data — Python implementation of c/Scripts/

Combines all five Tangut dictionary/phonetic sources:
    LiFanwen 2008, Kychanov 2006, Sofronov 1968, Nishida 1966,
    Miyake 2012/2015

Also provides the Tangut orchestration class with:
- Character identification
- Delegate accessors to all source dictionaries
- Merged source data, radical/stroke, IDS, variants
- Component data lookups
"""

from __future__ import annotations

from src.utils_.loader import ScriptsLoader

# ─── Unicode block ranges ──────────────────────────────────────────────

TANGUT_START = 0x17000
TANGUT_LAST = 0x187FF
TANGUT_COUNT = TANGUT_LAST - TANGUT_START + 1  # 6144

TANGUT_COMPS_START = 0x18800
TANGUT_COMPS_LAST = 0x18AFF
TANGUT_COMPS_COUNT = 768

TANGUT_SUPP_START = 0x18D00
TANGUT_SUPP_LAST = 0x18D7F
TANGUT_SUPP_COUNT = 76

# ─── Helper: range-checked offset ──────────────────────────────────────


def _offset(ch: int) -> int | None:
    if TANGUT_START <= ch <= TANGUT_LAST:
        return ch - TANGUT_START
    return None


def _get(data: list[dict], offset: int | None) -> dict | None:
    if offset is None or offset >= len(data):
        return None
    return data[offset] or None


# ═══════════════════════════════════════════════════════════════════════
#  Li Fanwen 2008
# ═══════════════════════════════════════════════════════════════════════


class LiFanwen:
    """Li Fanwen 2008 Tangut dictionary."""

    @staticmethod
    def has_entry(ch: int) -> bool:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_li_fanwen()
        if off is None or off >= len(data):
            return False
        return data[off].get("number", 0) != 0

    @staticmethod
    def get_number(ch: int, b1997: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_li_fanwen()
        entry = _get(data, off)
        if not entry or entry.get("number", 0) == 0:
            return ""
        num = entry["number"]
        var = entry["variant"]
        result = f"L2008-{num:04d}"
        if var == 1:
            result += "A"
        elif var == 2:
            result += "B"
        return result

    @staticmethod
    def get_reading(ch: int, b_tone: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_li_fanwen()
        entry = _get(data, off)
        if not entry:
            return ""
        reading = entry.get("reading", "")
        if b_tone and reading:
            tone = entry.get("tone", 0)
            if tone:
                reading += f" [{tone}]"
        return reading

    @staticmethod
    def get_meaning(ch: int, b_escape: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_li_fanwen()
        entry = _get(data, off)
        return entry.get("english", "") if entry else ""

    @staticmethod
    def get_tone_rime(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_li_fanwen()
        entry = _get(data, off)
        if not entry:
            return ""
        tone = entry.get("tone", 0)
        rime = entry.get("rime", 0)
        return f"{tone}.{rime:02d}" if tone or rime else ""

    @staticmethod
    def find_reference(ref: str, b1997: bool = False) -> int:
        data = ScriptsLoader.load_tangut_li_fanwen()
        for off, entry in enumerate(data):
            if not entry or entry.get("number", 0) == 0:
                continue
            if ref == f"L2008-{entry['number']:04d}":
                return TANGUT_START + off
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Kychanov 2006
# ═══════════════════════════════════════════════════════════════════════


class Kychanov:
    """Kychanov 2006 Tangut dictionary."""

    @staticmethod
    def has_entry(ch: int) -> bool:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_kychanov()
        if off is None or off >= len(data):
            return False
        return data[off].get("number", 0) != 0

    @staticmethod
    def get_number(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_kychanov()
        entry = _get(data, off)
        if not entry or entry.get("number", 0) == 0:
            return ""
        return f"K{entry['number']:04d}"

    @staticmethod
    def get_reading(ch: int, b_tone: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_kychanov()
        entry = _get(data, off)
        if not entry:
            return ""
        reading = entry.get("reading", "")
        if b_tone and reading:
            tone = entry.get("tone", 0)
            if tone:
                reading += f" [{tone}]"
        return reading

    @staticmethod
    def get_tone_rime(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_kychanov()
        entry = _get(data, off)
        if not entry:
            return ""
        tone = entry.get("tone", 0)
        rime = entry.get("rime", 0)
        return f"{tone}.{rime:02d}" if tone or rime else ""

    @staticmethod
    def find_reference(ref: str) -> int:
        data = ScriptsLoader.load_tangut_kychanov()
        for off, entry in enumerate(data):
            if not entry or entry.get("number", 0) == 0:
                continue
            if ref == f"K{entry['number']:04d}":
                return TANGUT_START + off
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Sofronov 1968
# ═══════════════════════════════════════════════════════════════════════


class Sofronov:
    """Sofronov 1968 Tangut dictionary."""

    @staticmethod
    def has_entry(ch: int) -> bool:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_sofronov()
        if off is None or off >= len(data):
            return False
        return data[off].get("number", 0) != 0

    @staticmethod
    def get_number(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_sofronov()
        entry = _get(data, off)
        if not entry or entry.get("number", 0) == 0:
            return ""
        return f"S{entry['number']:04d}"

    @staticmethod
    def get_reading(ch: int, b_tone: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_sofronov()
        entry = _get(data, off)
        if not entry:
            return ""
        reading = entry.get("reading", "")
        if b_tone and reading:
            tone = entry.get("tone", 0)
            if tone:
                reading += f" [{tone}]"
        return reading

    @staticmethod
    def get_tone_rime(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_sofronov()
        entry = _get(data, off)
        if not entry:
            return ""
        tone = entry.get("tone", 0)
        rime = entry.get("rime", 0)
        return f"{tone}.{rime:02d}" if tone or rime else ""

    @staticmethod
    def find_reference(ref: str) -> int:
        data = ScriptsLoader.load_tangut_sofronov()
        for off, entry in enumerate(data):
            if not entry or entry.get("number", 0) == 0:
                continue
            if ref == f"S{entry['number']:04d}":
                return TANGUT_START + off
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Nishida 1966
# ═══════════════════════════════════════════════════════════════════════


class Nishida:
    """Nishida 1966 Tangut dictionary."""

    @staticmethod
    def has_entry(ch: int) -> bool:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_nishida()
        if off is None or off >= len(data):
            return False
        entry = data[off]
        return bool(entry.get("reference1") or entry.get("reading"))

    @staticmethod
    def get_reference(ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_nishida()
        entry = _get(data, off)
        if not entry:
            return ""
        r1, r2 = entry.get("reference1", ""), entry.get("reference2", "")
        return f"{r1}, {r2}" if r1 and r2 else (r1 or r2)

    @staticmethod
    def get_reading(ch: int, b_tone: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_nishida()
        entry = _get(data, off)
        return entry.get("reading", "") if entry else ""

    @staticmethod
    def find_reference(ref: str) -> int:
        data = ScriptsLoader.load_tangut_nishida()
        for off, entry in enumerate(data):
            if not entry:
                continue
            r1, r2 = entry.get("reference1", ""), entry.get("reference2", "")
            if ref in (r1, r2) or ref == f"{r1}, {r2}":
                return TANGUT_START + off
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  Miyake 2012 / 2015
# ═══════════════════════════════════════════════════════════════════════


class Miyake:
    """Miyake Tangut phonetic reconstruction (2012 & 2015)."""

    def __init__(self, use_2012: bool = False) -> None:
        self._use_2012 = use_2012

    @property
    def _version(self) -> str:
        return "2012" if self._use_2012 else "2015"

    def _lookup(self, index: int, table_key: str) -> str:
        tables = ScriptsLoader.load_miyake_phonetic_tables()
        tbl = tables[table_key]
        version_tbl = tbl[self._version] if isinstance(tbl, dict) else tbl
        if 0 <= index < len(version_tbl):
            return version_tbl[index]
        return ""

    def has_entry(self, ch: int) -> bool:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        if off is None or off >= len(data):
            return False
        entry = data[off]
        return entry.get("initial", 0) != 0 or entry.get("final", 0) != 0

    def get_reading(self, ch: int, b_tone: bool = False) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        if not entry:
            return ""
        i, m, f = entry.get("initial", 0), entry.get("medial", 0), entry.get("final", 0)
        if i == 0 and f == 0:
            return ""
        reading = self._lookup(i, "initials") + self._lookup(m, "medials") + self._lookup(f, "finals")
        if b_tone and reading:
            tone = entry.get("tone", 0)
            if tone:
                reading += str(tone)
        return reading

    def get_initial(self, ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        return self._lookup(entry.get("initial", 0), "initials") if entry else ""

    def get_rime(self, ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        if not entry:
            return ""
        return self._lookup(entry.get("medial", 0), "medials") + self._lookup(entry.get("final", 0), "finals")

    def get_tone(self, ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        return str(entry.get("tone", 0)) if entry and entry.get("tone") else ""

    def get_tone_rime(self, ch: int) -> str:
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        if not entry:
            return ""
        tone, rime = entry.get("tone", 0), entry.get("rime", 0)
        return f"{tone}.{rime:02d}" if tone or rime else ""

    def get_syllable(self, ch: int) -> str:
        """Get the initial-medial-final-tone string (e.g. '9-0-61-1')."""
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        if not entry:
            return ""
        return f"{entry.get('initial', 0)}-{entry.get('medial', 0)}-{entry.get('final', 0)}-{entry.get('tone', 0)}"

    def get_imf(self, ch: int) -> str:
        """Get the initial-medial-final index string (e.g. '9-0-61')."""
        off = _offset(ch)
        data = ScriptsLoader.load_tangut_miyake()
        entry = _get(data, off)
        if not entry:
            return ""
        return f"{entry.get('initial', 0)}-{entry.get('medial', 0)}-{entry.get('final', 0)}"


# ═══════════════════════════════════════════════════════════════════════
#  Tangut — orchestration and merged data
# ═══════════════════════════════════════════════════════════════════════


class Tangut:
    """Tangut script orchestration and merged data lookups."""

    _miyake_2015 = Miyake(use_2012=False)
    _miyake_2012 = Miyake(use_2012=True)

    # ─── Character identification ───────────────────────────────────

    @staticmethod
    def is_tangut_ideograph(ch: int) -> bool:
        return TANGUT_START <= ch <= TANGUT_LAST or TANGUT_SUPP_START <= ch <= TANGUT_SUPP_LAST

    # ─── Source accessors ───────────────────────────────────────────

    @staticmethod
    def get_li_fanwen_number(ch: int) -> str:
        return LiFanwen.get_number(ch, False)

    @staticmethod
    def get_li_fanwen_1997_number(ch: int) -> str:
        return LiFanwen.get_number(ch, True)

    @staticmethod
    def get_li_fanwen_reading(ch: int, b_tone: bool = False) -> str:
        return LiFanwen.get_reading(ch, b_tone)

    @staticmethod
    def get_li_fanwen_meaning(ch: int) -> str:
        return LiFanwen.get_meaning(ch)

    @staticmethod
    def get_kychanov_number(ch: int) -> str:
        return Kychanov.get_number(ch)

    @staticmethod
    def get_kychanov_reading(ch: int, b_tone: bool = False) -> str:
        return Kychanov.get_reading(ch, b_tone)

    @staticmethod
    def get_sofronov_number(ch: int) -> str:
        return Sofronov.get_number(ch)

    @staticmethod
    def get_sofronov_reading(ch: int, b_tone: bool = False) -> str:
        return Sofronov.get_reading(ch, b_tone)

    @staticmethod
    def get_nishida_reference(ch: int) -> str:
        return Nishida.get_reference(ch)

    @staticmethod
    def get_nishida_reading(ch: int, b_tone: bool = False) -> str:
        return Nishida.get_reading(ch, b_tone)

    @staticmethod
    def get_miyake_reading(ch: int, b_2012: bool = False, b_tone: bool = False) -> str:
        m = Tangut._miyake_2012 if b_2012 else Tangut._miyake_2015
        return m.get_reading(ch, b_tone)

    # ─── Merged data accessors ──────────────────────────────────────

    @staticmethod
    def get_merged_source(ch: int) -> str:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return ""
        e = data[off]
        return e.get("merged_source", "") if e else ""

    @staticmethod
    def get_radical_stroke(ch: int) -> str:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return ""
        e = data[off]
        if not e:
            return ""
        r, s = e.get("radical", 0), e.get("stroke_count", 0)
        return f"{r}.{s}" if r else ""

    @staticmethod
    def get_radical_number(ch: int) -> int:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return 0
        e = data[off]
        return e.get("radical", 0) if e else 0

    @staticmethod
    def get_total_stroke_count(ch: int) -> int:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return 0
        e = data[off]
        return e.get("stroke_count", 0) if e else 0

    @staticmethod
    def get_additional_stroke_count(ch: int) -> int:
        total = Tangut.get_total_stroke_count(ch)
        rn = Tangut.get_radical_number(ch)
        comps = ScriptsLoader.load_tangut_component_data()
        if rn and rn <= len(comps):
            c = comps[rn - 1]
            return max(0, total - c.get("stroke_count", 0)) if c else total
        return total

    @staticmethod
    def get_ids(ch: int) -> str:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return ""
        e = data[off]
        return e.get("ids", "") if e else ""

    @staticmethod
    def has_variants(ch: int) -> bool:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return False
        e = data[off]
        return (e.get("variant1", 0) != 0 or e.get("variant2", 0) != 0) if e else False

    @staticmethod
    def get_variants(ch: int) -> str:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return ""
        e = data[off]
        if not e:
            return ""
        parts = []
        if e.get("variant1"):
            parts.append(chr(e["variant1"]))
        if e.get("variant2"):
            parts.append(chr(e["variant2"]))
        return " ".join(parts)

    @staticmethod
    def get_variant(ch: int, n_var: int) -> int:
        off = Tangut._get_offset(ch)
        data = ScriptsLoader.load_tangut_character_data()
        if off < 0 or off >= len(data):
            return 0
        e = data[off]
        return e.get(f"variant{n_var + 1}", 0) if e else 0

    # ─── Component data ────────────────────────────────────────────

    @staticmethod
    def get_stroke_count_for_component(ch: int) -> int:
        if not (TANGUT_COMPS_START <= ch <= TANGUT_COMPS_LAST):
            return 0
        off = ch - TANGUT_COMPS_START
        data = ScriptsLoader.load_tangut_component_data()
        if off >= len(data):
            return 0
        e = data[off]
        return e.get("stroke_count", 0) if e else 0

    @staticmethod
    def get_stroke_count_for_component_number(number: int) -> int:
        data = ScriptsLoader.load_tangut_component_data()
        if 1 <= number <= len(data):
            e = data[number - 1]
            return e.get("stroke_count", 0) if e else 0
        return 0

    @staticmethod
    def get_radical_for_character(ch: int) -> int:
        rn = Tangut.get_radical_number(ch)
        if rn and 1 <= rn <= len(ScriptsLoader.load_tangut_component_data()):
            return TANGUT_COMPS_START + rn - 1
        return 0

    # ─── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _get_offset(ch: int) -> int:
        if TANGUT_START <= ch <= TANGUT_LAST:
            return ch - TANGUT_START
        if TANGUT_SUPP_START <= ch <= TANGUT_SUPP_LAST:
            return (ch - TANGUT_SUPP_START) + (TANGUT_LAST - TANGUT_START + 1)
        return -1
