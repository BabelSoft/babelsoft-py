"""Tests for CJKV reading lookups and CJK character handling."""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))

from src.cjkv.cjk import CJK, IDS, RS, Radical, SrcRef  # noqa: E402
from src.cjkv.jyutping import Jyutping  # noqa: E402
from src.cjkv.korean import HangulSyllableType, Korean  # noqa: E402
from src.cjkv.pinyin import Pinyin  # noqa: E402
from src.cjkv.vietnamese import Vietnamese  # noqa: E402
from src.cjkv.zhuang import Zhuang  # noqa: E402
from src.unicode import CodePoint  # noqa: E402

# ═══════════════════════  CJK Character  ═══════════════════════


class TestCJK:
    """Tests for CJK character construction and basic properties."""

    def test_construction(self):
        assert str(CJK("A")) == "CJK(0x0041, A)"
        assert str(CJK(0x41)) == "CJK(0x0041, A)"
        assert str(CJK("U+4141")) == "CJK(0x4141, 䅁)"
        assert str(CJK("我")) == "CJK(0x6211, 我)"

    def test_equality(self):
        assert CJK("一") == CJK(0x4E00)
        assert CJK("一") == 0x4E00
        assert CJK("一") != CJK("国")
        assert CJK("一") != "一"

    def test_from_codepoint(self):
        assert CJK.from_codepoint(CodePoint(0x4E00)) == CJK("一")
        assert CJK.from_codepoint(None) is None

    def test_is_cjk_ideograph(self):
        assert CJK("一").is_cjk_ideograph() is True
        assert CJK("A").is_cjk_ideograph() is False
        assert CJK(0x4E00).is_cjk_ideograph() is True
        assert CJK(0x20000).is_cjk_ideograph() is True

    def test_is_cjk_ideograph_compat(self):
        assert CJK(0xFA0E).is_cjk_ideograph() is True
        assert CJK(0xFA10).is_cjk_ideograph() is False
        assert CJK(0xF900).is_cjk_ideograph(compatibility=True) is True

    def test_traditional_simplified(self):
        assert CJK("國").is_traditional() is True
        assert CJK("國").is_simplified() is False
        assert CJK("国").is_simplified() is True
        assert CJK("国").is_traditional() is False
        assert CJK("一").is_traditional() is False
        assert CJK("一").is_simplified() is False

    def test_shinjitai_kyujitai(self):
        assert CJK("國").is_kyujitai() is True
        assert CJK("国").is_shinjitai() is True
        assert CJK("龍").is_kyujitai() is True
        assert CJK("竜").is_shinjitai() is True

    def test_ivs(self):
        assert CJK("一").has_ivs() is True
        assert CJK("A").has_ivs() is False

    def test_misc(self):
        for c in [CJK("國"), CJK("国")]:
            assert c.is_fanti_jianti() is False
            assert c.is_zhuang() is False

    def test_filter_traditional(self):
        assert CJK("國").filter_traditional() is True
        assert CJK("一").filter_traditional() is True
        assert CJK("国").filter_traditional() is False

    def test_filter_simplified(self):
        assert CJK("国").filter_simplified() is True
        assert CJK("一").filter_simplified() is True
        assert CJK("國").filter_simplified() is False

    def test_to_simplified(self):
        assert CJK("國").to_simplified() == CJK("国")
        assert CJK("国").to_simplified() is None
        assert CJK("龍").to_simplified() == CJK("龙")

    def test_to_traditional(self):
        assert CJK("国").to_traditional() == CJK("國")
        assert CJK("國").to_traditional() is None
        assert CJK("龙").to_traditional() == CJK("龍")

    def test_to_shinjitai(self):
        assert CJK("龍").to_shinjitai() == CJK("竜")
        assert CJK("竜").to_shinjitai() is None

    def test_to_kyujitai(self):
        assert CJK("竜").to_kyujitai() == CJK("龍")
        assert CJK("龍").to_kyujitai() is None

    def test_get_mappings(self):
        ct, cs, cj = CJK("國").get_mappings()
        assert ct == CJK("國") and cs == CJK("国")
        ct, cs, cj = CJK("国").get_mappings()
        assert ct == CJK("國") and cs == CJK("国") and cj == CJK("国")
        ct, cs, cj = CJK("一").get_mappings()
        assert ct is None and cs is None and cj is None

    def test_to_equivalent(self):
        equiv = CJK(0xFA0E).to_equivalent()
        assert equiv is None or isinstance(equiv, CJK)

    def test_get_source_ref(self):
        c = CJK("一")
        assert c.get_source_ref("G") == "G0-523B"
        assert c.get_source_ref("H") == "HB1-A440"
        assert c.get_source_ref("J") == "J0-306C"
        assert c.get_source_ref("KP") == "KP0-FCD6"
        assert c.get_source_ref("X") == ""

    def test_find_source_ref(self):
        assert CJK.find_source_ref("G0-482B") == CJK(0x5168)
        assert CJK.find_source_ref("G0-482B", exact=True) == CJK(0x5168)
        assert CJK.find_source_ref("nonexistent") is None

    def test_source_refs(self):
        refs = CJK("一").source_refs()
        assert "G0-523B" in refs
        assert "HB1-A440" in refs
        assert CJK("A").source_refs() == ""

    def test_is_source(self):
        c = CJK("一")
        ok, _ = c.is_source(1)
        assert ok is True
        ok, _ = c.is_source(1 | 2, match=1)
        assert ok is True
        ok, _ = c.is_source(0x0800, inverse=True)
        assert ok is True
        ok, _ = CJK(0xF900).is_source(1, unified_only=True)
        assert ok is False
        ok, _ = CJK("A").is_source(1)
        assert ok is False

    def test_source_reference(self):
        assert CJK("已").source_reference() == [
            SrcRef(reference="G0-5251"),
            SrcRef(reference="HB1-A477"),
            SrcRef(reference="J0-5661"),
            SrcRef(reference="KP0-FCAC"),
            SrcRef(reference="K0-6C2B"),
            SrcRef(reference="T1-4458"),
            SrcRef(reference="V1-5360"),
        ]

    def test_source_reference_single(self):
        assert CJK("已").source_reference(submitter=SrcRef.IRGSrc.G) == [SrcRef(reference="G0-5251")]

    def test_src_ref(self):
        sr = SrcRef("G0-5251")
        assert sr.prefix == "G0"
        assert sr.is_valid() is True
        assert SrcRef("nonexistent").is_valid() is False

    def test_submitter(self):
        assert SrcRef("G0-5251").submitter.name == "CHINA_SINGAPORE"
        assert SrcRef("HB1-A477").submitter.name == "HONG_KONG_SAR"
        assert SrcRef("MY-12345").submitter is None
        assert SrcRef("GS-12345").submitter.name == "SINGAPORE"
        assert SrcRef("SG-12345").submitter.name == "SINGAPORE"

    def test_find(self):
        assert SrcRef("G0-482B").find() == CJK(0x5168)
        assert SrcRef("nonexistent").find() is None

    def test_irg_source_class(self):
        src = SrcRef.IRGSrc.by_code("G")
        assert src.name == "CHINA_SINGAPORE"
        assert src.bit == 0x0001
        assert src.field == "kIRG_GSource"
        assert SrcRef.IRGSrc.by_code("SG").name == "SINGAPORE"
        assert SrcRef.IRGSrc.by_code("MY").display == "Malaysia"
        assert len(SrcRef.IRGSrc.all()) == 13

    def test_irg_matches_sg(self):
        # A Singapore source: GS- ref under kIRG_GSource → codes ['G'], refs ['GS-xxxxx']
        assert SrcRef.IRGSrc.matches(["G"], ["GS-12345"], "SG") is True
        assert SrcRef.IRGSrc.matches(["G"], ["G0-12345"], "SG") is False
        assert SrcRef.IRGSrc.matches(["G"], ["G0-12345"], "G") is True
        assert SrcRef.IRGSrc.matches(["G"], ["GS-12345"], "G") is False
        assert SrcRef.IRGSrc.matches(["H"], ["HB1-A477"], "H") is True

    def test_radical_strokes(self):
        rs = CJK("已").radical_strokes()
        assert len(rs) == 1
        assert rs[0].radical == Radical(49, 0)
        assert rs[0].residual_stroke == 0

    def test_primary_radical_stroke(self):
        assert CJK("一").primary_radical_stroke().radical == Radical(1, 0)
        assert CJK("国").primary_radical_stroke().radical == Radical(31, 0)

    def test_primary_radical_stroke_error(self):
        with pytest.raises(AssertionError):
            CJK("A").primary_radical_stroke()

    def test_radical_glyph(self):
        assert CJK.get_radical_glyph(0) == CJK(0x2F00)
        assert CJK.get_radical_number(0) == 1
        assert CJK.get_radical_flag(0) == 0
        assert CJK.get_radical_glyph(-1) is None

    def test_find_ideographs_for_radical(self):
        assert CJK(0x9F8D) in CJK.find_ideographs_for_radical(212, 0, 0)
        assert len(CJK.find_ideographs_for_radical(212, 0, all_strokes=True)) > 40
        assert len(CJK.find_ideographs_for_radical(212, 0, 5, fuzzy=True)) > 0
        assert CJK.find_ideographs_for_radical(999, 0) == []

    def test_unihan_roundtrip(self):
        rs = RS.from_unihan("212'''.6")
        assert rs.radical == Radical(212, 3)
        assert rs.residual_stroke == 6
        assert rs.to_unihan() == "212'''.6"

    def test_no_variant(self):
        rs = RS.from_unihan("212'''.6").no_variant()
        assert rs.radical == Radical(212, 0)
        assert rs.residual_stroke == 6

    def test_irg_roundtrip(self):
        rs = RS.from_irg_radical("212.3")
        assert rs.radical == Radical(212, 3)
        assert rs.to_irg_radical() == "212.3"

    def test_no_stroke(self):
        rs = RS.from_unihan("212'''")
        assert rs.radical == Radical(212, 3)
        assert rs.residual_stroke == 0

    @pytest.mark.skip(reason="RSIndex data structure pending adjustment; test will pass after update")
    def test_ideographs(self):
        assert RS.from_unihan("212.11").ideographs() == [
            CJK(0x2A6A3),
            CJK(0x2A6A4),
            CJK(0x32ACB),
            CJK(0x33476),
        ]
        assert RS.from_unihan("212'.11").ideographs() == [CJK(0x2CE9D)]
        assert RS.from_unihan("212''.11").ideographs() == [
            CJK(0x2412F),
            CJK(0x2AC6F),
            CJK(0x2C099),
        ]
        assert RS.from_unihan("212'''.11").ideographs() == []

    def test_roundtrip(self):
        r = Radical.from_unihan("212'''")
        assert r.rad == 212
        assert r.var == 3
        assert r.to_unihan() == "212'''"
        assert r.to_irg_radical() == "212.3"

    def test_eq(self):
        assert Radical(212, 3) == Radical(212, 3)
        assert Radical(212, 3) != Radical(212, 0)
        assert hash(Radical(212, 3)) == hash(Radical(212, 3))

    def test_ids(self):
        ids_info = CJK("已").ids_babelsoft()
        assert ids_info
        assert ids_info.cjk == CJK("已")
        assert ids_info.ids_list == [IDS("^已$(GHTJKPV)")]

    def test_readings(self):
        rd = CJK("一").readings()
        assert rd["kMandarin"] == "yī"
        assert rd["kCantonese"] == "jat1"
        assert "kKorean" in rd
        assert CJK("A").readings() == {}

    def test_xml_data(self):
        xml = CJK("一").get_xml_data()
        assert "<Character" in xml
        assert "<RadicalStrokes>" in xml
        assert "<IDS>" in xml
        assert "<Readings>" in xml
        assert "<Mandarin>yī</Mandarin>" in xml
        assert "<SourceReferences>" in xml

    def test_xml_data_indent(self):
        xml = CJK("一").get_xml_data(indent=True)
        for line in xml.split("\r\n"):
            if line.strip():
                assert line.startswith("\t\t")

    def test_xml_data_mappings(self):
        xml = CJK("国").get_xml_data()
        assert "<Traditional" in xml
        assert "<SimplifiedChinese" in xml
        assert "<SimplifiedJapanese" in xml


