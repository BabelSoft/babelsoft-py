import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent
sys.path.append(str(LIB_DIR))


from src.cjkv.cjk import CJK, IDS, RS, Radical, SrcRef  # noqa: E402
from src.unicode.class_ import CodePoint  # noqa: E402

# ═══════════════════════  Basic CJK  ═══════════════════════


def test_cjk():
    assert str(CJK("A")) == "CJK(0x0041, A)"
    assert str(CJK(0x41)) == "CJK(0x0041, A)"
    assert str(CJK("U+4141")) == "CJK(0x4141, 䅁)"
    assert str(CJK("我")) == "CJK(0x6211, 我)"


def test_cjk_equality():
    assert CJK("一") == CJK(0x4E00)
    assert CJK("一") == 0x4E00
    assert CJK("一") != CJK("国")
    assert CJK("一") != "一"


def test_from_codepoint():
    assert CJK.from_codepoint(CodePoint(0x4E00)) == CJK("一")
    assert CJK.from_codepoint(None) is None


# ═══════════════════════  is_cjk_ideograph  ═══════════════════════


def test_is_cjk_ideograph():
    assert CJK("一").is_cjk_ideograph() is True
    assert CJK("A").is_cjk_ideograph() is False
    assert CJK(0x4E00).is_cjk_ideograph() is True
    assert CJK(0x20000).is_cjk_ideograph() is True


def test_is_cjk_ideograph_compat():
    assert CJK(0xFA0E).is_cjk_ideograph() is True
    assert CJK(0xFA10).is_cjk_ideograph() is False
    assert CJK(0xF900).is_cjk_ideograph(compatibility=True) is True


# ═══════════════════════  Flags  ═══════════════════════


def test_flags_traditional_simplified():
    assert CJK("國").is_traditional() is True
    assert CJK("國").is_simplified() is False
    assert CJK("国").is_simplified() is True
    assert CJK("国").is_traditional() is False
    assert CJK("一").is_traditional() is False
    assert CJK("一").is_simplified() is False


def test_flags_shinjitai_kyujitai():
    assert CJK("國").is_kyujitai() is True
    assert CJK("国").is_shinjitai() is True
    assert CJK("龍").is_kyujitai() is True
    assert CJK("竜").is_shinjitai() is True


def test_flags_ivs():
    assert CJK("一").has_ivs() is True
    assert CJK("A").has_ivs() is False


def test_flags_misc():
    for c in [CJK("國"), CJK("国")]:
        assert c.is_fanti_jianti() is False
        assert c.is_zhuang() is False


# ═══════════════════════  Filter  ═══════════════════════


def test_filter_traditional():
    assert CJK("國").filter_traditional() is True
    assert CJK("一").filter_traditional() is True
    assert CJK("国").filter_traditional() is False


def test_filter_simplified():
    assert CJK("国").filter_simplified() is True
    assert CJK("一").filter_simplified() is True
    assert CJK("國").filter_simplified() is False


# ═══════════════════════  Conversion  ═══════════════════════


def test_to_simplified():
    assert CJK("國").to_simplified() == CJK("国")
    assert CJK("国").to_simplified() is None
    assert CJK("龍").to_simplified() == CJK("龙")


def test_to_traditional():
    assert CJK("国").to_traditional() == CJK("國")
    assert CJK("國").to_traditional() is None
    assert CJK("龙").to_traditional() == CJK("龍")


def test_to_shinjitai():
    assert CJK("龍").to_shinjitai() == CJK("竜")
    assert CJK("竜").to_shinjitai() is None


def test_to_kyujitai():
    assert CJK("竜").to_kyujitai() == CJK("龍")
    assert CJK("龍").to_kyujitai() is None


# ═══════════════════════  GetMappings  ═══════════════════════


def test_get_mappings():
    ct, cs, cj = CJK("國").get_mappings()
    assert ct == CJK("國") and cs == CJK("国")
    ct, cs, cj = CJK("国").get_mappings()
    assert ct == CJK("國") and cs == CJK("国") and cj == CJK("国")
    ct, cs, cj = CJK("一").get_mappings()
    assert ct is None and cs is None and cj is None


# ═══════════════════════  IRG Sources  ═══════════════════════


def test_get_source_ref():
    c = CJK("一")
    assert c.get_source_ref("G") == "G0-523B"
    assert c.get_source_ref("H") == "HB1-A440"
    assert c.get_source_ref("J") == "J0-306C"
    assert c.get_source_ref("KP") == "KP0-FCD6"
    assert c.get_source_ref("X") == ""


def test_find_source_ref():
    assert CJK.find_source_ref("G0-482B") == CJK(0x5168)
    assert CJK.find_source_ref("G0-482B", exact=True) == CJK(0x5168)
    assert CJK.find_source_ref("nonexistent") is None


def test_source_refs():
    refs = CJK("一").source_refs()
    assert "G0-523B" in refs
    assert "HB1-A440" in refs
    assert CJK("A").source_refs() == ""


def test_is_source():
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


# ═══════════════════════  SrcRef  ═══════════════════════


def test_src_ref():
    sr = SrcRef("G0-5251")
    assert sr.prefix == "G0"
    assert sr.is_valid() is True
    assert SrcRef("nonexistent").is_valid() is False


def test_src_ref_submitter():
    assert SrcRef("G0-5251").submitter.name == "CHINA_SINGAPORE"
    assert SrcRef("HB1-A477").submitter.name == "HONG_KONG_SAR"
    assert SrcRef("MY-12345").submitter is None


def test_src_ref_find():
    assert SrcRef("G0-482B").find() == CJK(0x5168)
    assert SrcRef("nonexistent").find() is None


