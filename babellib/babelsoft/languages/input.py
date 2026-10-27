"""
TextInput - Python equivalent of c/Languages/TextInput.h/.cpp

Manages custom text input methods (.tim files) for BabelPad.
Handles loading, candidate list management, deadkey support,
and character-to-Unicode mapping via custom keyboard tables.
"""

from enum import Enum, auto


class InputType(Enum):
    """Text input result codes."""

    RESULT = auto()
    CLEAR = auto()
    IGNORE = auto()
    PENDING = auto()
    INVALID = auto()
    UNHANDLED = auto()
    UNMAPPED = auto()
    DEADKEY_PENDING = auto()
    DEADKEY_INVALID = auto()
    SHIFTKEY_PENDING = auto()


class StatusType(Enum):
    """Text input table status."""

    PENDING = 0
    LOADED = 1
    FAILED = 2
    MISSING = 3
    INVALID_FORMAT = 4
    INVALID_ENTRIES = 5


class InputMethod:
    """Represents a single text input method configuration."""

    def __init__(self, name: str = "", path: str = ""):
        self.name = name
        self.path = path


class InputTable:
    """Internal table data for a text input method."""

    def __init__(self):
        self.method = InputMethod()
        self.status = StatusType.PENDING
        self.entries: dict = {}  # key_code -> str mapping
        self.deadkeys: dict = {}  # deadkey_maps
        self.first_chars: list = []


