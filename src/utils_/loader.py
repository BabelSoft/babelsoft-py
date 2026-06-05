from __future__ import annotations

import functools
import re
from pathlib import Path

from src.unicode.class_ import Block, CodePoint
from src.utils_.dirs import Dirs
from src.utils_.parser import TsvParser, TxtParser, line_has_content


def _parse_rs_unihan(text: str) -> tuple[int, int, int]:
    """Parse Unihan RS string like "212'''.6" -> (212, 3, 6)."""
    radical_part, sep, stroke = text.partition(".")
    stroke = int(stroke) if sep else 0
    variant = len(radical_part) - len(radical_part.rstrip("'"))
    radical = int(radical_part.rstrip("'")) if variant else int(radical_part)
    return radical, variant, stroke


class CJKLoader:
    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_ucd_Blocks() -> list[Block]:
        lines = filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "Blocks.txt"))
        matches = TxtParser.match(lines, re.compile(r"([\da-fA-F]+)\.\.([\da-fA-F]+); (.+)"))
        return [Block(int(s, 16), int(e, 16), name.strip()) for s, e, name in matches]

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_charts_RSIndex() -> dict[tuple, list[int]]:
        sep = re.compile(r"(\|+)\s*")
        result = {}

        for line in filter(line_has_content, TxtParser.get_txt(Dirs.CHARTS / "RSIndex.txt")):
            line = line.split("#", 1)[0].rstrip()
            rs_part, data_part = line.split("\t", 1)
            rad, base_var, base_stroke = _parse_rs_unihan(rs_part)
            parts = sep.split(data_part, maxsplit=1)
            key = (rad, base_var, base_stroke)
            result[key] = [int(val[2:], 16) if val.startswith("U+") else int(val) for val in parts[0].split() if val]

            for i, match in enumerate(sep.finditer(data_part)):
                var = len(match.group(1))
                end = (
                    sep.search(data_part, match.end()).start()
                    if i + 1 < len(sep.findall(data_part))
                    else len(data_part)
                )
                val = data_part[match.end() : end].strip()
                if val:
                    key = (rad, var, base_stroke)
                    result[key] = [int(v[2:], 16) if v.startswith("U+") else int(v) for v in val.split()]
        return result

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_ucd_CJKRadicals() -> dict[tuple[int, int], tuple[int, int]]:
        # key=(rad, var), value=(char_cp, char_normalized_cp)
        lines = filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "CJKRadicals.txt"))
        res: dict[tuple[int, int], tuple[int, int]] = {}

        for line in lines:
            m = re.match(r"([\da-fA-F]+); ([\da-fA-F]+); ([\da-fA-F]+)", line)
            if not m:
                continue
            rs_str, cp1, cp2 = m.groups()
            rad, var, _ = _parse_rs_unihan(rs_str)
            res[(rad, var)] = (int(cp1, 16), int(cp2, 16))
        return res

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_flags() -> dict[int, int]:
        """Compute CJK character flags from derived data files.

        Flags are derived from:
          - IVD_Sequences.txt        → IVS (any character appearing as a base)
          - cjk_mappings.tsv         → Fanti / Jianti / FantiJianti (via direction column)
          - cjk_xinjiu_mapping.tsv   → Xinzixing / Jiuzixing
          - cjk_shinjitai_mapping.tsv → Shinjitai / Kyujitai
          - cjk_readings.tsv         → Pinyin / Jyutping / YaleKorean / QuocNgu / Zhuang
          - codepoint range          → SIP (>= 0x20000) / TIP (>= 0x30000)
        """
        flags: dict[int, int] = {}

        # ── IVS from IVD_Sequences.txt ──
        for row in CJKLoader.load_ivd_sequences():
            flags[row[0]] = flags.get(row[0], 0) | 0x0001

        # ── Fanti / Jianti / FantiJianti from mappings direction ──
        DIR_MAP = {"fanti": 0x0002, "jianti": 0x0004, "fanti_jianti": 0x0008}
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_mappings.tsv"):
            if len(row) >= 5:
                cp = int(row[0][2:], 16)
                direction = row[4].strip()
                if direction in DIR_MAP:
                    flags[cp] = flags.get(cp, 0) | DIR_MAP[direction]

        # ── Xinzixing / Jiuzixing ──
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_xinjiu_mapping.tsv"):
            if len(row) >= 2:
                src = int(row[0][2:], 16)
                tgt = int(row[1][2:], 16)
                flags[src] = flags.get(src, 0) | 0x0010  # XINZIXING
                flags[tgt] = flags.get(tgt, 0) | 0x0020  # JIUZIXING

        # ── Shinjitai / Kyujitai ──
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_shinjitai_mapping.tsv"):
            if len(row) >= 2:
                src = int(row[0][2:], 16)
                tgt = int(row[1][2:], 16)
                flags[src] = flags.get(src, 0) | 0x0040  # SHINJITAI
                flags[tgt] = flags.get(tgt, 0) | 0x0080  # KYUJITAI

        # ── Pinyin / Jyutping / YaleKorean / QuocNgu / Zhuang from readings ──
        FIELD_FLAGS = {
            "kMandarin": 0x0100,
            "kCantonese": 0x0200,
            "kKorean": 0x0400,
            "kVietnamese": 0x0800,
            "kZhuang": 0x1000,
        }
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_readings.tsv"):
            if len(row) >= 2:
                cp = int(row[0][2:], 16)
                field = row[1]
                if field in FIELD_FLAGS:
                    flags[cp] = flags.get(cp, 0) | FIELD_FLAGS[field]

        # ── SIP / TIP by range ──
        for cp in list(flags.keys()):
            if cp >= 0x30000:
                flags[cp] |= 0x4000  # TIP
            elif cp >= 0x20000:
                flags[cp] |= 0x2000  # SIP

        return flags

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_mappings() -> dict[int, tuple[int, str]]:
        """Load cjk_mappings.tsv → {source_cp: (target_cp, direction)}.
        Direction is one of: fanti, jianti, fanti_jianti.
        """
        result: dict[int, tuple[int, str]] = {}
        for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_mappings.tsv"):
            if len(row) >= 5:
                src = int(row[0][2:], 16)
                tgt = int(row[2][2:], 16)
                direction = row[4].strip()
                if direction in ("fanti", "jianti", "fanti_jianti"):
                    result[src] = (tgt, direction)
        return result

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_ivd_sequences() -> list[tuple[int, int, str, str]]:
        """Load IVD_Sequences.txt → [(base_cp, vs_cp, collection, reference), ...].

        Format: base_cp vs_cp; collection; reference
        e.g. "3402 E0100; Adobe-Japan1; CID+13698"
        """
        result: list[tuple[int, int, str, str]] = []
        for line in TxtParser.get_txt(Dirs.IVD / "IVD_Sequences.txt"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(";", 2)
            if len(parts) < 3:
                continue
            seq_parts = parts[0].strip().split()
            if len(seq_parts) != 2:
                continue
            base = int(seq_parts[0], 16)
            vs = int(seq_parts[1], 16)
            collection = parts[1].strip()
            ref = parts[2].strip()
            result.append((base, vs, collection, ref))
        return result

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_ivs_chars() -> set[int]:
        """Load set of all base codepoints that have IVS sequences."""
        return {base for base, vs, collection, ref in CJKLoader.load_ivd_sequences()}

    @staticmethod
    def get_ideographic_variant(base_cp: int, vs_cp: int, start_index: int = 0):
        """Look up IVS: given base character + variation selector, return
        (collection, reference, next_index) or None if not found.
        Corresponds to Unicode::GetIdeographicVariant in C++.
        """
        UNICODE_IVS_MIN = 0xE0100
        if vs_cp < UNICODE_IVS_MIN:
            return None
        vs_offset = vs_cp - UNICODE_IVS_MIN
        base16 = base_cp & 0xFFFF
        for i, (base, vs, collection, ref) in enumerate(CJKLoader.load_ivd_sequences()):
            if i < start_index:
                continue
            if (base & 0xFFFF) == base16 and (vs - UNICODE_IVS_MIN) == vs_offset:
                return (collection, ref, i + 1)
        return None

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _load_tsv_pair_map(path: Path) -> tuple[dict[int, int], dict[int, int]]:
        a2b, b2a = {}, {}
        for row in TsvParser.get_tsv(path):
            if len(row) >= 2:
                a = int(row[0][2:], 16)
                b = int(row[1][2:], 16)
                a2b[a], b2a[b] = b, a
        return a2b, b2a

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_shinjitai_maps():
        return CJKLoader._load_tsv_pair_map(Dirs.BABELSOFT / "cjk_shinjitai_mapping.tsv")

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_xinjiu_maps():
        return CJKLoader._load_tsv_pair_map(Dirs.BABELSOFT / "cjk_xinjiu_mapping.tsv")

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_cjk_irg_sources() -> dict[int, tuple[list[str], str]]:
        raw = CJKLoader.load_unihan_IRGSources()
        result: dict[int, tuple[list[str], str]] = {}
        for cp, fields in raw.items():
            parts: list[tuple[str, str]] = []
            for field, values in fields.items():
                if field.startswith("kIRG_") and field.endswith("Source"):
                    code = field.removeprefix("kIRG_").removesuffix("Source")
                    parts.extend((code, v) for v in values)
            result[int(cp)] = ([p[0] for p in parts], ", ".join(p[1] for p in parts))
        return result

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_cjk_irg_reverse() -> dict[str, int]:
        result: dict[str, int] = {}
        for cp, fields in CJKLoader.load_unihan_IRGSources().items():
            for field, values in fields.items():
                if field.startswith("kIRG_") and field.endswith("Source"):
                    for v in values:
                        result[v] = int(cp)
        return result

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_radical_mappings() -> list[tuple[int, int, int]]:
        data = CJKLoader.load_ucd_CJKRadicals()
        res = []
        for (rad, var), (cp, _) in sorted(data.items(), key=lambda x: (x[0][0], x[0][1])):
            res.append((cp, rad, var))
        return res

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_radical_data() -> dict[tuple[int, int], list[tuple[int, int]]]:
        res: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for cp, fields in CJKLoader.load_unihan_IRGSources().items():
            for d in fields.get("kRSUnicode", []):
                for t in d.split():
                    rad, var, stroke = _parse_rs_unihan(t)
                    res.setdefault((rad, var), []).append((stroke, int(cp)))
        for k in res:
            res[k].sort()
        return res

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_radical_equivs() -> dict[int, int]:
        return {int(k): int(v) for k, v in CJKLoader.load_ucd_EquivalentUnifiedIdeograph().items()}

    @staticmethod
    def _parse_adjustments(path: Path) -> dict[int, list[tuple[int, int, int]]]:
        def p(s):
            if "any" in s:
                return 0xFFFF
            match = re.search(r"U\+([0-9A-Fa-f]+)", s)
            return int(match.group(1), 16) if match else 0

        return {p(row[1]): [(p(row[0]), p(row[2]), p(row[3]))] for row in TsvParser.get_tsv(path) if len(row) >= 4}

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_simp_adjustments():
        return CJKLoader._parse_adjustments(Dirs.BABELSOFT / "cjk_simp_adjustments.tsv")

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_trad_adjustments():
        return CJKLoader._parse_adjustments(Dirs.BABELSOFT / "cjk_trad_adjustments.tsv")

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_unihan_IRGSources() -> dict[CodePoint, dict[str, list[str]]]:
        res: dict[CodePoint, dict[str, list[str]]] = {}
        for line in TxtParser.get_txt(Dirs.UNIHAN / "Unihan_IRGSources.txt"):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.strip().split("\t", 2)
            if len(parts) < 3:
                continue
            cp = CodePoint.from_(parts[0])
            if not cp:
                continue
            res.setdefault(cp, {}).setdefault(parts[1], []).append(parts[2])
        return res

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_unihan_Readings() -> dict[int, dict[str, str]]:
        """Load Unihan_Readings.txt -> {codepoint: {kMandarin, kCantonese, kKorean, kVietnamese, kZhuang, ...}}."""
        READING_FIELDS = {"kMandarin", "kCantonese", "kKorean", "kVietnamese", "kZhuang"}
        res: dict[int, dict[str, str]] = {}
        for line in TxtParser.get_txt(Dirs.UNIHAN / "Unihan_Readings.txt"):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.strip().split("\t", 2)
            if len(parts) < 3 or parts[1] not in READING_FIELDS:
                continue
            cp = CodePoint.from_(parts[0])
            if cp is not None:
                res.setdefault(int(cp), {})[parts[1]] = parts[2]
        return res

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_ucd_EquivalentUnifiedIdeograph() -> dict[CodePoint, CodePoint]:
        res = {}
        for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "EquivalentUnifiedIdeograph.txt")):
            m = re.match(r"^\s*([0-9A-Fa-f]+)(?:\.\.([0-9A-Fa-f]+))?\s*;\s*([0-9A-Fa-f]+)", line)
            if not m:
                continue
            s, e, t = m.groups()
            s, t = CodePoint.from_(s), CodePoint.from_(t)
            e = CodePoint.from_(e) if e else s
            for cp in range(s, e + 1):
                res[cp] = t
        return res


