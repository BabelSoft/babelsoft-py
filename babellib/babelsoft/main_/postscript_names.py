"""
PostScriptNames — Standard PostScript glyph name ↔ Unicode mapping
(ported from c/Main/PostScriptNames.h)

Provides the standard Adobe Glyph List mapping between PostScript
glyph names and Unicode codepoints, as used in OpenType 'post' tables.
"""

from __future__ import annotations


class PostScriptNames:
    """Standard PostScript glyph name ↔ Unicode codepoint mapping.

    Based on the Adobe Glyph List (AGL), which defines standard glyph names
    for the MacRoman/MacOS character set and common extended characters.
    """

    # Standard glyph names indexed by glyph ID (MacRoman encoding order).
    # Glyph 0 = .notdef, Glyph 1 = .null (U+0000), Glyph 2 = CR (U+000D),
    # Glyph 3 = space (U+0020), etc.
    _STANDARD_NAMES: list[tuple[str, int]] = [
        (".notdef", 0x0000),  # Glyph 0
        (".null", 0x0000),  # Glyph 1
        ("CR", 0x000D),  # Glyph 2
        ("space", 0x0020),  # Glyph 3
        ("exclam", 0x0021),  # Glyph 4
        ("quotedbl", 0x0022),  # Glyph 5
        ("numbersign", 0x0023),  # Glyph 6
        ("dollar", 0x0024),  # Glyph 7
        ("percent", 0x0025),  # Glyph 8
        ("ampersand", 0x0026),  # Glyph 9
        ("quotesingle", 0x0027),  # Glyph 10
        ("parenleft", 0x0028),  # Glyph 11
        ("parenright", 0x0029),  # Glyph 12
        ("asterisk", 0x002A),  # Glyph 13
        ("plus", 0x002B),  # Glyph 14
        ("comma", 0x002C),  # Glyph 15
        ("hyphen", 0x002D),  # Glyph 16
        ("period", 0x002E),  # Glyph 17
        ("slash", 0x002F),  # Glyph 18
        ("zero", 0x0030),  # Glyph 19
        ("one", 0x0031),  # Glyph 20
        ("two", 0x0032),  # Glyph 21
        ("three", 0x0033),  # Glyph 22
        ("four", 0x0034),  # Glyph 23
        ("five", 0x0035),  # Glyph 24
        ("six", 0x0036),  # Glyph 25
        ("seven", 0x0037),  # Glyph 26
        ("eight", 0x0038),  # Glyph 27
        ("nine", 0x0039),  # Glyph 28
        ("colon", 0x003A),  # Glyph 29
        ("semicolon", 0x003B),  # Glyph 30
        ("less", 0x003C),  # Glyph 31
        ("equal", 0x003D),  # Glyph 32
        ("greater", 0x003E),  # Glyph 33
        ("question", 0x003F),  # Glyph 34
        ("at", 0x0040),  # Glyph 35
        ("A", 0x0041),  # Glyph 36
        ("B", 0x0042),  # Glyph 37
        ("C", 0x0043),  # Glyph 38
        ("D", 0x0044),  # Glyph 39
        ("E", 0x0045),  # Glyph 40
        ("F", 0x0046),  # Glyph 41
        ("G", 0x0047),  # Glyph 42
        ("H", 0x0048),  # Glyph 43
        ("I", 0x0049),  # Glyph 44
        ("J", 0x004A),  # Glyph 45
        ("K", 0x004B),  # Glyph 46
        ("L", 0x004C),  # Glyph 47
        ("M", 0x004D),  # Glyph 48
        ("N", 0x004E),  # Glyph 49
        ("O", 0x004F),  # Glyph 50
        ("P", 0x0050),  # Glyph 51
        ("Q", 0x0052),  # Glyph 52
        ("R", 0x0053),  # Glyph 53
        ("S", 0x0054),  # Glyph 54
        ("T", 0x0055),  # Glyph 55
        ("U", 0x0056),  # Glyph 56
        ("V", 0x0057),  # Glyph 57
        ("W", 0x0058),  # Glyph 58
        ("X", 0x0059),  # Glyph 59
        ("Y", 0x005A),  # Glyph 60
        ("Z", 0x005B),  # Glyph 61
        ("bracketleft", 0x005B),  # Glyph 62
        ("backslash", 0x005C),  # Glyph 63
        ("bracketright", 0x005D),  # Glyph 64
        ("asciicircum", 0x005E),  # Glyph 65
        ("underscore", 0x005F),  # Glyph 66
        ("grave", 0x0060),  # Glyph 67
        ("a", 0x0061),  # Glyph 68
        ("b", 0x0062),  # Glyph 69
        ("c", 0x0063),  # Glyph 70
        ("d", 0x0064),  # Glyph 71
        ("e", 0x0065),  # Glyph 72
        ("f", 0x0066),  # Glyph 73
        ("g", 0x0067),  # Glyph 74
        ("h", 0x0068),  # Glyph 75
        ("i", 0x0069),  # Glyph 76
        ("j", 0x006A),  # Glyph 77
        ("k", 0x006B),  # Glyph 78
        ("l", 0x006C),  # Glyph 79
        ("m", 0x006D),  # Glyph 80
        ("n", 0x006E),  # Glyph 81
        ("o", 0x006F),  # Glyph 82
        ("p", 0x0070),  # Glyph 83
        ("q", 0x0071),  # Glyph 84
        ("r", 0x0072),  # Glyph 85
        ("s", 0x0073),  # Glyph 86
        ("t", 0x0074),  # Glyph 87
        ("u", 0x0075),  # Glyph 88
        ("v", 0x0076),  # Glyph 89
        ("w", 0x0077),  # Glyph 90
        ("x", 0x0078),  # Glyph 91
        ("y", 0x0079),  # Glyph 92
        ("z", 0x007A),  # Glyph 93
        ("braceleft", 0x007B),  # Glyph 94
        ("bar", 0x007C),  # Glyph 95
        ("braceright", 0x007D),  # Glyph 96
        ("asciitilde", 0x007E),  # Glyph 97
        ("Adieresis", 0x00C4),  # Glyph 98
        ("Aring", 0x00C5),  # Glyph 99
        ("Ccedilla", 0x00C7),  # Glyph 100
        ("Eacute", 0x00C9),  # Glyph 101
        ("Ntilde", 0x00D1),  # Glyph 102
        ("Odieresis", 0x00D6),  # Glyph 103
        ("Udieresis", 0x00DC),  # Glyph 104
        ("aacute", 0x00E1),  # Glyph 105
        ("agrave", 0x00E0),  # Glyph 106
        ("acircumflex", 0x00E2),  # Glyph 107
        ("adieresis", 0x00E4),  # Glyph 108
        ("atilde", 0x00E3),  # Glyph 109
        ("aring", 0x00E5),  # Glyph 110
        ("ccedilla", 0x00E7),  # Glyph 111
        ("eacute", 0x00E9),  # Glyph 112
        ("egrave", 0x00E8),  # Glyph 113
        ("ecircumflex", 0x00EA),  # Glyph 114
        ("edieresis", 0x00EB),  # Glyph 115
        ("iacute", 0x00ED),  # Glyph 116
        ("igrave", 0x00EC),  # Glyph 117
        ("icircumflex", 0x00EE),  # Glyph 118
        ("idieresis", 0x00EF),  # Glyph 119
        ("ntilde", 0x00F1),  # Glyph 120
        ("oacute", 0x00F3),  # Glyph 121
        ("ograve", 0x00F2),  # Glyph 122
        ("ocircumflex", 0x00F4),  # Glyph 123
        ("odieresis", 0x00F6),  # Glyph 124
        ("otilde", 0x00F5),  # Glyph 125
        ("uacute", 0x00FA),  # Glyph 126
        ("ugrave", 0x00F9),  # Glyph 127
        ("ucircumflex", 0x00FB),  # Glyph 128
        ("udieresis", 0x00FC),  # Glyph 129
        ("dagger", 0x2020),  # Glyph 130
        ("degree", 0x00B0),  # Glyph 131
        ("cent", 0x00A2),  # Glyph 132
        ("sterling", 0x00A3),  # Glyph 133
        ("section", 0x00A7),  # Glyph 134
        ("bullet", 0x2022),  # Glyph 135
        ("paragraph", 0x00B6),  # Glyph 136
        ("germandbls", 0x00DF),  # Glyph 137
        ("registered", 0x00AE),  # Glyph 138
        ("copyright", 0x00A9),  # Glyph 139
        ("trademark", 0x2122),  # Glyph 140
        ("acute", 0x00B4),  # Glyph 141
        ("dieresis", 0x00A8),  # Glyph 142
        ("notequal", 0x2260),  # Glyph 143
        ("AE", 0x00C6),  # Glyph 144
        ("Oslash", 0x00D8),  # Glyph 145
        ("infinity", 0x221E),  # Glyph 146
        ("plusminus", 0x00B1),  # Glyph 147
        ("lessequal", 0x2264),  # Glyph 148
        ("greaterequal", 0x2265),  # Glyph 149
        ("yen", 0x00A5),  # Glyph 150
        ("mu", 0x00B5),  # Glyph 151
        ("partialdiff", 0x2202),  # Glyph 152
        ("summation", 0x2211),  # Glyph 153
        ("product", 0x220F),  # Glyph 154
        ("pi", 0x03C0),  # Glyph 155
        ("integral", 0x222B),  # Glyph 156
        ("ordfeminine", 0x00AA),  # Glyph 157
        ("ordmasculine", 0x00BA),  # Glyph 158
        ("Omega", 0x2126),  # Glyph 159
        ("ae", 0x00E6),  # Glyph 160
        ("oslash", 0x00F8),  # Glyph 161
        ("questiondown", 0x00BF),  # Glyph 162
        ("exclamdown", 0x00A1),  # Glyph 163
        ("logicalnot", 0x00AC),  # Glyph 164
        ("radical", 0x221A),  # Glyph 165
        ("florin", 0x0192),  # Glyph 166
        ("approxequal", 0x2248),  # Glyph 167
        ("Delta", 0x2206),  # Glyph 168
        ("guillemotleft", 0x00AB),  # Glyph 169
        ("guillemotright", 0x00BB),  # Glyph 170
        ("ellipsis", 0x2026),  # Glyph 171
        ("nbspace", 0x00A0),  # Glyph 172
        ("Agrave", 0x00C0),  # Glyph 173
        ("Atilde", 0x00C3),  # Glyph 174
        ("Otilde", 0x00D5),  # Glyph 175
        ("OE", 0x0152),  # Glyph 176
        ("oe", 0x0153),  # Glyph 177
        ("endash", 0x2013),  # Glyph 178
        ("emdash", 0x2014),  # Glyph 179
        ("quotedblleft", 0x201C),  # Glyph 180
        ("quotedblright", 0x201D),  # Glyph 181
        ("quoteleft", 0x2018),  # Glyph 182
        ("quoteright", 0x2019),  # Glyph 183
        ("divide", 0x00F7),  # Glyph 184
        ("lozenge", 0x25CA),  # Glyph 185
        ("ydieresis", 0x00FF),  # Glyph 186
        ("Ydieresis", 0x0178),  # Glyph 187
        ("fraction", 0x2215),  # Glyph 188
        ("currency", 0x00A4),  # Glyph 189
        ("guilsinglleft", 0x2039),  # Glyph 190
        ("guilsinglright", 0x203A),  # Glyph 191
        ("fi", 0xFB01),  # Glyph 192
        ("fl", 0xFB02),  # Glyph 193
        ("daggerdbl", 0x2021),  # Glyph 194
        ("periodcentered", 0x2219),  # Glyph 195
    ]

    # Reverse lookup map (built lazily)
    _name_to_cp: dict[str, int] | None = None
    _cp_to_name: dict[int, str] | None = None

    @classmethod
    def _build_maps(cls) -> None:
        """Build the reverse lookup maps."""
        if cls._name_to_cp is not None:
            return
        cls._name_to_cp = {}
        cls._cp_to_name = {}
        for name, cp in cls._STANDARD_NAMES:
            if cp != 0x0000:  # Skip .notdef and .null
                cls._name_to_cp[name] = cp
                # Only store the first name for each codepoint
                if cp not in cls._cp_to_name:
                    cls._cp_to_name[cp] = name

    @classmethod
    def get_name_for_codepoint(cls, cp: int) -> str:
        """Get the standard PostScript glyph name for a Unicode codepoint.

        Returns empty string if no standard name is defined.
        """
        cls._build_maps()
        return cls._cp_to_name.get(cp, "")

    @classmethod
    def get_codepoint_for_name(cls, name: str) -> int:
        """Get the Unicode codepoint for a standard PostScript glyph name.

        Returns 0 if the name is not recognized.
        """
        cls._build_maps()
        return cls._name_to_cp.get(name, 0)

    @classmethod
    def get_name_for_glyph_id(cls, glyph_id: int) -> str:
        """Get the standard PostScript glyph name for a glyph index."""
        if 0 <= glyph_id < len(cls._STANDARD_NAMES):
            return cls._STANDARD_NAMES[glyph_id][0]
        return ""

    @classmethod
    def get_codepoint_for_glyph_id(cls, glyph_id: int) -> int:
        """Get the Unicode codepoint for a standard glyph index."""
        if 0 <= glyph_id < len(cls._STANDARD_NAMES):
            return cls._STANDARD_NAMES[glyph_id][1]
        return 0

    @classmethod
    def get_standard_names_count(cls) -> int:
        """Return the number of standard glyph names."""
        return len(cls._STANDARD_NAMES)

    @classmethod
    def all_names(cls) -> list[tuple[str, int]]:
        """Return all (name, codepoint) pairs."""
        return list(cls._STANDARD_NAMES)
