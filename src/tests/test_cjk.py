import sys
from pathlib import Path

from rich import print

LIB_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(LIB_DIR))


from src.cjkv.cjk import CJK  # noqa: E402


def test_cjk():
    cjk = CJK("A")
    assert cjk.__str__() == "CJK(U+0041, A)"
    cjk = CJK(0x41)
    assert cjk.__str__() == "CJK(U+0041, A)"
    cjk = CJK("U+4141")
    assert cjk.__str__() == "CJK(U+4141, 䅁)"
    cjk = CJK("我")
    assert cjk.__str__() == "CJK(U+6211, 我)"


def test_ids():
    cjk = CJK("已")
    print(cjk.ids_babelsoft())


def test_radical_strokes():
    cjk = CJK("已")
    print(cjk.radical_strokes())


test_cjk()
test_ids()
test_radical_strokes()
