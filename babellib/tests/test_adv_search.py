"""Tests for the advanced search expression fields and tokenizer/parser.

Covers the expression fields added for the search dialog:
    pinyin / cantonese / cjkradical / residualstroke / yiradical and the
    Tangut dictionaries (lifanwen2008 / lifanwen1997 / kychanov2006 /
    sofronov1968 / nishida1966), plus the tokenizer/parser fixes that make
    them work (digit-containing keys, space-separated implicit AND, pipe
    syntax for Tangut references).
"""

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from babelmap.backend.adv_search import (
    BinOp,
    Cond,
    _tokenize,
    evaluate,
    parse_query,
)


def matches(q: str, cp: int) -> bool:
    """Evaluate a query against a single codepoint (no block data)."""
    ast = parse_query(q)
    assert ast is not None, f"query failed to parse: {q!r}"
    return evaluate(ast, cp, [])


# ═══════════════════  Tokenizer / parser  ═══════════════════


class TestTokenizerParser:
    def test_key_with_digits(self):
        """Property keys containing digits (lifanwen1997 etc.) stay one token."""
        toks = _tokenize("lifanwen1997=5995")
        types = [t.type.name for t in toks]
        texts = [t.text for t in toks]
        assert types == ["IDENT", "OP", "VALUE", "EOF"]
        assert texts[0] == "lifanwen1997"
        assert texts[2] == "5995"

    def test_space_separated_implicit_and(self):
        ast = parse_query("cjkradical=154 residualstroke=14")
        assert isinstance(ast, BinOp)
        assert ast.op == "AND"
        assert isinstance(ast.left, Cond) and ast.left.key == "cjkradical"
        assert isinstance(ast.right, Cond) and ast.right.key == "residualstroke"

    def test_explicit_and_still_works(self):
        ast = parse_query("cjkradical=154 AND residualstroke=14")
        assert isinstance(ast, BinOp) and ast.op == "AND"

    def test_tangut_pipe_converted(self):
        ast = parse_query("lifanwen2008=|22|")
        assert isinstance(ast, Cond)
        assert ast.key == "lifanwen2008"
        assert ast.wildcard is True
        assert ast.value == "22"


# ═══════════════════  Pinyin / Cantonese  ═══════════════════


class TestPinyinCantonese:
    def test_pinyin_a_matches_user_examples(self):
        for cp in [
            0x5416,
            0x5475,
            0x554A,
            0x55C4,
            0x814C,
            0x9312,
            0x9515,
            0x963F,
            0x20F1E,
            0x25969,
            0x2825A,
        ]:  # 吖呵啊嗄腌錒锕阿𠼞𥥩𨉚
            assert matches("pinyin=a", cp), f"pinyin=a should match U+{cp:05X}"

    def test_pinyin_with_tone(self):
        assert matches("pinyin=a1", 0x5416)  # 吖 = ya1 / a1
        assert matches("pinyin=ya", 0x5416)
        assert matches("pinyin=ya1", 0x5416)

    def test_pinyin_negative(self):
        assert not matches("pinyin=zzz", 0x5416)
        assert not matches("pinyin=b", 0x5416)

    def test_cantonese_aan_matches_user_examples(self):
        for cp in [0x599F, 0x664F, 0x9D33, 0x9DC3, 0x20E75, 0x2A192, 0x2EB68]:  # 妟晏鴳鷃𠹵𪆒𮭨
            assert matches("cantonese=aan", cp), f"cantonese=aan should match U+{cp:05X}"

    def test_cantonese_with_tone(self):
        assert matches("cantonese=aan3", 0x599F)
        assert matches("cantonese=ngaan3", 0x599F)

    def test_cantonese_negative(self):
        assert not matches("cantonese=zzz", 0x599F)


# ═══════════════════  CJK radical / residual stroke  ═══════════════════


class TestCJKSRadicalStroke:
    def test_cjkradical_residualstroke_user_example(self):
        # 𫎬 U+2B3AC, 𬥿 U+2C97F, 𰷭 U+30DED — all radical 154, residual 14
        for cp in [0x2B3AC, 0x2C97F, 0x30DED]:
            assert matches("cjkradical=154 residualstroke=14", cp), f"U+{cp:05X}"

    def test_cjkradical_alone(self):
        assert matches("cjkradical=154", 0x2B3AC)

    def test_residualstroke_alone(self):
        assert matches("residualstroke=14", 0x2B3AC)

    def test_residualstroke_comparison_ops(self):
        assert matches("residualstroke>=14", 0x2B3AC)
        assert matches("residualstroke<=14", 0x2B3AC)
        assert not matches("residualstroke>14", 0x2B3AC)
        assert not matches("residualstroke<14", 0x2B3AC)
        assert matches("residualstroke!=15", 0x2B3AC)


# ═══════════════════  Yi radical / residual stroke  ═══════════════════


class TestYiRadical:
    def test_yiradical_residualstroke_user_example(self):
        # ꇭ U+A1ED = radical 26 (꓆), residual 2
        assert matches("yiradical=꓆", 0xA1ED)
        assert matches("yiradical=꓆ residualstroke=2", 0xA1ED)

    def test_yiradical_negative(self):
        # ꐭ U+A42D is radical 8, not 26
        assert not matches("yiradical=꓆", 0xA42D)
        assert not matches("yiradical=꓆ residualstroke=2", 0xA42D)

    def test_residualstroke_yi(self):
        assert matches("residualstroke=2", 0xA1ED)
        assert not matches("residualstroke=3", 0xA1ED)


# ═══════════════════  Tangut dictionaries  ═══════════════════


class TestTangutSources:
    def test_lifanwen2008_substring(self):
        assert matches("lifanwen2008=22", 0x17D55)  # L2008-0022 contains "22"

    def test_lifanwen2008_exact(self):
        assert matches("lifanwen2008=|22|", 0x17D55)
        assert not matches("lifanwen2008=|22|", 0x17073)  # other numbers aren't 22

    def test_lifanwen1997_special(self):
        assert matches("lifanwen1997=5995", 0x1869E)  # 1997-only number
        assert matches("lifanwen1997=1913", 0x17158)  # swapped vs 2008
        assert not matches("lifanwen1997=5995", 0x17158)

    def test_lifanwen1997_falls_back_to_2008(self):
        # 17D55 has no explicit 1997 entry (== 2008), so 1997 matches too.
        assert matches("lifanwen1997=|22|", 0x17D55)

    def test_kychanov(self):
        assert matches("kychanov2006=|3698|", 0x17000)
        assert matches("kychanov2006=3698", 0x17000)

    def test_sofronov(self):
        assert matches("sofronov1968=1100", 0x17000)
        assert matches("sofronov1968=|1100|", 0x17000)

    def test_nishida(self):
        assert matches("nishida1966=|1-052|", 0x17000)
        assert matches("nishida1966=052", 0x17000)

    def test_tangut_negative(self):
        assert not matches("lifanwen2008=|9999|", 0x17000)
        assert not matches("kychanov2006=|9999|", 0x17000)
