"""Unicode property enums — ported from c/Unicode/."""

from enum import IntEnum


class GeneralCategory(IntEnum):
    Cn = 0
    Lu = 1
    Ll = 2
    Lt = 3
    Lm = 4
    Lo = 5
    Mn = 6
    Mc = 7
    Me = 8
    Nd = 9
    Nl = 10
    No = 11
    Zs = 12
    Zl = 13
    Zp = 14
    Cc = 15
    Cf = 16
    Cs = 17
    Co = 18
    Pc = 20
    Pd = 21
    Ps = 22
    Pe = 23
    Pi = 24
    Pf = 25
    Po = 26
    Sm = 27
    Sc = 28
    Sk = 29
    So = 30


class BidiClass(IntEnum):
    L = 0
    R = 1
    AL = 2
    EN = 3
    ES = 4
    ET = 5
    AN = 6
    CS = 7
    NSM = 8
    BN = 9
    B = 10
    S = 11
    WS = 12
    ON = 13
    LRE = 14
    LRO = 15
    RLE = 16
    RLO = 17
    PDF = 18
    LRI = 19
    RLI = 20
    FSI = 21
    PDI = 22


class DecompositionType(IntEnum):
    None_ = 0
    Canon = 1
    Font = 2
    NoBreak = 3
    Initial = 4
    Medial = 5
    Final = 6
    Isolated = 7
    Circle = 8
    Super = 9
    Sub = 10
    Vertical = 11
    Wide = 12
    Narrow = 13
    Small = 14
    Square = 15
    Fraction = 16
    Compat = 17


class EastAsianWidth(IntEnum):
    N = 0
    A = 1
    H = 2
    W = 3
    F = 4
    Na = 5


class LineBreak(IntEnum):
    XX = 0
    AI = 1
    AL = 2
    B2 = 3
    BA = 4
    BB = 5
    BK = 6
    CB = 7
    CJ = 8
    CL = 9
    CM = 10
    CP = 11
    CR = 12
    EB = 13
    EM = 14
    EX = 15
    GL = 16
    H2 = 17
    H3 = 18
    HL = 19
    HY = 20
    ID = 21
    IN = 22
    IS = 23
    JL = 24
    JV = 25
    JT = 26
    LF = 27
    NL = 28
    NS = 29
    NU = 30
    OP = 31
    PO = 32
    PR = 33
    QU = 34
    RI = 35
    SA = 36
    SG = 37
    SP = 38
    SY = 39
    WJ = 40
    ZW = 41
    ZWJ = 42


class JoiningType(IntEnum):
    U = 0
    C = 1
    D = 2
    R = 3
    L = 4
    T = 5


GC_SHORT = {v: k for k, v in GeneralCategory.__members__.items()}
