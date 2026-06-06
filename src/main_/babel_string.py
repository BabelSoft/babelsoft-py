"""
BabelString — Unicode string utilities (ported from c/Main/BabelString.h)

Provides character-level string operations: iteration by codepoint/grapheme,
line navigation, word navigation, case mapping, search, and conversion.
"""

from __future__ import annotations

from src.unicode.core import Unicode

# ─── Line break constants ─────────────────────────────────────────────

LINE_FEED = 0x000A
CARRIAGE_RETURN = 0x000D
NEXT_LINE = 0x0085
LINE_SEPARATOR = 0x2028
PARA_SEPARATOR = 0x2029


class BabelString:
    """Static utility methods for Unicode string manipulation."""

    # ─── Codepoint iteration ──────────────────────────────────────

    @staticmethod
    def number_of_characters(text: str) -> int:
        """Count Unicode codepoints (not UTF-16 code units)."""
        count = 0
        for ch in text:
            cp = ord(ch)
            if 0xD800 <= cp <= 0xDFFF:
                continue  # Skip lone surrogates
            count += 1
        return count

    @staticmethod
    def codepoints(text: str) -> list[int]:
        """Get all codepoints as a list of ints."""
        result: list[int] = []
        i = 0
        while i < len(text):
            cp = ord(text[i])
            if 0xD800 <= cp <= 0xDBFF and i + 1 < len(text):
                lo = ord(text[i + 1])
                if 0xDC00 <= lo <= 0xDFFF:
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
                    i += 1
            result.append(cp)
            i += 1
        return result

    @staticmethod
    def from_codepoints(cps: list[int]) -> str:
        """Convert a list of codepoints to a string."""
        return "".join(chr(cp) for cp in cps)

    # ─── Character access ─────────────────────────────────────────

    @staticmethod
    def get_at(text: str, index: int) -> int:
        """Get codepoint at character index."""
        cps = BabelString.codepoints(text)
        if 0 <= index < len(cps):
            return cps[index]
        return 0

    @staticmethod
    def get_before(text: str, index: int) -> int:
        """Get codepoint before the given index."""
        return BabelString.get_at(text, index - 1)

    @staticmethod
    def get_after(text: str, index: int) -> int:
        """Get codepoint after the given index."""
        return BabelString.get_at(text, index + 1)

    # ─── Line navigation ──────────────────────────────────────────

    @staticmethod
    def is_line_break(cp: int) -> bool:
        """Check if a codepoint is a line break."""
        return cp in (LINE_FEED, CARRIAGE_RETURN, NEXT_LINE, LINE_SEPARATOR, PARA_SEPARATOR)

    @staticmethod
    def go_start_of_line(text: str, pos: int) -> int:
        """Move position to start of current line."""
        cps = BabelString.codepoints(text)
        while pos > 0:
            if BabelString.is_line_break(cps[pos - 1]):
                break
            pos -= 1
        return pos

    @staticmethod
    def go_end_of_line(text: str, pos: int) -> int:
        """Move position to end of current line."""
        cps = BabelString.codepoints(text)
        while pos < len(cps):
            if BabelString.is_line_break(cps[pos]):
                break
            pos += 1
        return pos

    # ─── Word navigation ──────────────────────────────────────────

    @staticmethod
    def goto_next_word(text: str, pos: int) -> int:
        """Move to start of next word."""
        cps = BabelString.codepoints(text)
        n = len(cps)
        # Skip current word characters
        while pos < n and not Unicode.is_whitespace(cps[pos]):
            pos += 1
        # Skip whitespace
        while pos < n and Unicode.is_whitespace(cps[pos]):
            pos += 1
        return pos

    @staticmethod
    def goto_prev_word(text: str, pos: int) -> int:
        """Move to start of previous word."""
        cps = BabelString.codepoints(text)
        if pos <= 0:
            return 0
        # Skip whitespace
        while pos > 0 and Unicode.is_whitespace(cps[pos - 1]):
            pos -= 1
        # Skip word characters
        while pos > 0 and not Unicode.is_whitespace(cps[pos - 1]):
            pos -= 1
        return pos

    # ─── Grapheme cluster ─────────────────────────────────────────

    @staticmethod
    def goto_start_of_grapheme_cluster(text: str, pos: int) -> int:
        """Move backward to the start of the grapheme cluster at pos."""
        if pos <= 0:
            return 0
        cps = BabelString.codepoints(text)
        if pos > len(cps):
            pos = len(cps)
        i = pos - 1
        # Walk back past combining marks and extenders
        while i > 0:
            ccc = Unicode.get_canonical_combining_class(cps[i])
            if ccc == 0:
                break
            i -= 1
        return i

    @staticmethod
    def goto_end_of_grapheme_cluster(text: str, pos: int) -> int:
        """Move forward to the end of the grapheme cluster at pos."""
        cps = BabelString.codepoints(text)
        if pos >= len(cps):
            return len(cps)
        i = pos + 1
        while i < len(cps):
            ccc = Unicode.get_canonical_combining_class(cps[i])
            if ccc == 0:
                break
            i += 1
        return i

    # ─── Search ───────────────────────────────────────────────────

    @staticmethod
    def find(text: str, needle: str | int, start: int = 0) -> int:
        """Find needle in text, returning codepoint index."""
        if isinstance(needle, int):
            needle = BabelString.from_codepoints([needle])
        cps = BabelString.codepoints(text)
        needle_cps = BabelString.codepoints(needle)
        for i in range(start, len(cps) - len(needle_cps) + 1):
            if cps[i : i + len(needle_cps)] == needle_cps:
                return i
        return -1

    @staticmethod
    def compare(a: str, b: str) -> int:
        """Compare two strings by codepoint values. Returns -1, 0, or 1."""
        ca = BabelString.codepoints(a)
        cb = BabelString.codepoints(b)
        for x, y in zip(ca, cb):
            if x < y:
                return -1
            if x > y:
                return 1
        if len(ca) < len(cb):
            return -1
        if len(ca) > len(cb):
            return 1
        return 0

    # ─── Case ─────────────────────────────────────────────────────

    @staticmethod
    def make_upper(text: str) -> str:
        """Convert string to uppercase."""
        result: list[str] = []
        for cp in BabelString.codepoints(text):
            upper = Unicode.get_simple_uppercase(cp)
            result.append(chr(upper))
        return "".join(result)

    @staticmethod
    def make_lower(text: str) -> str:
        """Convert string to lowercase."""
        result: list[str] = []
        for cp in BabelString.codepoints(text):
            lower = Unicode.get_simple_lowercase(cp)
            result.append(chr(lower))
        return "".join(result)

    @staticmethod
    def make_reverse(text: str) -> str:
        """Reverse the string by codepoints."""
        cps = BabelString.codepoints(text)
        return BabelString.from_codepoints(list(reversed(cps)))

    # ─── Substring ────────────────────────────────────────────────

    @staticmethod
    def left(text: str, count: int) -> str:
        """Get the first count codepoints."""
        cps = BabelString.codepoints(text)
        return BabelString.from_codepoints(cps[:count])

    @staticmethod
    def mid(text: str, start: int, count: int = -1) -> str:
        """Get substring starting at codepoint index start."""
        cps = BabelString.codepoints(text)
        if count < 0:
            return BabelString.from_codepoints(cps[start:])
        return BabelString.from_codepoints(cps[start : start + count])

    @staticmethod
    def right(text: str, count: int) -> str:
        """Get the last count codepoints."""
        cps = BabelString.codepoints(text)
        return BabelString.from_codepoints(cps[-count:] if count <= len(cps) else cps)

    # ─── Utility ──────────────────────────────────────────────────

    @staticmethod
    def remove_duplicates(text: str) -> str:
        """Remove consecutive duplicate characters."""
        cps = BabelString.codepoints(text)
        if not cps:
            return ""
        result = [cps[0]]
        for cp in cps[1:]:
            if cp != result[-1]:
                result.append(cp)
        return BabelString.from_codepoints(result)

    @staticmethod
    def convert_ucn(text: str) -> str:
        """Convert \\uXXXX and \\UXXXXXXXX escapes in text to characters."""
        import re

        def replace_ucn(m: re.Match) -> str:
            return chr(int(m.group(1), 16))

        text = re.sub(r"\\[Uu]\+?([0-9A-Fa-f]{4,8})", replace_ucn, text)
        return text

    @staticmethod
    def convert_ncr(text: str) -> str:
        """Convert &#XXXX; and &#xXXXX; NCR escapes to characters."""
        import re

        def replace_hex_ncr(m: re.Match) -> str:
            return chr(int(m.group(1), 16))

        def replace_dec_ncr(m: re.Match) -> str:
            return chr(int(m.group(1)))

        text = re.sub(r"&#x([0-9A-Fa-f]+);", replace_hex_ncr, text)
        text = re.sub(r"&#(\d+);", replace_dec_ncr, text)
        return text

    @staticmethod
    def substitute_iteration_marks(text: str, mark_cp: int, script: int, forward: bool = True) -> str:
        """Substitute iteration marks with the preceding character."""
        cps = BabelString.codepoints(text)
        result: list[int] = []
        for i, cp in enumerate(cps):
            if cp == mark_cp and i > 0:
                result.append(cps[i - 1])
            else:
                result.append(cp)
        return BabelString.from_codepoints(result)
