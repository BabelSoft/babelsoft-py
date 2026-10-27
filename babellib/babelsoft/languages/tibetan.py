"""
LanguageTibetan - Python equivalent of c/Languages/LanguageTibetan.h/.cpp

Handles Tibetan script input via Extended Wylie transliteration.
Converts Wylie transliteration to Tibetan Unicode characters.

The Tibetan script uses a complex syllabic structure:
  prefix + superfix + stem (+ subjoined stems) + vowel + final(s) + punctuation
"""

from typing import ClassVar

from babelsoft.utils_.loader import ScriptsLoader

from .class_ import ZERO_16, EInput, Language

# Tibetan Unicode block constants
TIBETAN_BASE = 0x0F00
TIBETAN_DIGITS = 0x0F20
TIBETAN_HALVES = 0x0F2A
TIBETAN_SUBJOIN_OFFSET = 0x50

# Prefix bit flags
PREFIX_X = 0x00
PREFIX_G = 0x01
PREFIX_D = 0x02
PREFIX_B = 0x04
PREFIX_M = 0x08
PREFIX_Q = 0x10
PREFIX_MASK = 0x1F
SUBFIX1_X = 0x00
SUBFIX1_W = 0x01
SUBFIX1_Y = 0x02
SUBFIX1_R = 0x04
SUBFIX1_L = 0x08
SUBFIX2_X = 0x00
SUBFIX2_W = 0x10
SUBFIX2_Y = 0x20
SUBFIX2_R = 0x40
SUBFIX2_L = 0x80

# Superfix bit flags
SUPERFIX_X = 0x00
SUPERFIX_R = 0x20
SUPERFIX_L = 0x40
SUPERFIX_S = 0x80
SUPERFIX_MASK = 0xE0

# TSA PHRU mask
TSA_PHRU_MASK = 0xF000

# data/scripts/tibetan.tsv spells the masks as the Tibetan letters they put in
# the syllable; these maps turn those letters back into the bit flags above.
_PREFIX_CHARACTERS = {
    "\u0f42": PREFIX_G,
    "\u0f51": PREFIX_D,
    "\u0f56": PREFIX_B,
    "\u0f58": PREFIX_M,
    "\u0f60": PREFIX_Q,
}
_SUPERFIX_CHARACTERS = {"\u0f62": SUPERFIX_R, "\u0f63": SUPERFIX_L, "\u0f66": SUPERFIX_S}
_SUBFIX_CHARACTERS = {"\u0fad": SUBFIX1_W, "\u0fb1": SUBFIX1_Y, "\u0fb2": SUBFIX1_R, "\u0fb3": SUBFIX1_L}
_SUBFIX2_CHARACTER = "\u0fad"
_ACHUNG = "\u0f71"


def _affix_flags(text: str) -> int:
    flags = 0
    for character in text:
        flags |= _PREFIX_CHARACTERS.get(character, 0) or _SUPERFIX_CHARACTERS.get(character, 0)
    return flags


def _subfix_flags(text: str) -> int:
    flags = 0
    for index, character in enumerate(text):
        flags |= SUBFIX2_W if index and character == _SUBFIX2_CHARACTER else _SUBFIX_CHARACTERS.get(character, 0)
    return flags


def _codepoints(text: str, width: int) -> tuple[int, ...]:
    """Split a Tibetan sequence into codepoints, padding it to ``width`` with zeros."""
    values = () if text == "-" else tuple(ord(character) for character in text)
    return values + (0,) * (width - len(values))


def _medial(text: str) -> tuple[int, int]:
    """Split an Extended Wylie vowel into its a-chung and vowel-sign codepoints."""
    if text == "-":
        return 0, 0
    if text[0] == _ACHUNG:
        return ord(_ACHUNG), ord(text[1]) if len(text) > 1 else 0
    return 0, ord(text[0])


