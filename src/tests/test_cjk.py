import sys
from pathlib import Path

from rich import print

LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.append(str(LIB_DIR))


from cjkv.cjk import CJK, Block  # noqa: E402

...
