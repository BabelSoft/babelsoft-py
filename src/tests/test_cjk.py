import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(LIB_DIR))


from src.cjkv.cjk import CJK, IDS, RS, SrcRef  # noqa: E402


def test_cjk():
    assert str(CJK("A")) == "CJK(0x0041, A)"
    assert str(CJK(0x41)) == "CJK(0x0041, A)"
    assert str(CJK("U+4141")) == "CJK(0x4141, 䅁)"
    assert str(CJK("我")) == "CJK(0x6211, 我)"


def test_ids():
    ids_info = CJK("已").ids_babelsoft()
    assert ids_info
    assert ids_info.cjk == CJK("已")
    assert ids_info.ids_list == [IDS("^已$(GHTJKPV)")]
    assert ids_info.comment == ""


def test_radical_strokes():
    rs = CJK("已").radical_strokes()
    assert len(rs) == 1
    assert rs[0].radical == 49
    assert rs[0].variant == 0
    assert rs[0].residual_stroke == 0


def test_source_reference():
    assert CJK("已").source_reference() == [
        SrcRef(submitter=SrcRef.Submitter.CHINA_SINGAPORE, reference="G0-5251"),
        SrcRef(submitter=SrcRef.Submitter.HONG_KONG_SAR, reference="HB1-A477"),
        SrcRef(submitter=SrcRef.Submitter.JAPAN, reference="J0-5661"),
        SrcRef(submitter=SrcRef.Submitter.ROK, reference="K0-6C2B"),
        SrcRef(submitter=SrcRef.Submitter.DPRK, reference="KP0-FCAC"),
        SrcRef(submitter=SrcRef.Submitter.TCA, reference="T1-4458"),
        SrcRef(submitter=SrcRef.Submitter.VIETNAM, reference="V1-5360"),
    ]


def test_find():
    src_ref = SrcRef(reference="G0-5251")
    assert src_ref.find() == CJK("已")


def test_ideographs():
    assert RS.from_unihan("212.11").ideographs() == [CJK(0x2A6A3), CJK(0x2A6A4), CJK(0x32ACB), CJK(0x33476)]
    assert RS.from_unihan("212'.11").ideographs() == [CJK(0x2CE9D)]
    assert RS.from_unihan("212''.11").ideographs() == [CJK(0x2412F), CJK(0x2AC6F), CJK(0x2C099)]
    assert RS.from_unihan("212'''.11").ideographs() == []