def _load_tables() -> dict[str, list]:
    """Convert the Tibetan text in tibetan.tsv into the numeric tables the state machine uses."""
    data = ScriptsLoader.load_tibetan()
    return {
        "initials": [
            (wylie, ord(stem) - TIBETAN_BASE, _affix_flags(affixes), _subfix_flags(subfixes))
            for wylie, stem, affixes, subfixes in data["initial"]
        ],
        "subjoins": [(wylie, _codepoints(text, 1)[0]) for wylie, text in data["subjoin"]],
        "medials": [(wylie, *_medial(text)) for wylie, text in data["medial"]],
        "finals": [(wylie, _codepoints(text, 4)) for wylie, text in data["final"]],
        "punctuation": [(wylie, _codepoints(text, 1)[0]) for wylie, text in data["punctuation"]],
    }


# Step enum for the Tibetan input state machine
class StepType:
    START = 0
    PUNCTUATION = 1
    INITIALS = 2
    INITIALS_PLUS = 3
    INITIALS_PLUS_PLUS = 4
    INITIALS_PLUS_PLUS_PLUS = 5
    MEDIALS = 6
    FINALS = 7
    FINALS2 = 8
    NULL = 9


# Word position indices for the Tibetan syllable structure
class WordType:
    PREFIX = 0
    PREFIX_MODIFIER = 1
    SUPERFIX = 2
    STEM = 3
    STEM_MODIFIER = 4
    SUBFIX1 = 5
    SUBFIX2 = 6
    SUBJOIN_STEM1 = 7
    SUBJOIN_STEM2 = 8
    SUBJOIN_STEM3 = 9
    ACHUNG1 = 10
    VOWEL1 = 11
    VOWEL1_PLUS1 = 12
    VOWEL1_PLUS2 = 13
    VOWEL1_PLUS3 = 14
    FINAL = 15
    FINAL_MODIFIER = 16
    POST_FINAL1 = 17
    POST_FINAL2 = 18
    POST_FINAL3 = 19
    SUBJOIN_FINAL1 = 20
    SUBJOIN_FINAL2 = 21
    ACHUNG2 = 22
    VOWEL2 = 23
    FINAL2 = 24
    PUNCTUATION1 = 25
    PUNCTUATION2 = 26
    END = 27


