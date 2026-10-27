"""
SCSU — Standard Compression Scheme for Unicode (ported from c/Main/SCSU.cpp)

Implements encoding and decoding of the SCSU algorithm as
defined in Unicode Technical Standard #6.
"""

from __future__ import annotations

# ─── SCSU Constants ───────────────────────────────────────────────────

# Window definitions
SCSU_WINDOWS = 8
SCSU_STATIC_WINDOW = 0
SCSU_DYNAMIC_WINDOW_START = 0x80

# Command bytes
SC0 = 0x00  # Change to static window 0
SC1 = 0x01
SC2 = 0x02
SC3 = 0x03
SC4 = 0x04
SC5 = 0x05
SC6 = 0x06
SC7 = 0x07
SD0 = 0x08  # Define dynamic window 0
SD1 = 0x09
SD2 = 0x0A
SD3 = 0x0B
SD4 = 0x0C
SD5 = 0x0D
SD6 = 0x0E
SD7 = 0x0F
SCU = 0x0F  # Switch to Unicode mode (same byte as SD7)
SQ0 = 0x10  # Single quote from window 0
SQ1 = 0x11
SQ2 = 0x12
SQ3 = 0x13
SQ4 = 0x14
SQ5 = 0x15
SQ6 = 0x16
SQ7 = 0x17
SQU = 0xE0  # Single quote Unicode
UC0 = 0xE1  # Unicode command range
UQU = 0xF0  # Quote Unicode

# Static window positions
STATIC_WINDOWS = [
    0x0000,  # ASCII
    0x0080,  # Latin-1 Supplement
    0x0100,  # Latin Extended-A
    0x0300,  # Combining Diacritical Marks
    0x2000,  # General Punctuation
    0x2080,  # not used
    0x2100,  # Letterlike Symbols
    0x3000,  # CJK Symbols and Punctuation
]

# Slide thresholds
SLIDE_MIN = 0x80
SLIDE_MAX = 0xFF