class Input:
    """
    Custom text input method manager.

    Manages loading and using custom keyboard layout tables (.tim files)
    for text input in BabelPad. Supports dead keys, shift keys,
    candidate lists, and multi-character input sequences.

    This is a simplified Python implementation focusing on the core API.
    """

    FIRST_CHARS = 64
    MAX_DEADKEYS = 3

    def __init__(self):
        self._tables: list[InputTable] = []
        self._current_method: int = -1
        self._candidate_list: list[int] = []
        self._candidate_offset: int = 0
        self._candidate_count: int = 0
        self._deadkey_pending: bool = False
        self._shift_next: bool = False
        self._deadkey_buffer: list[int] = []

    # --- Properties ---

    @property
    def input_count(self) -> int:
        """Get number of loaded input methods."""
        return len(self._tables)

    @property
    def current_method(self) -> int:
        """Get current input method index."""
        return self._current_method

    @property
    def is_empty(self) -> bool:
        """Check if candidate list is empty."""
        return self._candidate_count == 0

    @property
    def candidate_count(self) -> int:
        """Get current candidate count."""
        return self._candidate_count

    @property
    def candidate_list(self) -> list[int]:
        """Get the candidate list (Unicode code points)."""
        return self._candidate_list[: self._candidate_count]

    @property
    def is_deadkey(self) -> bool:
        """Check if deadkey is pending."""
        return self._deadkey_pending

    @property
    def is_shiftkey(self) -> bool:
        """Check if shift-next mode is active."""
        return self._shift_next

    # --- Table Management ---

    def get_status(self, index: int) -> StatusType:
        """Get status of a text input table."""
        if 0 <= index < len(self._tables):
            return self._tables[index].status
        return StatusType.MISSING

    def get_name(self, index: int) -> str:
        """Get name of a text input method."""
        if 0 <= index < len(self._tables):
            return self._tables[index].method.name
        return ""

    def get_file_path(self, index: int) -> str:
        """Get file path of a text input method table."""
        if 0 <= index < len(self._tables):
            return self._tables[index].method.path
        return ""

    def is_loaded(self, index: int) -> bool:
        """Check if a text input method is loaded."""
        if 0 <= index < len(self._tables):
            return self._tables[index].status == StatusType.LOADED
        return False

    def is_selected(self, index: int) -> bool:
        """Check if this is the currently selected method."""
        return index == self._current_method

    # --- Load/Reload Methods ---

    def load_methods(self) -> None:
        """Load all text input methods from configured directories."""
        # In the full implementation, this would scan directories
        # for .tim files and load them

    def reload_methods(self) -> None:
        """Reload all text input methods."""
        self._tables.clear()
        self.load_methods()

    def reload_method(self, index: int) -> None:
        """Reload a specific text input method."""
        if 0 <= index < len(self._tables):
            self._tables[index].status = StatusType.PENDING
            # Reload logic would go here

    def delete_method(self, index: int) -> None:
        """Delete a text input method."""
        if 0 <= index < len(self._tables):
            del self._tables[index]
            if self._current_method >= len(self._tables):
                self._current_method = len(self._tables) - 1

    def add_method(self, method: InputMethod, load_tables: bool = True) -> None:
        """Add a new text input method."""
        table = InputTable()
        table.method = method
        self._tables.append(table)
        if load_tables:
            self.reload_method(len(self._tables) - 1)

    def modify_method(self, index: int, method: InputMethod) -> None:
        """Modify an existing text input method."""
        if 0 <= index < len(self._tables):
            self._tables[index].method = method

    def move_method(self, index: int, up: bool) -> None:
        """Move a text input method up or down in the list."""
        if up and index > 0:
            self._tables[index], self._tables[index - 1] = self._tables[index - 1], self._tables[index]
            if self._current_method == index:
                self._current_method -= 1
        elif not up and index < len(self._tables) - 1:
            self._tables[index], self._tables[index + 1] = self._tables[index + 1], self._tables[index]
            if self._current_method == index:
                self._current_method += 1

    def set_method(self, index: int) -> StatusType:
        """Set the active text input method."""
        if 0 <= index < len(self._tables):
            self._current_method = index
            self.on_clear()
            return self._tables[index].status
        return StatusType.MISSING

    # --- Input Processing ---

    def on_clear(self) -> None:
        """Clear input state."""
        self._candidate_list.clear()
        self._candidate_count = 0
        self._candidate_offset = 0
        self._deadkey_pending = False
        self._shift_next = False
        self._deadkey_buffer.clear()

    def on_character_input(self, code: int, ctrl_alt: bool = False) -> InputType:
        """
        Process a character input through the current input method.

        Args:
            code: Unicode code point of input character.
            ctrl_alt: Whether Ctrl+Alt modifier is pressed.

        Returns:
            ETextInput result code.
        """
        if self._current_method < 0 or self._current_method >= len(self._tables):
            return InputType.UNMAPPED

        table = self._tables[self._current_method]
        if table.status != StatusType.LOADED:
            return InputType.UNMAPPED

        # Handle deadkey state
        if self._deadkey_pending:
            return self._process_deadkey(code)

        # Look up in table
        ch = chr(code) if code < 0x110000 else ""
        if ch in table.entries:
            result_str = table.entries[ch]
            if len(result_str) == 1:
                # Single character result
                self.on_clear()
                return InputType.RESULT
            else:
                # Multi-character: generate candidates
                self._candidate_list = [ord(c) for c in result_str]
                self._candidate_count = len(self._candidate_list)
                return InputType.PENDING

        return InputType.UNMAPPED

    def _process_deadkey(self, code: int) -> InputType:
        """Resolve a pending deadkey with the next input character.

        ``InputTable.deadkeys`` maps a key sequence — the deadkey plus every
        character typed after it — to the text that sequence produces, so the
        longest match wins: a sequence that is only a prefix of a longer one
        keeps the deadkey pending (:attr:`InputType.DEADKEY_PENDING`), a
        complete one yields :attr:`InputType.RESULT` (or a candidate list,
        :attr:`InputType.PENDING`), and anything else aborts the sequence.
        """
        if self._current_method < 0 or self._current_method >= len(self._tables):
            self.clear_deadkey()
            return InputType.UNMAPPED

        table = self._tables[self._current_method]
        deadkeys = table.deadkeys or {}
        if len(self._deadkey_buffer) >= self.MAX_DEADKEYS:
            self.clear_deadkey()
            return InputType.DEADKEY_INVALID

        self._deadkey_buffer.append(code)
        sequence = tuple(self._deadkey_buffer)

        result_str = deadkeys.get(sequence)
        if result_str is None:
            if any(key[: len(sequence)] == sequence for key in deadkeys):
                self._deadkey_pending = True
                return InputType.DEADKEY_PENDING
            self.clear_deadkey()
            return InputType.DEADKEY_INVALID

        self.clear_deadkey()
        if len(result_str) == 1:
            return InputType.RESULT

        self._candidate_list = [ord(c) for c in result_str]
        self._candidate_count = len(self._candidate_list)
        self._candidate_offset = 0
        return InputType.PENDING

    def clear_deadkey(self) -> None:
        """Clear pending deadkey state."""
        self._deadkey_pending = False
        self._deadkey_buffer.clear()

    # --- Candidate List Management ---

    def set_candidate_offset(self, offset: int) -> None:
        """Set the candidate list page offset."""
        self._candidate_offset = offset

    def get_candidate_result(self, candidate: int) -> str:
        """Get the result string for selecting a candidate."""
        if 0 <= candidate < self._candidate_count:
            cp = self._candidate_list[candidate]
            return chr(cp)
        return ""