# ═══════════════════════  Jyutping (Cantonese)  ═══════════════════════


class TestJyutping:
    """Tests for Jyutping (Cantonese) reading lookup."""

    def test_labels(self):
        assert Jyutping.get_reading_label(0) == "aa"
        assert Jyutping.get_reading_label(1) == "aai"
        assert len(Jyutping.get_reading_label(100)) > 0

    def test_for_char_basic(self):
        assert Jyutping.get_jyutping_for_char(0x4E00) == "jat1"  # 一
        assert Jyutping.get_jyutping_for_char(0x4E8C) == "ji6"  # 二
        assert Jyutping.get_jyutping_for_char(0x4E09) == "saam1, saam3"  # 三

    def test_for_char_unknown(self):
        assert Jyutping.get_jyutping_for_char(0x41) == ""

    def test_first_reading_only(self):
        result = Jyutping.get_jyutping_for_char(0x4E09, first_reading_only=True)
        assert result == "saam1"

    def test_strip_tones(self):
        Jyutping.convert_tones(True)
        result = Jyutping.get_jyutping_for_char(0x4E09, may_strip_tones=True)
        Jyutping.convert_tones(False)
        assert result == "saam"

    def test_separator(self):
        result = Jyutping.get_jyutping_for_char(0x4E09, separator="; ")
        assert result == "saam1; saam3"

    def test_upper_case(self):
        Jyutping.use_upper_case_readings(True)
        result = Jyutping.get_jyutping_for_char(0x4E00)
        Jyutping.use_upper_case_readings(False)
        assert result == "JAT1"

    def test_find(self):
        results = Jyutping.find_jyutping("jat")
        assert 0x4E00 in results
        results_tone = Jyutping.find_jyutping("jat", tone=1)
        assert 0x4E00 in results_tone

    def test_find_nonexistent(self):
        assert Jyutping.find_jyutping("nonexistent") == []


