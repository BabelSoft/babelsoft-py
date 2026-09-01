"""
Utilities package — data loading, parsing, and directory helpers.

Provides infrastructure for loading TSV/TXT data files and
synchronising Unicode data from external sources.

Note: CJKLoader and ScriptsLoader are not exported here to avoid
circular imports with babelsoft.unicode.core.  Import them directly::

    from babelsoft.utils_.loader import CJKLoader, ScriptsLoader
"""

from .dirs import Dirs
from .parser import TsvParser, TxtParser, line_has_content
from .sync import UnicodeDataDownloader

__all__ = [
    "Dirs",
    "TsvParser",
    "TxtParser",
    "UnicodeDataDownloader",
    "line_has_content",
]
