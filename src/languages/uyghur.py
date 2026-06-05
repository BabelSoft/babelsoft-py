"""
LanguageUyghur - Python equivalent of c/Languages/LanguageUyghur.h/.cpp

Handles Uyghur Arabic script input and conversion.
Provides Arabic<->Latin transcription and keyboard layout mapping.
"""

from .class_ import Language, EInput, FF_16, ZERO_16


class Uyghur(Language):
    """
    Uyghur language input method.

    Provides:
    - Keyboard layout mapping (ASCII -> Uyghur Arabic Unicode)
    - Arabic to Latin transcription
    - Latin to Arabic transcription
    """

    # Uyghur Arabic characters in order
    UYGHUR_ARABIC = [
        0x0627,  # A a (alef)
        0x06D5,  # E e
        0x0628,  # B b
        0x067E,  # P p
        0x062A,  # T t
        0x062C,  # J j
        0x0686,  # CH ch
        0x062E,  # X x
        0x062F,  # D d
        0x0631,  # R r
        0x0632,  # Z z
        0x0698,  # ZH zh
        0x0633,  # S s
        0x0634,  # SH sh
        0x0641,  # F f
        0x0642,  # Q q
        0x0643,  # K k
        0x06AF,  # G g
        0x063A,  # GH gh
        0x0644,  # L l
        0x0645,  # M m
        0x0646,  # N n
        0x06AD,  # NG ng
        0x06BE,  # H h
        0x0648,  # O o
        0x06C7,  # U u
        0x06C6,  # Ö ö
        0x06C8,  # Ü ü
        0x06CB,  # W w
        0x06D0,  # É é
        0x0649,  # I i
        0x064A,  # Y y
        0x060C,  # comma
        0x061B,  # semicolon
        0x061F,  # question mark
    ]

    # Uyghur Latin transcription (matches UYGHUR_ARABIC order)
    UYGHUR_LATIN = [
        ["a", ""],  # alef
        ["e", ""],  # E
        ["b", ""],  # B
        ["p", ""],  # P
        ["t", ""],  # T
        ["j", ""],  # J
        ["c", "h"],  # CH
        ["x", ""],  # X
        ["d", ""],  # D
        ["r", ""],  # R
        ["z", ""],  # Z
        ["z", "h"],  # ZH
        ["s", ""],  # S
        ["s", "h"],  # SH
        ["f", ""],  # F
        ["q", ""],  # Q
        ["k", ""],  # K
        ["g", ""],  # G
        ["g", "h"],  # GH
        ["l", ""],  # L
        ["m", ""],  # M
        ["n", ""],  # N
        ["n", "g"],  # NG
        ["h", ""],  # H
        ["o", ""],  # O
        ["u", ""],  # U
        ["ö", ""],  # Ö
        ["ü", ""],  # Ü
        ["w", ""],  # W
        ["é", ""],  # É
        ["i", ""],  # I
        ["y", ""],  # Y
        [",", ""],  # comma
        [";", ""],  # semicolon
        ["?", ""],  # question mark
    ]

    # Keyboard layout mapping (ASCII position -> Arabic Unicode)
    KEYBOARD_LAYOUT = [
        0x0020,  # (space)
        0x0021,  # !
        0x0022,  # "
        0x0023,  # #
        0x0024,  # $
        0x0025,  # %
        0x0026,  # &
        0x0027,  # '
        0x0029,  # ) [swapped with (]
        0x0028,  # ( [swapped with )]
        0x002A,  # *
        0x002B,  # +
        0x060C,  # , (Arabic comma)
        0x002D,  # -
        0x002E,  # .
        0x0626,  # /
        0x0030,  # 0
        0x0031,  # 1
        0x0032,  # 2
        0x0033,  # 3
        0x0034,  # 4
        0x0035,  # 5
        0x0036,  # 6
        0x0037,  # 7
        0x0038,  # 8
        0x0039,  # 9
        0x003A,  # :
        0x061B,  # ; (Arabic semicolon)
        0x003E,  # <
        0x003D,  # =
        0x003C,  # >
        0x061F,  # ? (Arabic question mark)
        0x0040,  # @
        0x0000,  # A
        0x0000,  # B
        0x0000,  # C
        0x0698,  # D (ZH)
        0x0000,  # E
        0x0641,  # F
        0x06AF,  # G
        0x062E,  # H (X)
        0x0000,  # I
        0x062C,  # J
        0x06C6,  # K (Ö)
        0x0000,  # L -> LA (0x0644 0x0627)
        0x0000,  # M
        0x0000,  # N
        0x0000,  # O
        0x0000,  # P
        0x0000,  # Q
        0x0000,  # R
        0x0000,  # S
        0x0000,  # T
        0x0000,  # U
        0x0000,  # V
        0x0000,  # W
        0x0000,  # X
        0x0000,  # Y
        0x0000,  # Z
        0x005D,  # [
        0x005C,  # \\ (backslash)
        0x005B,  # ]
        0x005E,  # ^
        0x005F,  # _
        0x0060,  # `
        0x06BE,  # a (H)
        0x0628,  # b
        0x063A,  # c (GH)
        0x062F,  # d
        0x06D0,  # e (É)
        0x0627,  # f (alef)
        0x06D5,  # g (E)
        0x0649,  # h (I)
        0x06AD,  # i (NG)
        0x0642,  # j (Q)
        0x0643,  # k
        0x0644,  # l
        0x0645,  # m
        0x0646,  # n
        0x0648,  # o
        0x067E,  # p
        0x0686,  # q (CH)
        0x0631,  # r
        0x0633,  # s
        0x062A,  # t
        0x06C7,  # u
        0x06C8,  # v (Ü)
        0x06CB,  # w
        0x0634,  # x (SH)
        0x064A,  # y
        0x0632,  # z
        0x00BB,  # {
        0x007C,  # |
        0x00AB,  # }
        0x007E,  # ~
    ]

    def __init__(self):
        super().__init__(block_start=0x0600, block_end=0x0700)
        self.on_clear(reset=True)

    # --- Public API ---

    def on_clear(self, reset: bool = False) -> None:
        """Clear Uyghur input state."""
        super().on_clear(reset)

    def on_input(self, code: int) -> EInput:
        """
        Process character input using Uyghur keyboard layout.

        Maps ASCII keyboard input to Uyghur Arabic Unicode.
        """
        if 0x0020 <= code < 0x007F:
            idx = code - 0x20
            if idx < len(self.KEYBOARD_LAYOUT):
                mapping = self.KEYBOARD_LAYOUT[idx]

                # Special case: L -> LA ligature
                if code == ord("L"):
                    self.str_output = chr(0x0644) + chr(0x0627)
                    return EInput.FINISHED

                if mapping == ZERO_16:
                    return EInput.NULL

                self.ch_output = mapping
                return EInput.CHARACTER

        return EInput.CHARACTER

    def on_return(self) -> EInput:
        return EInput.FINISHED

    def do_conversion(
        self, menu_id: int, text_in: str, start: int = 0, end: int = None, skip_ascii: bool = False
    ) -> tuple:
        """
        Perform Uyghur script conversion.

        menu_id=0: Arabic -> Latin
        menu_id=1: Latin -> Arabic

        Returns:
            Tuple of (converted_text, conversion_count).
        """
        if end is None:
            end = len(text_in)

        self.on_clear(reset=True)

        if menu_id == 0:  # Arabic -> Latin
            return self._convert_to_latin(text_in, start, end)
        elif menu_id == 1:  # Latin -> Arabic
            return self._convert_to_arabic(text_in, start, end)

        return text_in[start:end], 0

    # --- Private: Arabic -> Latin ---

    def _convert_to_latin(self, text: str, start: int, end: int) -> tuple:
        """Convert Uyghur Arabic script to Latin transcription."""
        result = ""
        count = 0
        prev_in = ZERO_16
        last_out = "\x00"
        pending_apos = False

        # Build lookup dict from Arabic to Latin
        arabic_to_latin = {}
        for i, ar in enumerate(self.UYGHUR_ARABIC):
            if i < len(self.UYGHUR_LATIN):
                arabic_to_latin[ar] = (self.UYGHUR_LATIN[i][0], self.UYGHUR_LATIN[i][1])

        vowels = {"a", "e", "i", "o", "u", "ö", "ü", "é"}

        for i in range(start, end):
            ch_in = ord(text[i])
            out_ch = text[i]
            out_latin = ["", ""]

            # Check if Arabic range character
            if 0x0600 <= ch_in < 0x0700:
                if ch_in in arabic_to_latin:
                    lat = arabic_to_latin[ch_in]
                    out_latin = [lat[0], lat[1]]
                    out_ch = ""
                    count += 1

            # Handle apostrophe between vowels
            if pending_apos:
                pending_apos = False
                vowel_before = last_out in vowels
                vowel_after = out_latin[0] in vowels

                if not vowel_before or not vowel_after:
                    result += "'"

            # Handle hamza (0x0626) - ignore between consonants
            if ch_in == 0x0626:
                out_ch = ""
                for j, ar in enumerate(self.UYGHUR_ARABIC):
                    if prev_in == ar:
                        pending_apos = True
                        break

            if out_ch:
                result += out_ch
                last_out = "\x00"
            else:
                # Check for n-g, s-h, g-h ambiguity
                if (
                    (last_out == "n" and out_latin[0] == "g")
                    or (last_out == "s" and out_latin[0] == "h")
                    or (last_out == "g" and out_latin[0] == "h")
                ):
                    result += "'"

                if out_latin[0]:
                    result += out_latin[0]
                    last_out = out_latin[0]
                if out_latin[1]:
                    result += out_latin[1]
                    last_out = out_latin[1]

            prev_in = ch_in

        return result, count

    # --- Private: Latin -> Arabic ---

    def _convert_to_arabic(self, text: str, start: int, end: int) -> tuple:
        """Convert Latin transcription to Uyghur Arabic script."""
        result = ""
        count = 0
        pending = ZERO_16
        last_in = "\x00"
        bracket_count = 0

        vowels = {"a", "e", "i", "o", "u", "ö", "ü", "é"}

        for i in range(start, end):
            ch = text[i]
            code = ord(ch)

            # Handle brackets
            if ch == "[":
                bracket_count += 1
                if bracket_count > 1:
                    result += ch
                continue
            if ch == "]":
                if bracket_count > 0:
                    bracket_count -= 1
                if bracket_count > 0:
                    result += ch
                continue

            if bracket_count:
                result += ch
                continue

            out_ch = ch
            in_latin = ch.lower()

            if pending:
                for j, lat in enumerate(self.UYGHUR_LATIN):
                    if last_in == lat[0] and in_latin == lat[1] and j < len(self.UYGHUR_ARABIC):
                        pending = self.UYGHUR_ARABIC[j]
                        out_ch = ""
                        in_latin = "\x00"
                        break

                if pending:
                    result += chr(pending)
                    pending = ZERO_16
                    count += 1

            # Look up single character mapping
            for j, lat in enumerate(self.UYGHUR_LATIN):
                if in_latin == lat[0] and j < len(self.UYGHUR_ARABIC):
                    if lat[1]:
                        # Multi-character pending
                        if j + 1 < len(self.UYGHUR_LATIN) and self.UYGHUR_LATIN[j + 1][0] == in_latin:
                            pending = ch
                        else:
                            pending = self.UYGHUR_ARABIC[j]
                        out_ch = ""
                    else:
                        out_ch = chr(self.UYGHUR_ARABIC[j])
                        count += 1
                    break

            # Insert hamza between vowels
            vowel_before = last_in in vowels
            vowel_after = in_latin in vowels

            if vowel_before and vowel_after:
                result += chr(0x0626)
            elif last_in == "'":
                if vowel_before or vowel_after:
                    result += chr(0x0626)
            elif vowel_after:
                if last_in and (last_in < "a" or last_in > "z"):
                    result += chr(0x0626)

            if out_ch:
                result += out_ch

            last_in = in_latin

        if pending != ZERO_16:
            result += chr(pending)

        return result, count