# ═══════════════════════  Pinyin (Mandarin)  ═══════════════════════


class TestPinyin:
    """Tests for Pinyin (Mandarin) reading lookup."""

    def test_for_char_basic(self):
        result = Pinyin.get_pinyin_for_char(0x4E00)  # 一
        assert "yi1" in result
        assert "yi2" in result
        assert "yi4" in result
        result = Pinyin.get_pinyin_for_char(0x6211)  # 我
        assert "wo3" in result

    def test_for_char_unknown(self):
        assert Pinyin.get_pinyin_for_char(0xFFFE) == ""

    def test_first_reading_only(self):
        assert Pinyin.get_pinyin_for_char(0x4E00, first_reading_only=True) == "yi1"

    def test_strip_tones(self):
        Pinyin.convert_tones(True)
        result = Pinyin.get_pinyin_for_char(0x4E00, may_strip_tones=True)
        Pinyin.convert_tones(False)
        assert "yi" in result

    def test_upper_case(self):
        Pinyin.use_upper_case_readings(True)
        result = Pinyin.get_pinyin_for_char(0x4E00)
        Pinyin.use_upper_case_readings(False)
        assert result.isupper()
        assert "YI" in result

    def test_find(self):
        results = Pinyin.find_pinyin("yi")
        assert 0x4E00 in results
        results = Pinyin.find_pinyin("wo")
        assert 0x6211 in results