class Tibetan(Language):
    """
    Tibetan language input method using Extended Wylie transliteration.

    Converts Wylie romanization to Tibetan Unicode characters (U+0F00-U+0FFF).
    Supports complex syllabic structures with prefixes, superfixes, subjoined
    letters, vowels, finals, and punctuation.
    """

    # Extended Wylie tables (data/scripts/tibetan.tsv), C++ row order.
    _TABLES = _load_tables()

    TABLE_INITIALS: ClassVar = _TABLES["initials"]

    TABLE_SUBJOINS: ClassVar = _TABLES["subjoins"]

    TABLE_MEDIALS: ClassVar = _TABLES["medials"]

    TABLE_FINALS: ClassVar = _TABLES["finals"]

    TABLE_PUNCTUATION: ClassVar = _TABLES["punctuation"]

    def __init__(self):
        super().__init__(block_start=0x0F00, block_end=0x1000)
        self._escape = True  # Tibetan uses Extended Wylie escape mode

        self._next1 = ZERO_16
        self._next2 = ZERO_16
        self._next3 = ZERO_16
        self._force_prefix = False
        self._force_long_vowel = False
        self._initials_index = 0
        self._medials_index = 0
        self._finals_index = 0
        self._finals2_index = 0
        self._subjoins_index = 0
        self._initials_pos = 0
        self._medials_pos = 0
        self._finals_pos = 0
        self._finals2_pos = 0
        self._subjoins_pos = 0
        self._plus_vowels = 0
        self._word = [ZERO_16] * WordType.END

        self.on_clear(reset=True)

    # --- Public API ---

    def get_output_string(self) -> str:
        """Get the accumulated Tibetan syllable output."""
        result = ""
        for i in range(WordType.END):
            if self._word[i]:
                if (self._word[i] & TSA_PHRU_MASK) == TSA_PHRU_MASK:
                    result += chr(self._word[i] & ~TSA_PHRU_MASK)
                    result += chr(0x0F39)
                else:
                    result += chr(self._word[i])
        self.on_clear()
        return result

    def on_clear(self, reset: bool = False) -> None:
        """Clear Tibetan input state."""
        super().on_clear(reset)
        self._step = StepType.NULL
        self._force_prefix = False
        self._force_long_vowel = False
        self._initials_index = 0
        self._medials_index = 0
        self._finals_index = 0
        self._finals2_index = 0
        self._subjoins_index = 0
        self._initials_pos = 0
        self._medials_pos = 0
        self._finals_pos = 0
        self._finals2_pos = 0
        self._subjoins_pos = 0
        self._plus_vowels = 0
        self._word = [ZERO_16] * WordType.END

    def _on_number(self, code: int) -> EInput:
        """Convert digit to Tibetan digit if not in bracket mode."""
        if self._ignore_text or self._other_lang:
            return EInput.IGNORE
        if self._bracket_count == 0:
            self.ch_output = code - 0x30 + TIBETAN_DIGITS
        return EInput.CHARACTER

    def on_input(self, code: int) -> EInput:
        """Process Extended Wylie character input."""
        return self._convert_extended_wylie(code)

    def on_return(self) -> EInput:
        return EInput.FINISHED

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int | None = None, skip_ascii: bool = False
    ) -> tuple:
        """
        Perform Tibetan script conversion.

        Convert an Extended Wylie string to Tibetan Unicode.

        Returns:
            Tuple of (converted_text, count).
        """
        if end is None:
            end = len(text_in)

        self.on_clear(reset=True)
        result = ""
        count = 0
        self._step = StepType.START
        self._next1 = self._next2 = self._next3 = ZERO_16
        i = start
        redo = False

        while i < end:
            if i == start:
                code = ord(text_in[i])
                self._next1 = ord(text_in[i + 1]) if i + 1 < end else ZERO_16
                self._next2 = ord(text_in[i + 2]) if i + 2 < end else ZERO_16
                self._next3 = ord(text_in[i + 3]) if i + 3 < end else ZERO_16
            elif redo:
                code = ord(text_in[i])
                redo = False
            else:
                code = self._next1
                self._next1, self._next2 = self._next2, self._next3
                self._next3 = ord(text_in[i + 3]) if i + 3 < end else ZERO_16

            if not code:
                i += 1
                continue

            if self._step == StepType.START:
                if code == ord(" "):
                    result += " "
                    i += 1
                    continue
                self._step = StepType.NULL
            if code == ord(" ") and not self._slash and self._step == StepType.NULL:
                result += chr(0x0F0B)
                self._step = StepType.START
                i += 1
                continue

            e_result = self.on_char(chr(code))
            if e_result in (
                EInput.IN_PROGRESS,
                EInput.CLEAR_IN_PROGRESS,
                EInput.CLEAR,
                EInput.BACKSPACE,
                EInput.BACKSPACE_REDO,
            ):
                pass
            elif e_result == EInput.INVALID:
                result += self.get_output_string()
                self.on_clear()
                e_result = self.on_char(chr(code))
                if e_result == EInput.INVALID:
                    result += chr(code)
            elif e_result == EInput.NULL:
                pass
            elif e_result == EInput.SHAD:
                self._step = StepType.START
                if self.ch_output:
                    result += chr(self.ch_output)
                    self.ch_output = 0
            elif e_result in (EInput.CHARACTER, EInput.CHARACTER_CLEAR, EInput.IGNORE, EInput.OK):
                result += chr(self.ch_output) if self.ch_output else chr(code)
                self.ch_output = 0
            elif e_result in (EInput.FINISHED, EInput.FINISHED_IN_PROGRESS):
                converted = self.get_output_string()
                result += converted
                if converted:
                    count += 1
            elif e_result == EInput.FINISHED_REDO:
                converted = self.get_output_string()
                result += converted
                if converted:
                    count += 1
                i -= 1
                redo = True
            elif e_result == EInput.CHAR32:
                result += chr(self.ch_output)
                count += 1
                self.ch_output = 0
            i += 1

        result += self.get_output_string()
        return result, count

    # --- Private: Extended Wylie conversion ---

    def _convert_extended_wylie(self, code: int) -> EInput:
        """State machine for Extended Wylie -> Tibetan Unicode."""
        ch = chr(code) if 0 <= code <= 0xFFFF else ""

        if ch == "[":
            self._bracket_count += 1
            if self._bracket_count > 1:
                return EInput.CHARACTER
            return EInput.FINISHED

        if ch == "]":
            if self._bracket_count > 0:
                self._bracket_count -= 1
            if self._bracket_count > 0:
                return EInput.CHARACTER
            return EInput.NULL

        if ch == "^" and self._bracket_count == 0:
            if self._step == StepType.NULL:
                self._word[WordType.STEM] = 0x0F68
                self._word[WordType.STEM_MODIFIER] = 0x0F39
                return EInput.IN_PROGRESS
            for i in range(WordType.END - 1, -1, -1):
                if self._word[i] and self._previous_input != ord("a"):
                    if i in (WordType.PREFIX, WordType.STEM, WordType.FINAL):
                        self._word[i] |= TSA_PHRU_MASK
                        return EInput.IN_PROGRESS
                    break
            return EInput.INVALID

        if self._bracket_count:
            return EInput.CHARACTER

        if self._step == StepType.NULL:
            if self._is_punctuation(code):
                if ch == "~":
                    self._step = StepType.PUNCTUATION
                    return EInput.IN_PROGRESS
                if ch == "/":
                    self.ch_output = self._word[WordType.PUNCTUATION1]
                    self._word[WordType.PUNCTUATION1] = ZERO_16
                    return EInput.SHAD
                if ch == ".":
                    return EInput.CHARACTER
                self.ch_output = self._word[WordType.PUNCTUATION1]
                self._word[WordType.PUNCTUATION1] = ZERO_16
                return EInput.CHARACTER
            if self._is_initial(code):
                self._step = StepType.INITIALS
                return EInput.IN_PROGRESS
            if self._is_medial(code, WordType.VOWEL1):
                self._word[WordType.STEM] = TIBETAN_BASE | self.TABLE_INITIALS[0][1]
                self._step = StepType.MEDIALS
                return EInput.IN_PROGRESS
            return EInput.INVALID

        if self._step == StepType.PUNCTUATION:
            if ch == "X":
                self._step = StepType.NULL
                return EInput.FINISHED
            return EInput.INVALID

        if self._step == StepType.INITIALS:
            if ch == "." and self._previous_input != ord("."):
                sequence = self.TABLE_INITIALS[self._initials_index][0]
                if self._initials_pos == 1 and sequence and sequence[0] in "gdbm'":
                    self._force_prefix = True
                    return EInput.IN_PROGRESS

            if self._force_prefix:
                second_vowels = {
                    "a": (0, 0), "i": (0, 0x0F72), "u": (0, 0x0F74),
                    "e": (0, 0x0F7A), "o": (0, 0x0F7C),
                    "A": (0x0F71, 0), "I": (0x0F71, 0x0F72),
                    "U": (0x0F71, 0x0F74), "E": (0x0F71, 0x0F7A),
                    "O": (0x0F71, 0x0F7C),
                }
                if ch in second_vowels:
                    achung, vowel = second_vowels[ch]
                    self._word[WordType.POST_FINAL1] = 0x0F68
                    self._word[WordType.ACHUNG2] = achung
                    self._word[WordType.VOWEL2] = vowel
                    self._step = StepType.FINALS2
                    return EInput.IN_PROGRESS

            if self._is_initial(code):
                if ch == "+":
                    self._step = StepType.INITIALS_PLUS
                return EInput.IN_PROGRESS
            if self._is_medial(code, WordType.VOWEL1):
                self._step = StepType.MEDIALS
                return EInput.IN_PROGRESS
            if self._is_final(code):
                self._step = StepType.FINALS
                return EInput.IN_PROGRESS
            if self._is_final2(code):
                self._step = StepType.FINALS2
                return EInput.IN_PROGRESS
            if self._is_punctuation(code):
                self._step = StepType.NULL
                return EInput.FINISHED
            self._step = StepType.NULL
            return EInput.FINISHED_REDO

        if self._step == StepType.INITIALS_PLUS:
            if self._is_subjoin(code, WordType.SUBJOIN_STEM1):
                return EInput.IN_PROGRESS
            if ch == "+" and self._subjoins_index and not self._medials_index:
                self._subjoins_index = self._subjoins_pos = 0
                self._step = StepType.INITIALS_PLUS_PLUS
                return EInput.IN_PROGRESS
            if self._is_medial(code, WordType.VOWEL1):
                if not self._subjoins_index:
                    self._word[WordType.SUBJOIN_STEM1] = 0x0FB8
                self._step = StepType.MEDIALS
                return EInput.IN_PROGRESS

        if self._step == StepType.INITIALS_PLUS_PLUS:
            if self._is_subjoin(code, WordType.SUBJOIN_STEM2):
                return EInput.IN_PROGRESS
            if ch == "+" and self._subjoins_index and not self._medials_index:
                self._subjoins_index = self._subjoins_pos = 0
                self._step = StepType.INITIALS_PLUS_PLUS_PLUS
                return EInput.IN_PROGRESS
            if self._is_medial(code, WordType.VOWEL1):
                if not self._subjoins_index:
                    self._word[WordType.SUBJOIN_STEM2] = 0x0FB8
                self._step = StepType.MEDIALS
                return EInput.IN_PROGRESS

        if self._step == StepType.INITIALS_PLUS_PLUS_PLUS:
            if self._is_subjoin(code, WordType.SUBJOIN_STEM3):
                return EInput.IN_PROGRESS
            if self._is_medial(code, WordType.VOWEL1):
                if not self._subjoins_index:
                    self._word[WordType.SUBJOIN_STEM3] = 0x0FB8
                self._step = StepType.MEDIALS
                return EInput.IN_PROGRESS

        if self._step == StepType.MEDIALS:
            if ch == "+" and self._plus_vowels < 3:
                if self._previous_input == ord("a"):
                    self._step = StepType.INITIALS_PLUS
                    self._medials_index = self._medials_pos = 0
                else:
                    self._plus_vowels += 1
                return EInput.IN_PROGRESS
            if self._plus_vowels:
                if self._previous_input == ord("-"):
                    if ch == "i":
                        self._word[WordType.VOWEL1 + self._plus_vowels] = 0x0F80
                        return EInput.IN_PROGRESS
                    return EInput.INVALID
                extra_vowels = {"i": 0x0F72, "u": 0x0F74, "e": 0x0F7A, "o": 0x0F7C}
                if ch in extra_vowels:
                    self._word[WordType.VOWEL1 + self._plus_vowels] = extra_vowels[ch]
                    return EInput.IN_PROGRESS
                if ch == "-":
                    return EInput.IN_PROGRESS
            elif self._is_medial(code, WordType.VOWEL1):
                return EInput.IN_PROGRESS
            if self._is_final(code):
                self._step = StepType.FINALS
                return EInput.IN_PROGRESS
            if self._is_punctuation(code):
                self._step = StepType.NULL
                return EInput.FINISHED
            self._step = StepType.NULL
            return EInput.FINISHED_REDO

        if self._step == StepType.FINALS:
            if self._is_final(code):
                return EInput.IN_PROGRESS
            if self._is_punctuation(code):
                self._step = StepType.NULL
                return EInput.FINISHED
            self._step = StepType.NULL
            return EInput.FINISHED_REDO

        if self._step == StepType.FINALS2:
            if self._is_final2(code):
                return EInput.IN_PROGRESS
            if self._is_punctuation(code):
                self._step = StepType.NULL
                return EInput.FINISHED
            self._step = StepType.NULL
            return EInput.FINISHED_REDO

        return EInput.INVALID

    def _is_punctuation(self, code: int) -> bool:
        if self.TABLE_MEDIALS[self._medials_index][0][self._medials_pos:self._medials_pos + 1] or \
                self.TABLE_FINALS[self._finals_index][0][self._finals_pos:self._finals_pos + 1]:
            return False
        for i, (punctuation, mapped) in enumerate(self.TABLE_PUNCTUATION):
            if ord(punctuation) != code:
                continue
            if not mapped:
                return True
            if code == ord("/") and self._next1 == ord("/"):
                self._next1 = ZERO_16
                i += 1
                mapped = self.TABLE_PUNCTUATION[i][1]
            self._word[WordType.PUNCTUATION1] = mapped
            if mapped == 0x0F0D:
                if self._word[WordType.STEM] == 0x0F44 and not self._word[WordType.FINAL]:
                    self._word[WordType.PUNCTUATION1] = 0x0F0C
                    self._word[WordType.PUNCTUATION2] = mapped
                if self._word[WordType.FINAL] == 0x0F44 and not self._word[WordType.POST_FINAL1]:
                    self._word[WordType.PUNCTUATION1] = 0x0F0C
                    self._word[WordType.PUNCTUATION2] = mapped
            return True
        if ord("0") <= code <= ord("9"):
            self._on_number(code)
            self._word[WordType.PUNCTUATION1] = self.ch_output
            self.ch_output = 0
            return True
        return False

    def _is_initial(self, code: int) -> bool:
        for i in range(self._initials_index, len(self.TABLE_INITIALS)):
            sequence, stem_index, flags, subfixes = self.TABLE_INITIALS[i]
            if self._initials_pos and sequence[:self._initials_pos] != \
                    self.TABLE_INITIALS[self._initials_index][0][:self._initials_pos]:
                return False
            if self._initials_pos >= len(sequence) or ord(sequence[self._initials_pos]) != code:
                continue
            if self._force_prefix:
                if not flags & PREFIX_MASK:
                    continue
                self._force_prefix = False
            if code in (ord("f"), ord("v")):
                self._word[WordType.STEM_MODIFIER] = 0x0F39

            old_prefix, old_stem = self._word[WordType.PREFIX], self._word[WordType.STEM]
            self._initials_index = i
            self._initials_pos += 1
            self._word[WordType.STEM] = TIBETAN_BASE | stem_index
            self._word[WordType.PREFIX] = self._prefix_character(flags)
            self._word[WordType.SUPERFIX] = self._superfix_character(flags)
            self._word[WordType.SUBFIX1] = self._subfix_character(subfixes, second=False)
            self._word[WordType.SUBFIX2] = self._subfix_character(subfixes, second=True)

            if old_prefix & TSA_PHRU_MASK == TSA_PHRU_MASK and old_prefix & ~TSA_PHRU_MASK == self._word[WordType.PREFIX]:
                self._word[WordType.PREFIX] |= TSA_PHRU_MASK
            if old_stem & TSA_PHRU_MASK == TSA_PHRU_MASK:
                if old_stem & ~TSA_PHRU_MASK == self._word[WordType.STEM]:
                    self._word[WordType.STEM] |= TSA_PHRU_MASK
                elif old_stem & ~TSA_PHRU_MASK == self._word[WordType.PREFIX]:
                    self._word[WordType.PREFIX] |= TSA_PHRU_MASK
            if code == ord("F"):
                self._word[WordType.SUBFIX1] = 0x0FA5
            return True
        return False

    def _is_medial(self, code: int, word_pos: int) -> bool:
        initial = self.TABLE_INITIALS[self._initials_index][0]
        subjoin = self.TABLE_SUBJOINS[self._subjoins_index][0]
        if (self._initials_pos < len(initial) and ord(initial[self._initials_pos]) == code) or \
                (self._subjoins_pos < len(subjoin) and ord(subjoin[self._subjoins_pos]) == code):
            return False
        for i in range(self._medials_index, len(self.TABLE_MEDIALS)):
            sequence, achung, vowel = self.TABLE_MEDIALS[i]
            if self._medials_pos and sequence[:self._medials_pos] != \
                    self.TABLE_MEDIALS[self._medials_index][0][:self._medials_pos]:
                return False
            if self._medials_pos < len(sequence) and ord(sequence[self._medials_pos]) == code:
                self._medials_index = i
                self._medials_pos += 1
                self._word[word_pos - 1] = achung
                self._word[word_pos] = vowel
                return True
        return False

    def _is_final(self, code: int) -> bool:
        if self._medials_pos < len(self.TABLE_MEDIALS[self._medials_index][0]):
            return False
        if self._next1 in map(ord, "aiueo-"):
            return False
        if ord("A") <= self._next1 <= ord("Z") and code != ord("~"):
            return False
        next_char = chr(self._next1) if self._next1 else ""
        next2 = chr(self._next2) if self._next2 else ""
        next3 = chr(self._next3) if self._next3 else ""
        n_finals = 1
        if code in (ord("H"), ord("M")):
            n_finals = 0
        elif code == ord("n"):
            n_finals += int(next_char == "d")
            if next_char == "g":
                n_finals += 1 + int(next2 == "s")
        elif code in (ord("r"), ord("l")) and next_char == "d" or code in (ord("g"), ord("b"), ord("m")) and next_char == "s":
            n_finals += 1
        if n_finals == 1:
            if next_char == "h" or (code == ord("r") and "a" <= next_char <= "z") or \
                    (code == ord("d") and next_char == "z") or (code == ord("n") and next_char == "y") or \
                    next_char in ("+", "-"):
                return False
        elif n_finals == 2 and (("a" <= next2 <= "z") or next2 in ("+", "-")) or n_finals == 3 and (("a" <= next3 <= "z") or next3 in ("+", "-")):
            return False

        for i in range(self._finals_index, len(self.TABLE_FINALS)):
            sequence, mapped = self.TABLE_FINALS[i]
            if self._finals_pos and sequence[:self._finals_pos] != \
                    self.TABLE_FINALS[self._finals_index][0][:self._finals_pos]:
                return False
            if self._finals_pos < len(sequence) and ord(sequence[self._finals_pos]) == code:
                self._finals_index = i
                self._finals_pos += 1
                for slot, character in zip(
                    (WordType.FINAL, WordType.POST_FINAL1, WordType.POST_FINAL2, WordType.POST_FINAL3),
                    mapped,
                ):
                    self._word[slot] = (self._word[slot] & TSA_PHRU_MASK) | character
                return True
        return False

    def _is_final2(self, code: int) -> bool:
        for i in range(self._finals2_index, len(self.TABLE_FINALS)):
            sequence, mapped = self.TABLE_FINALS[i]
            if self._finals2_pos and sequence[:self._finals2_pos] != \
                    self.TABLE_FINALS[self._finals2_index][0][:self._finals2_pos]:
                return False
            if self._finals2_pos < len(sequence) and ord(sequence[self._finals2_pos]) == code:
                self._finals2_index = i
                self._finals2_pos += 1
                marker = self._word[WordType.FINAL2] & TSA_PHRU_MASK
                self._word[WordType.FINAL2] = mapped[0] | marker
                return True
        return False

    def _is_subjoin(self, code: int, word_pos: int) -> bool:
        for i in range(self._subjoins_index, len(self.TABLE_SUBJOINS)):
            sequence, mapped = self.TABLE_SUBJOINS[i]
            if self._subjoins_pos and sequence[:self._subjoins_pos] != \
                    self.TABLE_SUBJOINS[self._subjoins_index][0][:self._subjoins_pos]:
                return False
            if self._subjoins_pos < len(sequence) and ord(sequence[self._subjoins_pos]) == code:
                self._subjoins_index = i
                self._subjoins_pos += 1
                self._word[word_pos] = mapped
                return True
        return False

    @staticmethod
    def _prefix_character(flags: int) -> int:
        for flag, code in ((PREFIX_G, 0x0F42), (PREFIX_D, 0x0F51), (PREFIX_B, 0x0F56),
                           (PREFIX_M, 0x0F58), (PREFIX_Q, 0x0F60)):
            if flags & flag:
                return code
        return ZERO_16

    @staticmethod
    def _superfix_character(flags: int) -> int:
        for flag, code in ((SUPERFIX_R, 0x0F62), (SUPERFIX_L, 0x0F63), (SUPERFIX_S, 0x0F66)):
            if flags & flag:
                return code
        return ZERO_16

    @staticmethod
    def _subfix_character(flags: int, second: bool) -> int:
        choices = ((SUBFIX2_W, 0x0FAD),) if second else (
            (SUBFIX1_W, 0x0FAD), (SUBFIX1_Y, 0x0FB1), (SUBFIX1_R, 0x0FB2), (SUBFIX1_L, 0x0FB3)
        )
        return next((code for flag, code in choices if flags & flag), ZERO_16)

    def _previous_char_in(self, char_set: set) -> bool:
        return self._previous_input != ZERO_16 and chr(self._previous_input) in char_set