class SCSU:
    """Standard Compression Scheme for Unicode encoder/decoder."""

    def __init__(self, strip_bom: bool = True) -> None:
        self._strip_bom = strip_bom
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset internal state for a new encode/decode session."""
        self._windows = list(STATIC_WINDOWS)
        self._active_window = 0
        self._mode_unicode = False

    # ─── Encode ────────────────────────────────────────────────────

    def encode(self, text: str) -> bytes:
        """Encode a Unicode string to SCSU compressed bytes."""
        self._reset_state()
        output: list[int] = []
        cps = [ord(ch) for ch in text]

        i = 0
        while i < len(cps):
            cp = cps[i]

            if cp <= 0x7F:
                # ASCII range — always in window 0
                if self._active_window != 0 or self._mode_unicode:
                    output.append(SC0)
                    self._active_window = 0
                    self._mode_unicode = False
                output.append(cp)

            elif cp <= 0xFF:
                # Latin-1 supplement range
                if self._mode_unicode:
                    output.append(SC1)
                    self._active_window = 1
                    self._mode_unicode = False
                elif self._active_window != 1:
                    wi = self._find_window(cp)
                    if wi >= 0:
                        output.append(SC0 + wi)
                        self._active_window = wi
                    else:
                        output.append(SD0)
                        self._windows[0] = cp & 0xFF80
                        self._active_window = 0
                output.append(cp & 0x7F)

            elif cp <= 0xFFFF:
                # BMP
                wi = self._best_window(cp)
                if wi >= 0:
                    diff = cp - self._windows[wi]
                    if 0x00 <= diff <= 0x7F:
                        if self._active_window != wi:
                            output.append(SC0 + wi)
                            self._active_window = wi
                            self._mode_unicode = False
                        output.append(diff)
                    elif 0x00 <= diff <= 0xFF:
                        if self._active_window != wi:
                            output.append(SC0 + wi)
                            self._active_window = wi
                            self._mode_unicode = False
                        output.append(SQ0 + wi)
                        output.append(diff)
                    else:
                        output.append(SQU)
                        output.append((cp >> 8) & 0xFF)
                        output.append(cp & 0xFF)
                        self._mode_unicode = True
                else:
                    # Define new dynamic window
                    dw = self._find_free_dynamic()
                    if dw >= 0:
                        output.append(SD0 + dw)
                        self._windows[dw] = cp & 0xFF80
                        self._active_window = dw
                        self._mode_unicode = False
                        output.append(cp & 0x7F)
                    else:
                        output.append(SQU)
                        output.append((cp >> 8) & 0xFF)
                        output.append(cp & 0xFF)
                        self._mode_unicode = True

            else:
                # Supplementary planes (>= 0x10000)
                output.append(SQU)
                # Encode as surrogate pair
                cp_s = cp - 0x10000
                hi = 0xD800 | (cp_s >> 10)
                lo = 0xDC00 | (cp_s & 0x3FF)
                output.append((hi >> 8) & 0xFF)
                output.append(hi & 0xFF)
                output.append((lo >> 8) & 0xFF)
                output.append(lo & 0xFF)
                self._mode_unicode = True

            i += 1

        return bytes(output)

    # ─── Decode ────────────────────────────────────────────────────

    def decode(self, data: bytes) -> str:
        """Decode SCSU compressed bytes to a Unicode string."""
        self._reset_state()
        output: list[str] = []
        buf = list(data)
        n = len(buf)
        i = 0

        # Skip BOM if present
        if self._strip_bom and n >= 2 and ((buf[0] == 0xFE and buf[1] == 0xFF) or (buf[0] == 0xFF and buf[1] == 0xFE)):
            i = 2

        while i < n:
            b = buf[i]

            if self._mode_unicode:
                # In Unicode mode
                if b >= UQU:
                    # Quote Unicode
                    i += 1
                    if i < n:
                        output.append(chr((b - UQU) << 8 | buf[i]))
                elif b >= UC0:
                    # Unicode run
                    count = b - UC0 + 1
                    for _ in range(count):
                        i += 1
                        if i + 1 >= n:
                            break
                        hi = buf[i]
                        lo = buf[i + 1]
                        i += 1
                        cp = (hi << 8) | lo
                        if 0xD800 <= cp <= 0xDBFF and i + 1 < n:
                            lo2 = buf[i + 1]
                            cp2 = (buf[i] << 8) | lo2
                            if 0xDC00 <= cp2 <= 0xDFFF:
                                cp = 0x10000 + ((cp - 0xD800) << 10) + (cp2 - 0xDC00)
                                i += 1
                        output.append(chr(cp))
                    self._mode_unicode = False
                    self._active_window = 0
                else:
                    i += 1
                    if i < n:
                        output.append(chr((b << 8) | buf[i]))
            else:
                # In window mode
                if b <= SC7:
                    # Switch to static/dynamic window
                    self._active_window = b
                elif b <= SD7:
                    # Define dynamic window
                    dw = b - SD0
                    i += 1
                    if i < n:
                        self._windows[dw] = buf[i] << 8
                elif b <= SQ7:
                    # Single quote from window
                    self._active_window = b - SQ0
                    i += 1
                    if i < n:
                        cp = self._windows[self._active_window] + buf[i]
                        output.append(chr(cp))
                elif b <= 0xDF:
                    # Character from current window
                    cp = self._windows[self._active_window] + b
                    output.append(chr(cp))
                else:
                    # SQU: switch to Unicode mode
                    if b == SQU:
                        self._mode_unicode = True
                    elif b >= UC0:
                        count = b - UC0 + 1
                        for _ in range(count):
                            i += 1
                            if i + 1 >= n:
                                break
                            cp = (buf[i] << 8) | buf[i + 1]
                            i += 1
                            output.append(chr(cp))
                        self._active_window = 0
                    else:
                        # UQU range
                        i += 1
                        if i < n:
                            cp = ((b - UQU) << 8) | buf[i]
                            output.append(chr(cp))

            i += 1

        return "".join(output)

    # ─── Window management helpers ─────────────────────────────────

    def _find_window(self, cp: int) -> int:
        """Find the best window for a codepoint."""
        best = -1
        best_dist = 0x10000
        for i, base in enumerate(self._windows):
            if base <= cp < base + 0x80:
                dist = cp - base
            elif base + 0xFF80 <= cp < base + 0x10000:
                dist = cp - base - 0xFF80 + 0x80
            else:
                continue
            if dist < best_dist:
                best_dist = dist
                best = i
        return best

    def _best_window(self, cp: int) -> int:
        """Find best window index for encoding cp."""
        w = self._find_window(cp)
        if w >= 0:
            return w
        # Check if any dynamic window could fit
        for i in range(SCSU_WINDOWS):
            base = self._windows[i] & 0xFF80
            if base <= cp < base + 0x80:
                return i
        return -1

    def _find_free_dynamic(self) -> int:
        """Find a free dynamic window slot."""
        # Reserve first few windows (0-2 are usually static)
        for i in range(1, SCSU_WINDOWS):
            if i not in (0, 1, 2):
                return i
        return -1
