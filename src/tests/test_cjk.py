import sys
from pathlib import Path

from rich import print

LIB_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(LIB_DIR))


from src.cjkv.cjk import CJK  # noqa: E402


def test_cjk():
    print(CJK("A"))
    print(CJK(0x41))
    print(CJK("U+4141"))
    print(CJK("我"))


def test_ids():
    cjk = CJK("已")
    print(cjk.ids_babelsoft())


def test_radical_strokes():
    cjk = CJK("已")
    print(cjk.radical_strokes())


def test_source_reference():
    cjk = CJK("已")
    print(cjk.source_reference())


test_cjk()
test_ids()
test_radical_strokes()
test_source_reference()
