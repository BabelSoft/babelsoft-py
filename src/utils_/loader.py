from __future__ import annotations

import functools
import re
from pathlib import Path

from src.unicode.class_ import Block, CodePoint
from src.utils_.dirs import Dirs
from src.utils_.parser import TsvParser, TxtParser, YamlParser, line_has_content


def _parse_rs_unihan(text: str) -> tuple[int, int, int]:
    """Parse Unihan RS string like "212'''.6" -> (212, 3, 6)."""
    radical_part, sep, stroke = text.partition(".")
    stroke = int(stroke) if sep else 0
    variant = len(radical_part) - len(radical_part.rstrip("'"))
    radical = int(radical_part.rstrip("'")) if variant else int(radical_part)
    return radical, variant, stroke


_FLAG_NAME_TO_BIT = {
    "IVS": 0x0001,
    "Fanti": 0x0002,
    "FantiPlus": 0x0002,
    "Jianti": 0x0004,
    "JiantiPlus": 0x0004,
    "FantiJianti": 0x0008,
    "Xinzixing": 0x0010,
    "Jiuzixing": 0x0020,
    "Shinjitai": 0x0040,
    "Kyujitai": 0x0080,
    "Pinyin": 0x0100,
    "Jyutping": 0x0200,
    "YaleKorean": 0x0400,
    "QuocNgu": 0x0800,
    "Zhuang": 0x1000,
    "SIP": 0x2000,
    "TIP": 0x4000,
}


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
        return {
            int(row[0][2:], 16): sum(_FLAG_NAME_TO_BIT[label] for label in row[2].split() if label in _FLAG_NAME_TO_BIT)
            for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_flags.tsv")
            if len(row) >= 3
        }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_mappings() -> dict[int, int]:
        return {
            int(row[0][2:], 16): int(row[2][2:], 16)
            for row in TsvParser.get_tsv(Dirs.BABELSOFT / "cjk_mappings.tsv")
            if len(row) >= 4
        }

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _load_yaml_pair_map(path: Path) -> tuple[dict[int, int], dict[int, int]]:
        a2b, b2a = {}, {}
        for x, y in YamlParser.get_yaml(path):
            a2b[x], b2a[y] = y, x
        return a2b, b2a

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_shinjitai_maps():
        return CJKLoader._load_yaml_pair_map(Dirs.BABELSOFT / "ShinjitaiMapping.yaml")

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def load_xinjiu_maps():
        return CJKLoader._load_yaml_pair_map(Dirs.BABELSOFT / "XinJiuMapping.yaml")

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
