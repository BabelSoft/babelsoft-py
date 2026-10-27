"""
LanguageYi - Python equivalent of c/Languages/LanguageYi.h and LanguageYi.cpp

Handles Yi script (U+A000-U+A48F syllables, U+A490-U+A4C6 radicals).
Provides Latin->Yi, Yi->Latin, Yi->IPA conversion, radical/stroke lookup.
"""

from typing import ClassVar

from babelsoft.utils_.loader import ScriptsLoader

from .class_ import EInput, Language

# Block constants
SYLLABLE_FIRST = 0xA000
SYLLABLE_LAST = 0xA48F
RADICAL_FIRST = 0xA490
RADICAL_COUNT = 55
SYLLABLE_COUNT = 1165

# Tone constants
TONE_1 = 1  # High Level = t
TONE_2 = 2  # Secondary High = x
TONE_3 = 3  # Mid Level = (null)
TONE_4 = 4  # Low Falling = p

# Syllable/index/radical tables (data/scripts/yi.tsv).
_YI_DATA = ScriptsLoader.load_yi()


# Step enum
class StepType:
    INITIAL1_OR_MEDIAL1 = 0
    INITIAL2_OR_MEDIAL1 = 1
    MEDIAL1 = 2
    MEDIAL2 = 3
    MEDIAL2_OR_FINAL = 4
    FINAL = 5


# Transcription system enum
class TranscriptionType:
    LATIN = 0
    IPA = 1