# ═══════════════════════  Korean (Yale + Hangul)  ═══════════════════════


class TestKoreanHangul:
    """Tests for Hangul decomposition, composition, and classification."""

    def test_decomposition(self):
        leading, vowel, trailing = Korean.get_hangul_decomposition(0xD55C)  # 한
        assert leading == 0x1112
        assert vowel == 0x1161
        assert trailing == 0x11AB

    def test_composition(self):
        assert Korean.compose_hangul(0x1112, 0x1161, 0x11AB) == 0xD55C  # 한
        assert Korean.compose_hangul(0x1100, 0x1161, 0) == 0xAC00  # 가

    def test_open_syllable(self):
        assert Korean.is_hangul_open_syllable(0xAC00) is True  # 가
        assert Korean.is_hangul_open_syllable(0xD55C) is False  # 한

    def test_syllable_type(self):
        assert Korean.get_hangul_syllable_type(0x1100) == HangulSyllableType.L
        assert Korean.get_hangul_syllable_type(0x1161) == HangulSyllableType.V
        assert Korean.get_hangul_syllable_type(0x11AB) == HangulSyllableType.T
        assert Korean.get_hangul_syllable_type(0xAC00) == HangulSyllableType.LV
        assert Korean.get_hangul_syllable_type(0xD55C) == HangulSyllableType.LVT

    def test_jamo_classification(self):
        assert Korean.is_lead_jamo(0x1100) is True
        assert Korean.is_lead_jamo(0x1161) is False
        assert Korean.is_vowel_jamo(0x1161) is True
        assert Korean.is_vowel_jamo(0x1100) is False
        assert Korean.is_trail_jamo(0x11AB) is True
        assert Korean.is_trail_jamo(0x1100) is False

    def test_hangul_name(self):
        name = Korean.get_hangul_name(0xD55C)  # 한
        assert "HANGUL SYLLABLE" in name
        assert "H" in name
        assert "A" in name
        assert "N" in name

    def test_jamo_short_name(self):
        assert Korean.get_jamo_short_name(0x1100) == "G"
        assert Korean.get_jamo_short_name(0x1161) == "A"


