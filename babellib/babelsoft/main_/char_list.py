"""
CharList — ordered character list (ported from c/Main/CharList.h)

Maintains a sorted list of Unicode codepoints with
insert, append, remove, and lookup operations.
"""

from __future__ import annotations

import bisect


class CharList:
    """Ordered, deduplicated list of Unicode codepoints."""

    def __init__(self, items: list[int] | None = None) -> None:
        self._data: list[int] = []
        if items:
            for cp in items:
                self.insert(cp)

    def insert(self, cp: int) -> bool:
        """Insert a codepoint. Returns True if inserted, False if already present."""
        idx = bisect.bisect_left(self._data, cp)
        if idx < len(self._data) and self._data[idx] == cp:
            return False
        self._data.insert(idx, cp)
        return True

    def append(self, cp: int) -> bool:
        """Append a codepoint to the end (only if larger than all existing)."""
        if not self._data or cp > self._data[-1]:
            self._data.append(cp)
            return True
        return self.insert(cp)

    def remove(self, cp: int) -> bool:
        """Remove a codepoint. Returns True if found and removed."""
        idx = bisect.bisect_left(self._data, cp)
        if idx < len(self._data) and self._data[idx] == cp:
            self._data.pop(idx)
            return True
        return False

    def is_in_list(self, cp: int) -> bool:
        """Check if a codepoint is in the list."""
        idx = bisect.bisect_left(self._data, cp)
        return idx < len(self._data) and self._data[idx] == cp

    @property
    def count(self) -> int:
        return len(self._data)

    def get_at(self, index: int) -> int:
        """Get codepoint at the given index."""
        if 0 <= index < len(self._data):
            return self._data[index]
        return 0

    def to_list(self) -> list[int]:
        """Return a copy of the list."""
        return list(self._data)

    def to_string(self) -> str:
        """Convert all codepoints to a Unicode string."""
        return "".join(chr(cp) for cp in self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, cp: int) -> bool:
        return self.is_in_list(cp)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self) -> str:
        cps = ", ".join(f"U+{cp:04X}" for cp in self._data[:10])
        if len(self._data) > 10:
            cps += ", ..."
        return f"CharList([{cps}])"