class Yi(Language):
    """
    Yi language input method and conversion class.

    Provides:
    - Latin transcription -> Yi syllable conversion
    - Yi syllable -> Latin transcription
    - Yi syllable -> IPA transcription
    - Character name lookup (e.g., "NGA OP RROX")
    - Radical/stroke lookup for syllables
    - Syllable lookup by radical + stroke count
    """

    # --- Latin Initials Table (45 entries; copied from LanguageYi.cpp) ---
    # [first_letter, second_letter]
    TABLE_YI_LATIN_INITIALS: ClassVar[list[list[int]]] = [
        [0x00, 0x00],
        [0x77, 0x20],
        [0x62, 0x00],
        [0x70, 0x00],
        [0x62, 0x62],
        [0x6e, 0x62],
        [0x68, 0x6d],
        [0x6d, 0x00],
        [0x66, 0x00],
        [0x76, 0x00],
        [0x64, 0x00],
        [0x74, 0x00],
        [0x64, 0x64],
        [0x6e, 0x64],
        [0x68, 0x6e],
        [0x6e, 0x00],
        [0x68, 0x6c],
        [0x6c, 0x00],
        [0x67, 0x00],
        [0x6b, 0x00],
        [0x67, 0x67],
        [0x6d, 0x67],
        [0x68, 0x78],
        [0x6e, 0x67],
        [0x68, 0x00],
        [0x77, 0x00],
        [0x7a, 0x00],
        [0x63, 0x00],
        [0x7a, 0x7a],
        [0x6e, 0x7a],
        [0x73, 0x00],
        [0x73, 0x73],
        [0x7a, 0x68],
        [0x63, 0x68],
        [0x72, 0x72],
        [0x6e, 0x72],
        [0x73, 0x68],
        [0x72, 0x00],
        [0x6a, 0x00],
        [0x71, 0x00],
        [0x6a, 0x6a],
        [0x6e, 0x6a],
        [0x6e, 0x79],
        [0x78, 0x00],
        [0x79, 0x00],
    ]

    # --- Latin Medials Table (11 entries) ---
    # [first_vowel, second_vowel]
    TABLE_YI_LATIN_MEDIALS: ClassVar[list[list[int]]] = [
        [0x00, 0x00],
        [0x69, 0x00],
        [0x69, 0x65],
        [0x61, 0x00],
        [0x75, 0x6f],
        [0x6f, 0x00],
        [0x65, 0x00],
        [0x75, 0x00],
        [0x75, 0x72],
        [0x79, 0x00],
        [0x79, 0x72],
    ]

    # --- Latin Finals Table (5 entries) ---
    TABLE_YI_LATIN_FINALS: ClassVar[list[int]] = [0x00, 0x74, 0x78, 0x20, 0x70]

    # --- Yi Syllable Index (46 boundaries; data/scripts/yi.tsv) ---
    TABLE_YI_INDEX: ClassVar[list[int]] = list(_YI_DATA["index"])

    # --- Yi Syllables Table (1165 entries; data/scripts/yi.tsv) ---
    # Each row: [initial_index, medial_index, final_index]
    TABLE_YI_SYLLABLES: ClassVar[list[list[int]]] = [list(row) for row in _YI_DATA["syllables"]]

    # --- Punctuation Table ---
    TABLE_YI_PUNCTUATION: ClassVar[list[int]] = [ord(","), ord("."), ord("!"), ord("?")]
    TABLE_YI_PUNCTUATION_MAP: ClassVar[list[int]] = [0xA1AA, 0xA1AB, 0xA1AC, 0xA1AD]

    # --- Radical Names (55 names; data/scripts/yi.tsv) ---
    RADICAL_NAMES: ClassVar[list[str]] = list(_YI_DATA["radicals"])

    # --- IPA Tables ---
    TABLE_YI_IPA_INITIALS: ClassVar[list[list[int]]] = [
        [0x0000, 0x0000, 0x0000],
        [0x0000, 0x0000, 0x0000],
        [0x0070, 0x0000, 0x0000],
        [0x0070, 0x0068, 0x0000],
        [0x0062, 0x0000, 0x0000],
        [0x006d, 0x0062, 0x0000],
        [0x006d, 0x0325, 0x0000],
        [0x006d, 0x0000, 0x0000],
        [0x0066, 0x0000, 0x0000],
        [0x0076, 0x0000, 0x0000],
        [0x0074, 0x0000, 0x0000],
        [0x0074, 0x0068, 0x0000],
        [0x0064, 0x0000, 0x0000],
        [0x006e, 0x0064, 0x0000],
        [0x006e, 0x0325, 0x0000],
        [0x006e, 0x0000, 0x0000],
        [0x026c, 0x0000, 0x0000],
        [0x006c, 0x0000, 0x0000],
        [0x006b, 0x0000, 0x0000],
        [0x006b, 0x0068, 0x0000],
        [0x0067, 0x0000, 0x0000],
        [0x014b, 0x0067, 0x0000],
        [0x0068, 0x0000, 0x0000],
        [0x014b, 0x0000, 0x0000],
        [0x0078, 0x0000, 0x0000],
        [0x0263, 0x0000, 0x0000],
        [0x0074, 0x0073, 0x0000],
        [0x0074, 0x0073, 0x0068],
        [0x0064, 0x007a, 0x0000],
        [0x006e, 0x0064, 0x007a],
        [0x0073, 0x0000, 0x0000],
        [0x007a, 0x0000, 0x0000],
        [0x0074, 0x0282, 0x0000],
        [0x0074, 0x0282, 0x0068],
        [0x0064, 0x0290, 0x0000],
        [0x006e, 0x0064, 0x0290],
        [0x0282, 0x0000, 0x0000],
        [0x0290, 0x0000, 0x0000],
        [0x0074, 0x0255, 0x0000],
        [0x0074, 0x0255, 0x0068],
        [0x0064, 0x0291, 0x0000],
        [0x006e, 0x0064, 0x0291],
        [0x0235, 0x0000, 0x0000],
        [0x0255, 0x0000, 0x0000],
        [0x0291, 0x0000, 0x0000],
    ]

    TABLE_YI_IPA_MEDIALS: ClassVar[list[list[int]]] = [
        [0x0000, 0x0000],
        [0x0069, 0x0000],
        [0x025b, 0x0000],
        [0x0061, 0x0000],
        [0x0254, 0x0000],
        [0x006f, 0x0000],
        [0x026f, 0x0000],
        [0x0075, 0x0000],
        [0x0075, 0x0331],
        [0x027f, 0x0000],
        [0x027f, 0x0331],
    ]

    # IPA tone marks (stored as tuples of individual character ordinals)
    # [tone1, tone2] where tone2 may be 0
    TABLE_YI_IPA_FINALS: ClassVar[list[list[int]]] = [
        [0x0000, 0x0000],
        [0x2075, 0x2075],
        [0x00b3, 0x2074],
        [0x00b3, 0x00b3],
        [0x00b2, 0x00b9],
    ]

    def __init__(self):
        super().__init__(block_start=SYLLABLE_FIRST, block_end=RADICAL_FIRST + RADICAL_COUNT)
        self._initials_index = 0
        self._medials_index = 0
        self._finals_index = 0
        self._syllables_index = 0
        self._hanging_vowel = False
        self._completed_syllables_index = None
        self.on_clear(reset=True)

    # --- Public API ---

    def on_clear(self, reset: bool = False) -> None:
        """Clear Yi input state."""
        super().on_clear(reset)
        self._initials_index = 0
        self._medials_index = 0
        self._finals_index = 0
        self._syllables_index = 0
        self._hanging_vowel = False
        self._completed_syllables_index = None

    def on_input(self, code: int) -> EInput:
        """Process character input for Yi Latin transcription."""
        return self._convert_latin(code)

    def on_return(self) -> EInput:
        return EInput.RETURN

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int | None = None, skip_ascii: bool = False
    ) -> tuple:
        """
        Perform conversion based on menu_id.

        Args:
            menu_id: Conversion type (see EYiTrans).
            text_in: Input text.
            start: Start position.
            end: End position (None = len(text_in)).
            skip_ascii: Whether to skip ASCII characters.

        Returns:
            Tuple of (converted_text, count_of_conversions).
        """
        if end is None:
            end = len(text_in)

        self.on_clear(reset=True)
        count = 0
        result = ""

        if menu_id == 0:  # Yi -> Latin
            result, count = self._convert_yi_to_latin(text_in, start, end)
        elif menu_id == 1:  # Yi -> IPA
            result, count = self._convert_yi_to_ipa(text_in, start, end)
        elif menu_id == 2:  # Latin -> Yi
            result, count = self._convert_latin_to_yi(text_in, start, end)

        return result, count

    @staticmethod
    def get_character_name(code_point: int, add_space: bool = False) -> str:
        """
        Get the name of a Yi character.

        Yi syllable names are composed from Latin initials + medials + finals.
        Yi radical names are predefined.

        Args:
            code_point: Unicode code point.
            add_space: Whether to append a trailing space.

        Returns:
            Character name string.
        """
        name = ""

        if SYLLABLE_FIRST <= code_point <= SYLLABLE_LAST:
            idx = code_point - SYLLABLE_FIRST
            if idx < len(Yi.TABLE_YI_SYLLABLES):
                syl = Yi.TABLE_YI_SYLLABLES[idx]
                ni, mi, fi = syl[0], syl[1], syl[2]

                # Initials
                init = Yi.TABLE_YI_LATIN_INITIALS[ni]
                if init[0]:
                    name += chr(init[0])
                if init[1] and init[1] != 0x20:
                    name += chr(init[1])

                # Medials
                med = Yi.TABLE_YI_LATIN_MEDIALS[mi]
                if med[0]:
                    name += chr(med[0])
                if med[1]:
                    name += chr(med[1])

                # Finals
                fin = Yi.TABLE_YI_LATIN_FINALS[fi]
                if fin and fin != 0x20:
                    name += chr(fin)

        elif RADICAL_FIRST <= code_point < RADICAL_FIRST + RADICAL_COUNT:
            idx = code_point - RADICAL_FIRST
            if idx < len(Yi.RADICAL_NAMES):
                name = Yi.RADICAL_NAMES[idx]

        if add_space:
            name += " "

        return name

    @staticmethod
    def get_ipa(code_point: int) -> str:
        """
        Get the IPA transcription of a Yi syllable.

        Args:
            code_point: Unicode code point of the Yi syllable.

        Returns:
            IPA transcription string.
        """
        ipa = ""

        if SYLLABLE_FIRST <= code_point <= SYLLABLE_LAST:
            idx = code_point - SYLLABLE_FIRST
            if idx < len(Yi.TABLE_YI_SYLLABLES):
                syl = Yi.TABLE_YI_SYLLABLES[idx]
                ni, mi, fi = syl[0], syl[1], syl[2]

                # IPA Initials
                ipa_init = Yi.TABLE_YI_IPA_INITIALS[ni]
                for ch in ipa_init:
                    if ch:
                        ipa += chr(ch)

                # IPA Medials
                ipa_med = Yi.TABLE_YI_IPA_MEDIALS[mi]
                for ch in ipa_med:
                    if ch:
                        ipa += chr(ch)

                # IPA Finals
                ipa_fin = Yi.TABLE_YI_IPA_FINALS[fi]
                for ch in ipa_fin:
                    if ch:
                        ipa += chr(ch)

        return ipa

    @staticmethod
    def get_tone(code_point: int) -> int:
        """
        Get the tone of a Yi syllable.

        Args:
            code_point: Unicode code point.

        Returns:
            Tone number (1-4) or 0 if not a syllable.
        """
        if SYLLABLE_FIRST <= code_point <= SYLLABLE_LAST:
            idx = code_point - SYLLABLE_FIRST
            if idx < len(Yi.TABLE_YI_SYLLABLES):
                return Yi.TABLE_YI_SYLLABLES[idx][2]
        return 0

    @staticmethod
    def find_radical_stroke_for_syllable(code_point: int) -> tuple:
        """Radical number (1-26) and residual stroke count of a Yi syllable.

        Returns ``(None, None)`` when the code point has no entry in the Yi
        radical table (e.g. it is not a Yi syllable).
        """
        from babelsoft.scripts.yi import YiRadical

        pairs = YiRadical.get_radical_stroke(code_point)
        if not pairs:
            return None, None
        return pairs[0]

    @staticmethod
    def find_syllables_for_radical(radical: int, strokes: int, all_strokes: bool = False, fuzzy: bool = False) -> list:
        """Code points of the Yi syllables written with ``radical``.

        ``all_strokes`` ignores the stroke count, ``fuzzy`` also accepts one
        stroke more or less.  A syllable can list several radical/stroke pairs
        (that is how the Yi charts count ambiguous shapes), and it matches when
        any pair fits.
        """
        from babelsoft.scripts.yi import YiRadical

        wanted = {strokes}
        if fuzzy:
            wanted |= {strokes - 1, strokes + 1}
        return [
            cp
            for cp, pairs in sorted(YiRadical.syllables().items())
            if any(rad == radical and (all_strokes or stroke in wanted) for rad, stroke in pairs)
        ]

    # --- Private: Latin -> Yi conversion ---

    def _convert_latin(self, code: int) -> EInput:
        """Convert Latin transcription character to Yi syllable."""
        ch = chr(code)

        # Handle brackets for literal mode
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

        if self._bracket_count:
            return EInput.CHARACTER

        # Convert uppercase to lowercase
        if "A" <= ch <= "Z":
            code = ord(ch.lower())
            ch = chr(code)

        step = self._step

        if step == StepType.INITIAL1_OR_MEDIAL1:
            if self._is_punctuation(code):
                return EInput.CHARACTER

            if self._is_initial(ch, False):
                self._step = StepType.INITIAL2_OR_MEDIAL1
                return EInput.IN_PROGRESS

            if self._is_medial(ch, False):
                self._step = StepType.MEDIAL2_OR_FINAL
                if self._hanging_vowel:
                    self._step = StepType.MEDIAL2
                return EInput.IN_PROGRESS

            return EInput.IGNORE

        elif step == StepType.INITIAL2_OR_MEDIAL1:
            if self._is_initial(ch, True):
                if self._initials_index == 1:
                    self.on_clear()
                    self._completed_syllables_index = self.TABLE_YI_INDEX[1] - SYLLABLE_FIRST
                    return EInput.CHARACTER_CLEAR
                self._step = StepType.MEDIAL1
                return EInput.IN_PROGRESS

            if self._is_medial(ch, False):
                self._step = StepType.MEDIAL2_OR_FINAL
                if self._hanging_vowel:
                    self._step = StepType.MEDIAL2
                return EInput.IN_PROGRESS

            return EInput.INVALID

        elif step == StepType.MEDIAL1:
            if self._is_medial(ch, False):
                self._step = StepType.MEDIAL2_OR_FINAL
                if self._hanging_vowel:
                    self._step = StepType.MEDIAL2
                return EInput.IN_PROGRESS
            return EInput.INVALID

        elif step == StepType.MEDIAL2:
            if self._is_medial(ch, True):
                self._step = StepType.FINAL
                return EInput.IN_PROGRESS
            return EInput.INVALID

        elif step == StepType.MEDIAL2_OR_FINAL:
            if self._is_medial(ch, True):
                self._step = StepType.FINAL
                return EInput.IN_PROGRESS
            if self._is_final(ch):
                completed_index = self._syllables_index
                self.on_clear()
                self._completed_syllables_index = completed_index
                return EInput.CHARACTER_CLEAR
            return EInput.INVALID

        elif step == StepType.FINAL:
            if self._is_final(ch):
                completed_index = self._syllables_index
                self.on_clear()
                self._completed_syllables_index = completed_index
                return EInput.CHARACTER_CLEAR
            return EInput.INVALID

        return EInput.INVALID

    def _is_punctuation(self, code: int) -> bool:
        """Check if character is Yi punctuation."""
        for i, pc in enumerate(self.TABLE_YI_PUNCTUATION):
            if pc == code:
                return True
        return False

    def _is_initial(self, ch: str, is_second: bool) -> bool:
        """Check if character is a valid initial consonant."""
        ch_one = ch
        ch_two = "\x00"

        if is_second:
            if self._initials_index >= len(self.TABLE_YI_LATIN_INITIALS):
                return False
            ch_one = chr(self.TABLE_YI_LATIN_INITIALS[self._initials_index][0])
            ch_two = ch

        for i, init in enumerate(self.TABLE_YI_LATIN_INITIALS):
            if chr(init[0]) == ch_one and (not ch_two or chr(init[1]) == ch_two):
                self._initials_index = i
                return True

        return False

    def _is_medial(self, ch: str, is_second: bool) -> bool:
        """Check if character is a valid medial vowel."""
        ch_one = ch
        ch_two = "\x00"

        if is_second:
            if self._medials_index >= len(self.TABLE_YI_LATIN_MEDIALS):
                return False
            ch_one = chr(self.TABLE_YI_LATIN_MEDIALS[self._medials_index][0])
            ch_two = ch

        for i, med in enumerate(self.TABLE_YI_LATIN_MEDIALS):
            if chr(med[0]) == ch_one and (not ch_two or chr(med[1]) == ch_two):
                return self._is_valid_medial(i)

        return False

    def _is_valid_medial(self, medial_idx: int) -> bool:
        """Check if the medial is valid for the current initial."""
        if self._initials_index >= len(self.TABLE_YI_INDEX) - 1:
            return False

        start = self.TABLE_YI_INDEX[self._initials_index] - SYLLABLE_FIRST
        end = self.TABLE_YI_INDEX[self._initials_index + 1] - SYLLABLE_FIRST

        for i in range(start, min(end, len(self.TABLE_YI_SYLLABLES))):
            if self.TABLE_YI_SYLLABLES[i][1] == medial_idx:
                self._medials_index = medial_idx
                self._syllables_index = i
                return True

        # Check hanging vowel cases (ie -> i, uo -> u)
        if medial_idx == 1 and self._is_valid_medial(2):
            self._hanging_vowel = True
            return True

        if medial_idx == 7 and self._is_valid_medial(4):
            self._hanging_vowel = True
            return True

        return False

    def _is_final(self, ch: str) -> bool:
        """Check if character is a valid final tone marker."""
        code = ord(ch)
        for i, fin in enumerate(self.TABLE_YI_LATIN_FINALS):
            if fin == code:
                return self._is_valid_final(i)
        return False

    def _is_valid_final(self, final_idx: int) -> bool:
        """Check if the final is valid for the current medial."""
        if self._syllables_index >= len(self.TABLE_YI_SYLLABLES):
            return False

        current_medial = self.TABLE_YI_SYLLABLES[self._syllables_index][1]
        i = self._syllables_index

        while i < len(self.TABLE_YI_SYLLABLES) and self.TABLE_YI_SYLLABLES[i][1] == current_medial:
            if self.TABLE_YI_SYLLABLES[i][2] == final_idx:
                self._finals_index = final_idx
                self._syllables_index = i
                return True
            i += 1

        return False

    # --- Private: Conversion methods ---

    def _convert_yi_to_latin(self, text: str, start: int, end: int) -> tuple:
        """Convert Yi syllables to Latin transcription."""
        result = ""
        count = 0

        for i in range(start, end):
            code = ord(text[i])

            if SYLLABLE_FIRST <= code <= SYLLABLE_LAST:
                idx = code - SYLLABLE_FIRST
                if idx < len(self.TABLE_YI_SYLLABLES):
                    syl = self.TABLE_YI_SYLLABLES[idx]
                    ni, mi, fi = syl[0], syl[1], syl[2]

                    init = self.TABLE_YI_LATIN_INITIALS[ni]
                    med = self.TABLE_YI_LATIN_MEDIALS[mi]
                    fin = self.TABLE_YI_LATIN_FINALS[fi]

                    if init[0]:
                        result += chr(init[0])
                    if init[1] and init[1] != 0x20:
                        result += chr(init[1])
                    if med[0]:
                        result += chr(med[0])
                    if med[1]:
                        result += chr(med[1])
                    if fin and fin != 0x20:
                        result += chr(fin)

                    count += 1
            elif RADICAL_FIRST <= code < RADICAL_FIRST + RADICAL_COUNT:
                idx = code - RADICAL_FIRST
                if idx < len(self.RADICAL_NAMES):
                    result += self.RADICAL_NAMES[idx]
            else:
                result += text[i]

        return result, count

    def _convert_yi_to_ipa(self, text: str, start: int, end: int) -> tuple:
        """Convert Yi syllables to IPA transcription."""
        result = ""
        count = 0

        for i in range(start, end):
            code = ord(text[i])

            if SYLLABLE_FIRST <= code <= SYLLABLE_LAST:
                idx = code - SYLLABLE_FIRST
                if idx < len(self.TABLE_YI_SYLLABLES):
                    syl = self.TABLE_YI_SYLLABLES[idx]
                    ni, mi, fi = syl[0], syl[1], syl[2]

                    ipa_init = self.TABLE_YI_IPA_INITIALS[ni]
                    ipa_med = self.TABLE_YI_IPA_MEDIALS[mi]
                    ipa_fin = self.TABLE_YI_IPA_FINALS[fi]

                    for ch in ipa_init:
                        if ch:
                            result += chr(ch)
                    for ch in ipa_med:
                        if ch:
                            result += chr(ch)
                    for ch in ipa_fin:
                        if ch:
                            result += chr(ch)

                    count += 1
            else:
                result += text[i]

        return result, count

    def _convert_latin_to_yi(self, text: str, start: int, end: int) -> tuple:
        """Convert Latin transcription to Yi syllables."""
        result = ""
        count = 0

        for i in range(start, end):
            ch = text[i]

            e_input = self.on_char(ch)

            if e_input == EInput.IN_PROGRESS:
                continue
            elif e_input == EInput.CHARACTER_CLEAR or e_input == EInput.CHARACTER:
                # Get the Yi syllable code point
                syllable_index = self._completed_syllables_index
                if syllable_index is None:
                    syllable_index = self._syllables_index
                yi_code = SYLLABLE_FIRST + syllable_index
                if SYLLABLE_FIRST <= yi_code <= SYLLABLE_LAST:
                    result += chr(yi_code)
                    count += 1
                else:
                    result += ch
                self._completed_syllables_index = None
            elif e_input == EInput.IGNORE:
                result += ch
            elif e_input in (EInput.BACKSPACE, EInput.BACKSPACE_REDO):
                continue
            elif e_input == EInput.INVALID:
                result += ch

        return result, count