def test_irg_source_class():
    src = SrcRef.IRGSrc.by_code("G")
    assert src.name == "CHINA_SINGAPORE"
    assert src.bit == 0x0001
    assert src.field == "kIRG_GSource"
    assert len(SrcRef.IRGSrc.all()) == 11


# ═══════════════════════  Source reference list  ═══════════════════════


def test_source_reference():
    assert CJK("已").source_reference() == [
        SrcRef(reference="G0-5251"),
        SrcRef(reference="HB1-A477"),
        SrcRef(reference="J0-5661"),
        SrcRef(reference="KP0-FCAC"),
        SrcRef(reference="K0-6C2B"),
        SrcRef(reference="T1-4458"),
        SrcRef(reference="V1-5360"),
    ]


def test_source_reference_single():
    assert CJK("已").source_reference(submitter=SrcRef.IRGSrc.G) == [SrcRef(reference="G0-5251")]


# ═══════════════════════  Radical  ═══════════════════════


def test_radical_strokes():
    rs = CJK("已").radical_strokes()
    assert len(rs) == 1
    assert rs[0].radical == Radical(49, 0)
    assert rs[0].residual_stroke == 0


def test_primary_radical_stroke():
    assert CJK("一").primary_radical_stroke().radical == Radical(1, 0)
    assert CJK("国").primary_radical_stroke().radical == Radical(31, 0)


def test_primary_radical_stroke_error():
    import pytest

    with pytest.raises(AssertionError):
        CJK("A").primary_radical_stroke()


def test_radical_glyph():
    assert CJK.get_radical_glyph(0) == CJK(0x2F00)
    assert CJK.get_radical_number(0) == 1
    assert CJK.get_radical_flag(0) == 0
    assert CJK.get_radical_glyph(-1) is None


def test_find_ideographs_for_radical():
    assert CJK(0x9F8D) in CJK.find_ideographs_for_radical(212, 0, 0)
    assert len(CJK.find_ideographs_for_radical(212, 0, all_strokes=True)) > 40
    assert len(CJK.find_ideographs_for_radical(212, 0, 5, fuzzy=True)) > 0
    assert CJK.find_ideographs_for_radical(999, 0) == []


def test_to_equivalent():
    # Some CJK compat chars have equivalents, some don't
    equiv = CJK(0xFA0E).to_equivalent()
    # Just verify the method doesn't crash
    assert equiv is None or isinstance(equiv, CJK)


# ═══════════════════════  IDS  ═══════════════════════


def test_ids():
    ids_info = CJK("已").ids_babelsoft()
    assert ids_info
    assert ids_info.cjk == CJK("已")
    assert ids_info.ids_list == [IDS("^已$(GHTJKPV)")]


# ═══════════════════════  RS ideographs  ═══════════════════════


def test_ideographs():
    assert RS.from_unihan("212.11").ideographs() == [CJK(0x2A6A3), CJK(0x2A6A4), CJK(0x32ACB), CJK(0x33476)]
    assert RS.from_unihan("212'.11").ideographs() == [CJK(0x2CE9D)]
    assert RS.from_unihan("212''.11").ideographs() == [CJK(0x2412F), CJK(0x2AC6F), CJK(0x2C099)]
    assert RS.from_unihan("212'''.11").ideographs() == []


# ═══════════════════════  Readings  ═══════════════════════


def test_readings():
    rd = CJK("一").readings()
    assert rd["kMandarin"] == "yī"
    assert rd["kCantonese"] == "jat1"
    assert "kKorean" in rd
    assert CJK("A").readings() == {}


# ═══════════════════════  XML  ═══════════════════════


def test_get_xml_data():
    xml = CJK("一").get_xml_data()
    assert "<Character" in xml
    assert "<RadicalStrokes>" in xml
    assert "<IDS>" in xml
    assert "<Readings>" in xml
    assert "<Mandarin>yī</Mandarin>" in xml
    assert "<SourceReferences>" in xml


def test_get_xml_data_indent():
    xml = CJK("一").get_xml_data(indent=True)
    for line in xml.split("\r\n"):
        if line.strip():
            assert line.startswith("\t\t")


def test_get_xml_data_mappings():
    xml = CJK("国").get_xml_data()
    assert "<Traditional" in xml
    assert "<SimplifiedChinese" in xml
    assert "<SimplifiedJapanese" in xml


# ═══════════════════════  RS class  ═══════════════════════


def test_rs_unihan_roundtrip():
    rs = RS.from_unihan("212'''.6")
    assert rs.radical == Radical(212, 3)
    assert rs.residual_stroke == 6
    assert rs.to_unihan() == "212'''.6"


def test_rs_no_variant():
    rs = RS.from_unihan("212'''.6").no_variant()
    assert rs.radical == Radical(212, 0)
    assert rs.residual_stroke == 6


def test_rs_irg_roundtrip():
    rs = RS.from_irg_radical("212.3")
    assert rs.radical == Radical(212, 3)
    assert rs.to_irg_radical() == "212.3"


def test_rs_no_stroke():
    rs = RS.from_unihan("212'''")
    assert rs.radical == Radical(212, 3)
    assert rs.residual_stroke == 0


# ═══════════════════════  Radical class  ═══════════════════════


def test_radical_roundtrip():
    r = Radical.from_unihan("212'''")
    assert r.rad == 212
    assert r.var == 3
    assert r.to_unihan() == "212'''"
    assert r.to_irg_radical() == "212.3"


def test_radical_eq():
    assert Radical(212, 3) == Radical(212, 3)
    assert Radical(212, 3) != Radical(212, 0)
    assert hash(Radical(212, 3)) == hash(Radical(212, 3))
