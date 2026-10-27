"""
BabelString — Unicode string utilities (ported from c/Main/BabelString.h)

Provides character-level string operations: iteration by codepoint/grapheme,
line navigation, word navigation, case mapping, search, and conversion.
"""

from __future__ import annotations

from babelsoft.unicode.core import Unicode

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
        pos = min(pos, len(cps))
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

    # ─── Cursor movement ──────────────────────────────────────────

    @staticmethod
    def go_left(text: str, pos: int) -> int:
        """Move cursor one codepoint to the left. Returns new position."""
        if pos <= 0:
            return 0
        # Convert from codepoint position to codepoint index and back
        cp_index = BabelString._codepoint_position(text, pos)
        return max(0, BabelString._byte_position(text, cp_index - 1))

    @staticmethod
    def go_right(text: str, pos: int) -> int:
        """Move cursor one codepoint to the right. Returns new position."""
        cp_index = BabelString._codepoint_position(text, pos)
        return min(len(text), BabelString._byte_position(text, cp_index + 1))

    @staticmethod
    def go_up(text: str, pos: int) -> int:
        """Move to equivalent position on previous line. Returns new position."""
        line_start = BabelString.go_start_of_line(text, pos)
        if line_start == 0:
            return 0
        prev_line_start = BabelString.go_start_of_line(text, line_start - 1)
        offset = pos - line_start
        return min(prev_line_start + offset, max(0, line_start - 1))

    @staticmethod
    def go_down(text: str, pos: int) -> int:
        """Move to equivalent position on next line. Returns new position."""
        cps = BabelString.codepoints(text)
        line_end = BabelString.go_end_of_line(text, pos)
        if line_end >= len(cps):
            return len(text)
        next_line_end = BabelString.go_end_of_line(text, line_end + 1)
        offset = pos - BabelString.go_start_of_line(text, pos)
        next_start = line_end + 1
        return min(next_start + offset, next_line_end)

    # ─── Backspace and delete ─────────────────────────────────────

    @staticmethod
    def backspace(text: str, pos: int) -> tuple[str, int]:
        """Delete the codepoint before pos. Returns (new_text, new_pos)."""
        if pos <= 0:
            return text, 0
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        if cp_index <= 0:
            return text, 0
        new_cps = cps[: cp_index - 1] + cps[cp_index:]
        new_text = BabelString.from_codepoints(new_cps)
        new_pos = BabelString._byte_position(text, cp_index - 1)
        return new_text, new_pos

    @staticmethod
    def delete_at(text: str, pos: int, count: int = 1) -> str:
        """Delete count codepoints starting at pos. Returns new text."""
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        if cp_index >= len(cps):
            return text
        new_cps = cps[:cp_index] + cps[cp_index + count :]
        return BabelString.from_codepoints(new_cps)

    @staticmethod
    def delete_line_break(text: str, pos: int, before: bool = True) -> tuple[str, int, int]:
        """Delete a line break character near pos. Returns (new_text, new_pos, length_deleted)."""
        cps = BabelString.codepoints(text)
        if before:
            if pos > 0 and BabelString.is_line_break(cps[pos - 1]):
                new_cps = cps[: pos - 1] + cps[pos:]
                return BabelString.from_codepoints(new_cps), pos - 1, 1
            # Handle CR+LF pair
            if pos > 1 and cps[pos - 1] == LINE_FEED and cps[pos - 2] == CARRIAGE_RETURN:
                new_cps = cps[: pos - 2] + cps[pos:]
                return BabelString.from_codepoints(new_cps), pos - 2, 2
        else:
            if pos < len(cps) and BabelString.is_line_break(cps[pos]):
                new_cps = cps[:pos] + cps[pos + 1 :]
                return BabelString.from_codepoints(new_cps), pos, 1
            if pos + 1 < len(cps) and cps[pos] == CARRIAGE_RETURN and cps[pos + 1] == LINE_FEED:
                new_cps = cps[:pos] + cps[pos + 2 :]
                return BabelString.from_codepoints(new_cps), pos, 2
        return text, pos, 0

    # ─── Character access ─────────────────────────────────────────

    @staticmethod
    def get16_at(text: str, pos: int) -> int:
        """Get the UTF-16 code unit at byte position pos."""
        if 0 <= pos < len(text):
            return ord(text[pos])
        return 0

    @staticmethod
    def get32_at(text: str, pos: int) -> int:
        """Get the full 32-bit codepoint at byte position pos."""
        if pos < 0 or pos >= len(text):
            return 0
        cp = ord(text[pos])
        if 0xD800 <= cp <= 0xDBFF and pos + 1 < len(text):
            lo = ord(text[pos + 1])
            if 0xDC00 <= lo <= 0xDFFF:
                return 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
        return cp

    @staticmethod
    def peek_at(text: str, pos: int) -> int:
        """Peek at the codepoint at the given index (like array access)."""
        cps = BabelString.codepoints(text)
        if 0 <= pos < len(cps):
            return cps[pos]
        return 0

    @staticmethod
    def get_safe_at(text: str, pos: int) -> tuple[int, int]:
        """Get codepoint at pos, advancing pos past it. Returns (cp, new_pos)."""
        if pos >= len(text):
            return 0, pos
        cp = ord(text[pos])
        if 0xD800 <= cp <= 0xDBFF and pos + 1 < len(text):
            lo = ord(text[pos + 1])
            if 0xDC00 <= lo <= 0xDFFF:
                return 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00), pos + 2
        return cp, pos + 1

    # ─── Length and counting ─────────────────────────────────────

    @staticmethod
    def get_length(text: str, pos: int = -1) -> int:
        """Get codepoint length of text."""
        if pos >= 0:
            return len(BabelString.codepoints(text[:pos]))
        return len(BabelString.codepoints(text))

    @staticmethod
    def get_bytes(text: str) -> int:
        """Get number of UTF-16 code units (Python len)."""
        return len(text)

    @staticmethod
    def advance_characters(text: str, start: int, end: int, advance: int) -> int:
        """Return position advanced by advance codepoints from start, clamped to [start, end]."""
        target = BabelString._codepoint_position(text, start) + advance
        return max(0, min(end, BabelString._byte_position(text, target)))

    @staticmethod
    def count(text: str, needle: str | int, start: int = 0, end: int = -1) -> int:
        """Count occurrences of needle (codepoint or string) in text."""
        if isinstance(needle, int):
            needle = BabelString.from_codepoints([needle])
        cps = BabelString.codepoints(text)
        ncps = BabelString.codepoints(needle)
        if end < 0:
            end = len(cps)
        count = 0
        for i in range(start, min(end, len(cps) - len(ncps) + 1)):
            if cps[i : i + len(ncps)] == ncps:
                count += 1
        return count

    # ─── Modification ─────────────────────────────────────────────

    @staticmethod
    def set_at(text: str, pos: int, ch: int) -> str:
        """Replace the codepoint at pos with ch. Returns new string."""
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        if 0 <= cp_index < len(cps):
            cps[cp_index] = ch
        return BabelString.from_codepoints(cps)

    @staticmethod
    def replace_at(text: str, pos: int, ch1: int, ch2: int = 0) -> str:
        """Replace codepoint(s) at pos with ch1 (and optionally ch2). Returns new string."""
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        if 0 <= cp_index < len(cps):
            if ch2:
                cps[cp_index : cp_index + 1] = [ch1, ch2]
            else:
                cps[cp_index] = ch1
        return BabelString.from_codepoints(cps)

    @staticmethod
    def insert_at(text: str, pos: int, insert: str | int) -> str:
        """Insert a string or codepoint at pos. Returns new string."""
        if isinstance(insert, int):
            insert = BabelString.from_codepoints([insert])
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        icps = BabelString.codepoints(insert)
        new_cps = cps[:cp_index] + icps + cps[cp_index:]
        return BabelString.from_codepoints(new_cps)

    @staticmethod
    def insert_unique_in_order(text: str, ch: int) -> str:
        """Insert ch in sorted order if not already present. Returns new string."""
        cps = BabelString.codepoints(text)
        if ch in cps:
            return text
        cps.append(ch)
        cps.sort()
        return BabelString.from_codepoints(cps)

    @staticmethod
    def remove(text: str, remove_ch: int) -> str:
        """Remove all occurrences of remove_ch from text."""
        cps = [cp for cp in BabelString.codepoints(text) if cp != remove_ch]
        return BabelString.from_codepoints(cps)

    @staticmethod
    def replace(text: str, old_ch: int, new_ch: int) -> str:
        """Replace all occurrences of old_ch with new_ch."""
        cps = [new_ch if cp == old_ch else cp for cp in BabelString.codepoints(text)]
        return BabelString.from_codepoints(cps)

    @staticmethod
    def remove_trailing_whitespace(text: str) -> str:
        """Remove trailing whitespace from text."""
        cps = BabelString.codepoints(text)
        while cps and Unicode.is_whitespace(cps[-1]):
            cps.pop()
        return BabelString.from_codepoints(cps)

    # ─── Case (non-mutating) ─────────────────────────────────────

    @staticmethod
    def to_upper(text: str) -> str:
        """Return uppercase copy of text (non-mutating)."""
        return BabelString.make_upper(text)

    @staticmethod
    def to_lower(text: str) -> str:
        """Return lowercase copy of text (non-mutating)."""
        return BabelString.make_lower(text)

    # ─── Search ───────────────────────────────────────────────────

    @staticmethod
    def find_string(text: str, needle: str, start: int = 0) -> int:
        """Find needle in text starting at start. Returns codepoint position or -1."""
        cps = BabelString.codepoints(text)
        ncps = BabelString.codepoints(needle)
        if not ncps:
            return start if start < len(cps) else -1
        for i in range(start, len(cps) - len(ncps) + 1):
            if cps[i : i + len(ncps)] == ncps:
                return i
        return -1

    @staticmethod
    def find_string_reverse(text: str, needle: str, start: int = -1) -> int:
        """Find needle searching backwards from start. Returns codepoint position or -1."""
        cps = BabelString.codepoints(text)
        ncps = BabelString.codepoints(needle)
        if start < 0:
            start = len(cps) - 1
        for i in range(min(start, len(cps) - len(ncps)), -1, -1):
            if cps[i : i + len(ncps)] == ncps:
                return i
        return -1

    @staticmethod
    def find_case_folded_string(text: str, needle: str, start: int = 0) -> int:
        """Case-folded version of find_string."""
        return BabelString.find_string(text.casefold(), needle.casefold(), start)

    @staticmethod
    def is_start_of_line(text: str, needle: str, pos: int = 0) -> bool:
        """Check if needle matches the start of a line at pos."""
        cps = BabelString.codepoints(text)
        ncps = BabelString.codepoints(needle)
        if pos == 0 or BabelString.is_line_break(cps[pos - 1]):
            return cps[pos : pos + len(ncps)] == ncps
        return False

    @staticmethod
    def is_same(a: str, b: str) -> bool:
        """Check if two strings are identical."""
        return a == b

    @staticmethod
    def is_same_wild(target: str, pattern: str, match_start: bool = False) -> bool:
        """Wildcard pattern match. Uses WILDCARD_ONE (0xFFFE) and WILDCARD_ANY (0xFFFF)."""
        WILD_ONE = chr(0xFFFE)
        WILD_ANY = chr(0xFFFF)
        import re

        regex_parts = []
        for ch in pattern:
            if ch == WILD_ONE:
                regex_parts.append(".")
            elif ch == WILD_ANY:
                regex_parts.append(".*")
            else:
                regex_parts.append(re.escape(ch))
        regex = "".join(regex_parts)
        if match_start:
            regex = "^" + regex
        return re.fullmatch(regex, target) is not None

    @staticmethod
    def is_match(a: str, b: str, start1: int = 0, start2: int = 0, len1: int = -1, len2: int = -1) -> bool:
        """Compare substrings of a and b for equality."""
        cps1 = BabelString.codepoints(a)[start1 : start1 + len1 if len1 >= 0 else None]
        cps2 = BabelString.codepoints(b)[start2 : start2 + len2 if len2 >= 0 else None]
        return cps1 == cps2

    # ─── String appending and assignment ─────────────────────────

    @staticmethod
    def append(text: str, ch: int) -> str:
        """Append a codepoint to text. Returns new string."""
        return text + BabelString.from_codepoints([ch])

    @staticmethod
    def append_string(text: str, other: str, newline: bool = False) -> str:
        """Append one string to another, optionally with a newline."""
        if newline and text and not text.endswith("\n"):
            return text + "\n" + other
        return text + other

    @staticmethod
    def assign_scalar(ch: int) -> str:
        """Create a string from a single scalar codepoint."""
        return BabelString.from_codepoints([ch])

    # ─── Selection ────────────────────────────────────────────────

    @staticmethod
    def select_word(text: str, pos: int) -> tuple[int, int]:
        """Get start and end positions of the word at pos. Returns (start, end)."""
        cps = BabelString.codepoints(text)
        if pos >= len(cps):
            return pos, pos
        cp_index = BabelString._codepoint_position(text, pos)
        start = cp_index
        while start > 0 and not Unicode.is_whitespace(cps[start - 1]):
            start -= 1
        end = cp_index
        while end < len(cps) and not Unicode.is_whitespace(cps[end]):
            end += 1
        return start, end

    @staticmethod
    def get_next_word(text: str, pos: int) -> tuple[str, int, int]:
        """Get the next word from pos. Returns (word, word_len, new_pos)."""
        cps = BabelString.codepoints(text)
        cp_index = BabelString._codepoint_position(text, pos)
        # Skip whitespace
        while cp_index < len(cps) and Unicode.is_whitespace(cps[cp_index]):
            cp_index += 1
        start = cp_index
        while cp_index < len(cps) and not Unicode.is_whitespace(cps[cp_index]):
            cp_index += 1
        word_cps = cps[start:cp_index]
        return BabelString.from_codepoints(word_cps), len(word_cps), cp_index

    # ─── Conversion ───────────────────────────────────────────────

    @staticmethod
    def string_to_integer(text: str) -> int:
        """Parse a string as an integer. Returns 0 on failure."""
        try:
            return int(text.strip())
        except ValueError:
            return 0

    @staticmethod
    def hex_string_to_unicode(text: str) -> int:
        """Parse a hex string as a Unicode codepoint. Returns 0 on failure."""
        try:
            return int(text.strip(), 16)
        except ValueError:
            return 0

    @staticmethod
    def add_comma(value: int | str) -> str:
        """Format number with comma separators."""
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                return str(value)
        return f"{value:,}"

    @staticmethod
    def extract_para(text: str, start_pos: int) -> tuple[str, int, int, int]:
        """Extract a paragraph starting at start_pos.
        Returns (paragraph_text, new_start, new_end, para_length_in_codepoints).
        """
        cps = BabelString.codepoints(text)
        # Find paragraph boundaries
        para_start = start_pos
        while para_start > 0 and not (
            cps[para_start - 1] == PARA_SEPARATOR
            or (para_start > 1 and cps[para_start - 2] == CARRIAGE_RETURN and cps[para_start - 1] == LINE_FEED)
        ):
            para_start -= 1

        para_end = start_pos
        while para_end < len(cps) and cps[para_end] not in (PARA_SEPARATOR, LINE_FEED):
            para_end += 1

        para_cps = cps[para_start:para_end]
        return BabelString.from_codepoints(para_cps), para_start, para_end, len(para_cps)

    # ─── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _codepoint_position(text: str, byte_pos: int) -> int:
        """Convert byte position to codepoint index."""
        if byte_pos <= 0:
            return 0
        count = 0
        i = 0
        while i < byte_pos and i < len(text):
            cp = ord(text[i])
            if 0xD800 <= cp <= 0xDBFF and i + 1 < len(text) and 0xDC00 <= ord(text[i + 1]) <= 0xDFFF:
                i += 2
            else:
                i += 1
            count += 1
        return count

    @staticmethod
    def _byte_position(text: str, cp_index: int) -> int:
        """Convert codepoint index to byte position."""
        if cp_index <= 0:
            return 0
        count = 0
        pos = 0
        while count < cp_index and pos < len(text):
            cp = ord(text[pos])
            if 0xD800 <= cp <= 0xDBFF and pos + 1 < len(text) and 0xDC00 <= ord(text[pos + 1]) <= 0xDFFF:
                pos += 2
            else:
                pos += 1
            count += 1
        return pos
