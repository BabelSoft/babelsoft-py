"""
Language base module - Python equivalent of c/Languages/Language.h and Language.cpp

Provides the base Language class and enums used by all language-specific
input method and conversion classes.
"""

from enum import Enum, auto


class EInput(Enum):
    """Input processing result codes (equivalent to C++ EInput enum)."""

    OK = auto()
    NULL = auto()
    IGNORE = auto()
    INVALID = auto()
    INVALID_CLEAR = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()
    FINISHED_REDO = auto()
    FINISHED_IGNORE = auto()
    FINISHED_IN_PROGRESS = auto()
    CHARACTER_CLEAR = auto()
    CHARACTER = auto()
    CHAR32 = auto()
    CLEAR = auto()
    CLEAR_IN_PROGRESS = auto()
    BACKSPACE = auto()
    BACKSPACE_REDO = auto()
    SHAD = auto()
    RETURN = auto()


class ELanguage(Enum):
    """Enumeration of supported languages."""

    DEFAULT = 0
    UNICODE = 1
    MANCHU = 2
    MONGOLIAN = 3
    TIBETAN = 4
    UYGHUR = 5
    YI = 6
    END = 7


# Constants
FIRST_LANGUAGE_INDEX = ELanguage.TIBETAN
CASE_OFFSET = 0x0020
MAX_MONGOLIAN_WORD = 128
MAX_NAME = 24
FF_16 = 0xFFFF
ZERO_16 = 0x0000
ZERO_32 = 0x00000000


class Language:
    """
    Base class for all language input method processors.

    This is the Python equivalent of the C++ Language class. It provides:
    - Character-by-character input processing via OnChar/OnInput
    - Escape sequence handling (\\uXXXX, \\UXXXXXXXX)
    - Backspace, return, and number handling
    - Output string accumulation

    Subclasses must implement OnInput().
    """

    def __init__(self, block_start: int = 0, block_end: int = 0, unicode_block: int = 0):
        self.ch_block_start = block_start
        self.ch_block_end = block_end
        self.ch_block_range = block_end - block_start
        self.unicode_block = unicode_block
        self.ch_output = ZERO_32
        self.str_output = ""

        # Escape sequence state
        self._escape = False
        self._slash = False
        self._escape_char = ZERO_32
        self._escape_digits = 4
        self._escape_count = 0
        self._bracket_count = 0

        # Input state
        self._step = 0
        self._previous_input = ZERO_16
        self._ignore_text = False
        self._other_lang = False

    # --- Public API ---

    def get_output_string(self) -> str:
        """Get accumulated output string."""
        return self.str_output

    def get_character(self) -> int:
        """Get the current output character (as Unicode code point)."""
        return self.ch_output

    def on_clear(self, reset: bool = False) -> None:
        """Clear input state. If reset=True, also clears escape/bracket state."""
        self._step = 0
        self._previous_input = ZERO_16
        self.ch_output = ZERO_32

        if reset:
            self._escape_char = ZERO_32
            self._escape_digits = 4
            self._escape_count = 0
            self._slash = False
            self._ignore_text = False
            self._other_lang = False
            self._bracket_count = 0

    def on_char(self, ch: str) -> EInput:
        """
        Process a single character input.

        Args:
            ch: A single character string.

        Returns:
            EInput result code indicating how the character was handled.
        """
        if not ch:
            return EInput.NULL

        code = ord(ch)

        # Process any in-progress escape sequence
        if self._escape:
            if self._escape_count:
                return self._on_escape_sequence(code)

            if self._slash:
                self._slash = False
                self._escape_char = ZERO_32

                if ch == "u":
                    self._escape_digits = 4
                    self._escape_count = 1
                    return EInput.IN_PROGRESS
                elif ch == "U":
                    self._escape_digits = 8
                    self._escape_count = 1
                    return EInput.IN_PROGRESS
                else:
                    self._escape_count = 0
                    return EInput.CLEAR

            # Check for backslash (escape character)
            if code == 0x005C:
                self._slash = True
                self._escape_count = 0
                return EInput.FINISHED_IN_PROGRESS

        # Pre-process special characters at step 0
        if self._step == 0:
            if code in (0x1B, 0x08, 0x0D, 0x09, 0x20):
                return self._on_ignorable(code)

            if 0x30 <= code <= 0x39:
                result = self._on_number(code)
                if result != EInput.NULL:
                    return result

        # Handle backspace, escape, return
        if code == 0x08:  # Backspace
            return self._on_backspace(code)
        if code == 0x1B:  # Escape
            self.on_clear()
            return EInput.CLEAR
        if code == 0x0D:  # Return
            return self._on_return()

        result = self.on_input(code)

        if result == EInput.IN_PROGRESS:
            self._previous_input = code
        elif result == EInput.FINISHED:
            self._previous_input = ZERO_16

        return result

    def on_text(self, text: str) -> EInput:
        """
        Process a string of text character by character.

        Args:
            text: Input text string.

        Returns:
            EInput result from the last character processed.
        """
        self.on_clear()
        result = EInput.NULL
        for ch in text:
            result = self.on_char(ch)
        return result

    # --- Subclass overridable methods ---

    def on_input(self, code: int) -> EInput:
        """
        Process a single character code. MUST be overridden by subclasses.

        Args:
            code: Unicode code point of the input character.

        Returns:
            EInput result code.
        """
        raise NotImplementedError("Subclasses must implement on_input()")

    def on_menu(self, menu_id: int, convert_str: str = "") -> EInput:
        """Handle menu commands. Default returns CLEAR."""
        return EInput.CLEAR

    def do_conversion(
        self,
        menu_id: int,
        text_in: str,
        text_out: list,
        start: int,
        end: int,
        count1: list,
        count2: list,
        skip_ascii: bool = False,
    ) -> int:
        """
        Perform a conversion operation. Override in subclass.

        Returns:
            Number of characters output.
        """
        return 0

    # --- Protected methods ---

    def _on_backspace(self, code: int) -> EInput:
        return EInput.BACKSPACE_REDO

    def _on_number(self, code: int) -> EInput:
        return EInput.CHARACTER

    def _on_ignorable(self, code: int) -> EInput:
        return EInput.IGNORE

    def _on_return(self) -> EInput:
        self.on_clear()
        return EInput.RETURN

    def _on_finish(self) -> None:
        """Called when input is finished. Override in subclass."""
        pass

    def _on_escape_sequence(self, code: int) -> EInput:
        """Process hex digits in \\uXXXX or \\UXXXXXXXX sequences."""
        hex_digit = None
        if 0x30 <= code <= 0x39:
            hex_digit = code - 0x30
        elif 0x41 <= code <= 0x46:
            hex_digit = code - 0x41 + 10
        elif 0x61 <= code <= 0x66:
            hex_digit = code - 0x61 + 10

        if hex_digit is not None:
            self._escape_char = (self._escape_char << 4) | hex_digit
            if self._escape_count >= self._escape_digits:
                self._escape_count = 0
                try:
                    self.ch_output = self._escape_char
                    return EInput.CHAR32
                except ValueError:
                    return EInput.INVALID
            self._escape_count += 1
            return EInput.IN_PROGRESS

        # Not a valid hex digit
        self._escape_count = 0
        return EInput.INVALID