# ─── Scripts Loader ────────────────────────────────────────────────────


class ScriptsLoader:
    """Load script-specific data from data/scripts/*.tsv files."""

    DATA_DIR = Dirs.DATA / "scripts"

    # ─── Nushu ───────────────────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_nushu() -> tuple[dict[int, str], dict[int, str]]:
        """Load Nushu readings and Duben references from NushuSources.txt."""
        readings: dict[int, str] = {}
        refs: dict[int, str] = {}
        for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "NushuSources.txt")):
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            try:
                cp = int(parts[0][2:], 16)
            except (ValueError, IndexError):
                continue
            tag = parts[1]
            value = parts[2]
            if tag == "kNSHU_Reading":
                readings[cp] = value
            elif tag == "kNSHU_DubenSrc":
                refs[cp] = value
        return readings, refs

    # ─── Khitan ─────────────────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_khitan() -> tuple[dict[int, str], dict[int, str]]:
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "khitan.tsv")
        readings: dict[int, str] = {}
        meanings: dict[int, str] = {}
        for row in rows:
            if len(row) < 3:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            if row[1]:
                readings[cp] = row[1]
            if row[2]:
                meanings[cp] = row[2]
        return readings, meanings

    # ─── Egyptian Hieroglyphs ───────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_hieroglyph_descriptions() -> dict[int, str]:
        """Load Egyptian hieroglyph descriptions from Unikemet.txt."""
        result: dict[int, str] = {}
        for line in filter(line_has_content, TxtParser.get_txt(Dirs.UCD / "Unikemet.txt")):
            parts = line.strip().split("\t")
            if len(parts) < 3 or parts[1] != "kEH_Desc":
                continue
            try:
                cp = int(parts[0][2:], 16)
            except (ValueError, IndexError):
                continue
            if parts[2]:
                result[cp] = parts[2]
        return result

    # ─── Tangut: Li Fanwen ──────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_li_fanwen() -> list[dict]:
        """Returns list indexed by offset from TANGUT_START."""
        TANGUT_START = 0x17000
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_li_fanwen.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 8:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_START
            while len(data) <= offset:
                data.append({})
            data[offset] = {
                "number": int(row[1]) if row[1] else 0,
                "variant": int(row[2]) if row[2] else 0,
                "additional": int(row[3]) if row[3] else 0,
                "reading": row[4],
                "english": row[5],
                "tone": int(row[6]) if row[6] else 0,
                "rime": int(row[7]) if row[7] else 0,
            }
        return data

    # ─── Tangut: Kychanov ───────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_kychanov() -> list[dict]:
        TANGUT_START = 0x17000
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_kychanov.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 6:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_START
            while len(data) <= offset:
                data.append({})
            data[offset] = {
                "number": int(row[1]) if row[1] else 0,
                "additional": int(row[2]) if row[2] else 0,
                "reading": row[3],
                "tone": int(row[4]) if row[4] else 0,
                "rime": int(row[5]) if row[5] else 0,
            }
        return data

    # ─── Tangut: Sofronov ───────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_sofronov() -> list[dict]:
        TANGUT_START = 0x17000
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_sofronov.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 6:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_START
            while len(data) <= offset:
                data.append({})
            data[offset] = {
                "number": int(row[1]) if row[1] else 0,
                "additional": int(row[2]) if row[2] else 0,
                "reading": row[3],
                "tone": int(row[4]) if row[4] else 0,
                "rime": int(row[5]) if row[5] else 0,
            }
        return data

    # ─── Tangut: Nishida ────────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_nishida() -> list[dict]:
        TANGUT_START = 0x17000
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_nishida.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 4:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_START
            while len(data) <= offset:
                data.append({})
            data[offset] = {
                "reference1": row[1],
                "reference2": row[2],
                "reading": row[3],
            }
        return data

    # ─── Tangut: Miyake ─────────────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_miyake() -> list[dict]:
        TANGUT_START = 0x17000
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_miyake.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 3:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_START
            while len(data) <= offset:
                data.append({})
            syllable = row[1]
            parts = syllable.split("-")
            data[offset] = {
                "initial": int(parts[0]) if len(parts) > 0 and parts[0] else 0,
                "medial": int(parts[1]) if len(parts) > 1 and parts[1] else 0,
                "final": int(parts[2]) if len(parts) > 2 and parts[2] else 0,
                "tone": int(parts[3]) if len(parts) > 3 and parts[3] else 0,
                "rime": int(row[2]) if row[2] else 0,
            }
        return data

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_miyake_phonetic_tables() -> dict:
        """Load merged Miyake phonetic table from tangut_miyake_phonetics.tsv.

        Format: key, miyake2015, miyake2012
        Keys: initial-N, medial-N, final-N
        """
        d = ScriptsLoader.DATA_DIR
        initials: dict[str, list[str]] = {"2015": [], "2012": []}
        medials: list[str] = []
        finals: dict[str, list[str]] = {"2015": [], "2012": []}
        for row in TsvParser.get_tsv(d / "tangut_miyake_phonetics.tsv")[1:]:
            if len(row) < 3:
                continue
            key = row[0]
            v2015 = row[1]
            v2012 = row[2]
            if key.startswith("initial-"):
                initials["2015"].append(v2015)
                initials["2012"].append(v2012)
            elif key.startswith("medial-"):
                medials.append(v2015)
            elif key.startswith("final-"):
                finals["2015"].append(v2015)
                finals["2012"].append(v2012)
        return {"initials": initials, "medials": medials, "finals": finals}

    # ─── Tangut: merged character data ──────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_character_data() -> list[dict]:
        TANGUT_START = 0x17000
        TANGUT_SUPP_START = 0x18D00
        TANGUT_COUNT = 0x187FF - TANGUT_START + 1
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_character_data.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 7:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            if TANGUT_START <= cp <= 0x187FF:
                offset = cp - TANGUT_START
            elif TANGUT_SUPP_START <= cp <= 0x18D7F:
                offset = (cp - TANGUT_SUPP_START) + TANGUT_COUNT
            else:
                continue
            while len(data) <= offset:
                data.append({})
            var1_str, var2_str = row[5], row[6]
            var1 = int(var1_str, 16) if var1_str.startswith("0x") else (int(var1_str) if var1_str.isdigit() else 0)
            var2 = int(var2_str, 16) if var2_str.startswith("0x") else (int(var2_str) if var2_str.isdigit() else 0)
            data[offset] = {
                "merged_source": row[1],
                "radical": int(row[2]) if row[2] else 0,
                "stroke_count": int(row[3]) if row[3] else 0,
                "ids": row[4],
                "variant1": var1,
                "variant2": var2,
            }
        return data

    # ─── Tangut: component data ─────────────────────────────────────

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_tangut_component_data() -> list[dict]:
        TANGUT_COMPS_START = 0x18800
        rows = TsvParser.get_tsv(ScriptsLoader.DATA_DIR / "tangut_component_data.tsv")
        data: list[dict] = []
        for row in rows:
            if len(row) < 6:
                continue
            try:
                cp = int(row[0][2:], 16)
            except (ValueError, IndexError):
                continue
            offset = cp - TANGUT_COMPS_START
            while len(data) <= offset:
                data.append({})
            fc = row[4]
            data[offset] = {
                "stroke_count": int(row[1]) if row[1] else 0,
                "radical": int(row[2]) if row[2] else 0,
                "char_count": int(row[3]) if row[3] else 0,
                "first_character": int(fc, 16) if fc.startswith("0x") else 0,
                "extra_count": int(row[5]) if row[5] else 0,
            }
        return data