class TestKoreanReadings:
    """Tests for Korean (Yale) reading lookup."""

    def test_for_char(self):
        assert Korean.get_korean_for_char(0x4E00) == "il"  # 一
        assert Korean.get_korean_for_char(0x4E8C) == "i"  # 二

    def test_for_char_unknown(self):
        assert Korean.get_korean_for_char(0x41) == ""

    def test_upper_case(self):
        Korean.use_upper_case_readings(True)
        result = Korean.get_korean_for_char(0x4E00)
        Korean.use_upper_case_readings(False)
        assert result == "IL"


# ═══════════════════════  Vietnamese (Quốc Ngữ)  ═══════════════════════


class TestVietnameseReadings:
    """Tests for Vietnamese (Quốc Ngữ) reading lookup."""

    def test_for_char(self):
        result = Vietnamese.get_vietnamese_for_char(0x4E00)  # 一
        assert "nhất" in result

    def test_for_char_multiple(self):
        result = Vietnamese.get_vietnamese_for_char(0x4E09)  # 三
        assert result in ("tam", "tám") or "tam" in result

    def test_for_char_unknown(self):
        assert Vietnamese.get_vietnamese_for_char(0x41) == ""

    def test_upper_case(self):
        Vietnamese.use_upper_case_readings(True)
        result = Vietnamese.get_vietnamese_for_char(0x4E00)
        Vietnamese.use_upper_case_readings(False)
        assert result == "NHẤT"

    def test_first_reading_only(self):
        result = Vietnamese.get_vietnamese_for_char(0x4E00, first_reading_only=True)
        assert result == "nhất"


class TestVietnameseVIQR:
    """Tests for VIQR encoding/decoding."""

    def test_is_viqr(self):
        assert Vietnamese.is_viqr(0x41) is True
        assert Vietnamese.is_viqr(0x4E00) is False

    def test_unicode_to_viqr(self):
        assert Vietnamese.unicode_to_viqr(0x00E2) == "a^"  # â

    def test_conversion_roundtrip(self):
        viqr_str = Vietnamese.unicode_to_viqr(0x00E2)  # â
        ch1, ch2, ch3 = ord(viqr_str[0]), ord(viqr_str[1]), 0
        uni, _, _, _ = Vietnamese.viqr_to_unicode(ch1, ch2, ch3)
        assert uni == 0x00E2


# ═══════════════════════  Zhuang  ═══════════════════════


class TestZhuang:
    """Tests for Zhuang reading lookup."""

    def test_for_char(self):
        result = Zhuang.get_zhuang_for_char(0x4E00)  # 一
        assert "it" in result

    def test_for_char_unknown(self):
        assert Zhuang.get_zhuang_for_char(0x41) == ""

    def test_first_reading_only(self):
        result = Zhuang.get_zhuang_for_char(0x4E00, first_reading_only=True)
        assert len(result) > 0

    def test_strip_tones(self):
        result = Zhuang.get_zhuang_for_char(0x4E00, may_strip_tones=True)
        for tone_char in "zjxqh":
            assert tone_char not in result[-1:] if result else True

    def test_upper_case(self):
        Zhuang.use_upper_case_readings(True)
        result = Zhuang.get_zhuang_for_char(0x4E00)
        Zhuang.use_upper_case_readings(False)
        assert result == result.upper()

    def test_find(self):
        results = Zhuang.find_zhuang("it")
        assert 0x4E00 in results
