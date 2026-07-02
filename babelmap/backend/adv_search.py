"""Advanced character search: property definitions, tokenizer, AST parser, evaluator."""

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from src.unicode.core import Unicode

# ── Property definitions ───────────────────────────────────────────

ADV_PROPS: list[dict[str, Any]] = [
    {"key": "name", "label": "Name", "type": "text", "desc": "|cc starts, cc| ends, |cc| exact, cc contains"},
    {"key": "formalalias", "label": "FormalAlias", "type": "text", "desc": "Formal name alias"},
    {"key": "unicode1name", "label": "Unicode1Name", "type": "text", "desc": "Unicode 1.0 name"},
    {"key": "aliases", "label": "Aliases", "type": "text", "desc": "All names & aliases"},
    {"key": "notes", "label": "Notes", "type": "text", "desc": "Character notes"},
    {"key": "crossreferences", "label": "CrossReferences", "type": "text", "desc": "Cross references"},
    {
        "key": "wholewords",
        "label": "WholeWords",
        "type": "bool",
        "values": ["True", "False"],
        "desc": "Match whole words only",
    },
    {
        "key": "gc",
        "label": "GeneralCategory",
        "type": "enum",
        "alias": ["general_category", "generalcategory"],
        "values": [
            "Lu",
            "Ll",
            "Lt",
            "Lm",
            "Lo",
            "Mn",
            "Mc",
            "Me",
            "Nd",
            "Nl",
            "No",
            "Pc",
            "Pd",
            "Ps",
            "Pe",
            "Pi",
            "Pf",
            "Po",
            "Sm",
            "Sc",
            "Sk",
            "So",
            "Zs",
            "Zl",
            "Zp",
            "Cc",
            "Cf",
            "Cs",
            "Co",
            "Cn",
        ],
    },
    {
        "key": "ccc",
        "label": "CanonicalCombiningClass",
        "type": "text",
        "alias": ["canonical_combining_class", "canonicalcombiningclass"],
        "desc": "0-240 (comma-separated)",
    },
    {
        "key": "bc",
        "label": "BidiClass",
        "type": "enum",
        "alias": ["bidi_class", "bidiclass"],
        "values": [
            "L",
            "R",
            "AL",
            "EN",
            "ES",
            "ET",
            "AN",
            "CS",
            "NSM",
            "BN",
            "B",
            "S",
            "WS",
            "ON",
            "LRE",
            "LRO",
            "RLE",
            "RLO",
            "PDF",
            "LRI",
            "RLI",
            "FSI",
            "PDI",
        ],
    },
    {
        "key": "bm",
        "label": "BidiMirrored",
        "type": "bool",
        "alias": ["bidi_mirrored", "bidimirrored"],
        "values": ["True", "False"],
    },
    {
        "key": "dt",
        "label": "DecompositionType",
        "type": "text",
        "alias": ["decomposition_type", "decompositiontype"],
        "desc": "canonical, compat, circle, font, etc.",
    },
    {
        "key": "nt",
        "label": "NumericType",
        "type": "text",
        "alias": ["numeric_type", "numerictype"],
        "desc": "Decimal, Digit, Numeric, None",
    },
    {
        "key": "lb",
        "label": "LineBreak",
        "type": "text",
        "alias": ["line_break", "linebreak"],
        "desc": "AK, AL, BB, BK, etc.",
    },
    {
        "key": "binary",
        "label": "BinaryProperty",
        "type": "text",
        "alias": ["binary_property", "binaryproperty"],
        "desc": "Dash, Math, Emoji, ID_Start, etc.",
    },
    {"key": "script", "label": "Script", "type": "text", "desc": "ISO 15924 script (comma-separated)"},
    {"key": "block", "label": "Block", "type": "text", "desc": "Unicode block name"},
    {
        "key": "unicode",
        "label": "Unicode",
        "type": "version",
        "desc": "Unicode version: 5.0, >=5.0, <=5.0",
    },
    {
        "key": "nocjkui",
        "label": "NoCJKUI",
        "type": "bool",
        "alias": ["nocjk"],
        "values": ["True", "False"],
        "desc": "Exclude CJK Unified Ideographs",
    },
    {
        "key": "nopua",
        "label": "NoPUA",
        "type": "bool",
        "values": ["True", "False"],
        "desc": "Exclude Private Use Areas",
    },
]


def matching_properties(q: str) -> list[dict[str, Any]]:
    """Return property definitions matching the query (for autocomplete)."""
    results = []
    qu = q.lower().strip()
    for p in ADV_PROPS:
        keys = [p["key"]] + p.get("alias", [])
        if not qu or any(qu in k for k in keys) or qu in p["label"].lower():
            results.append(
                {
                    "key": p["key"],
                    "label": p["label"],
                    "type": p["type"],
                    "values": p.get("values"),
                    "desc": p.get("desc", ""),
                }
            )
    return results


# ── Pipe boundary syntax ───────────────────────────────────────────

_PIPE_FIELDS = {"name", "formalalias", "unicode1name", "aliases"}


def _convert_pipe_to_wildcard(val: str) -> tuple[str, bool]:
    """Convert | boundary syntax to fnmatch wildcard pattern.

    Returns (converted_value, force_wildcard).
    """
    if not val:
        return val, False

    has_left = val.startswith("|")
    has_right = val.endswith("|")

    if has_left and has_right:
        return val[1:-1], True  # |cc| → cc  (exact via fnmatch)
    elif has_left:
        return val[1:] + "*", True  # |cc → cc*
    elif has_right:
        return "*" + val[:-1], True  # cc| → *cc
    else:
        return "*" + val + "*", True  # cc → *cc*


# ═══════════════════════════════════════════════════════════════════
#  Tokenizer
# ═══════════════════════════════════════════════════════════════════


class TokenType(Enum):
    IDENT = auto()
    OP = auto()
    VALUE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    text: str
    pos: int = 0


_OP_SET = {"=", "!=", ">=", "<=", ">", "<", ":"}
# Sort by length descending so longer ops match first
_OPS_SORTED = sorted(_OP_SET, key=len, reverse=True)


def _tokenize(q: str) -> list[Token]:
    """Tokenize a query string into a list of tokens."""
    tokens: list[Token] = []
    i = 0
    n = len(q)

    while i < n:
        ch = q[i]

        # Skip whitespace
        if ch.isspace():
            i += 1
            continue

        # Parentheses
        if ch == "(":
            tokens.append(Token(TokenType.LPAREN, "(", i))
            i += 1
            continue
        if ch == ")":
            tokens.append(Token(TokenType.RPAREN, ")", i))
            i += 1
            continue

        # Quoted string (single or double)
        if ch in ('"', "'"):
            quote = ch
            j = i + 1
            while j < n and q[j] != quote:
                j += 1
            val = q[i + 1 : j]
            tokens.append(Token(TokenType.VALUE, val, i))
            i = j + 1 if j < n else n
            continue

        # Operator — try longest match first
        matched = False
        for op in _OPS_SORTED:
            if q[i : i + len(op)] == op:
                tokens.append(Token(TokenType.OP, op, i))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        # Word: AND / OR / NOT (case-insensitive)
        if ch.isalpha():
            j = i
            while j < n and q[j].isalpha():
                j += 1
            word = q[i:j].upper()
            if word == "AND":
                tokens.append(Token(TokenType.AND, word, i))
            elif word == "OR":
                tokens.append(Token(TokenType.OR, word, i))
            elif word == "NOT":
                tokens.append(Token(TokenType.NOT, word, i))
            else:
                # It's an identifier (property key)
                tokens.append(Token(TokenType.IDENT, q[i:j], i))
            i = j
            continue

        # Otherwise, treat as value (catch-all: numbers, punctuation, etc.)
        j = i
        while j < n and not q[j].isspace() and q[j] not in "()":
            if q[j] in "=!><:" and j > i:
                break
            j += 1
        tokens.append(Token(TokenType.VALUE, q[i:j], i))
        i = j

    tokens.append(Token(TokenType.EOF, "", n))

    # Post-process: after an OP, merge consecutive IDENT/VALUE into one VALUE
    # so "Latn,Hani" becomes one VALUE instead of IDENT + VALUE.
    merged: list[Token] = []
    m = len(tokens)
    k = 0
    while k < m:
        tok = tokens[k]
        if tok.type == TokenType.OP:
            merged.append(tok)
            k += 1
            if k < m and tokens[k].type in (TokenType.IDENT, TokenType.VALUE):
                parts: list[str] = []
                start_pos = tokens[k].pos
                while k < m and tokens[k].type in (TokenType.IDENT, TokenType.VALUE):
                    parts.append(tokens[k].text)
                    k += 1
                merged.append(Token(TokenType.VALUE, "".join(parts), start_pos))
        else:
            merged.append(tok)
            k += 1

    return merged


# ═══════════════════════════════════════════════════════════════════
#  AST nodes
# ═══════════════════════════════════════════════════════════════════


@dataclass
class Cond:
    """Leaf node: a single property condition like name=lisu."""

    key: str
    op: str  # =, !=, >=, <=, :, >, <
    value: str  # raw value
    negate: bool = False  # from != or NOT
    wildcard: bool = False  # value contains * or ?
    comma: bool = False  # comma-separated values
    values: list[str] = field(default_factory=list)


@dataclass
class BinOp:
    """Binary logical operation: AND / OR."""

    left: "ASTNode"
    op: str  # 'AND' | 'OR'
    right: "ASTNode"


@dataclass
class NotOp:
    """Unary NOT operation."""

    expr: "ASTNode"


# Union type for AST nodes
ASTNode = Cond | BinOp | NotOp


# ═══════════════════════════════════════════════════════════════════
#  Recursive-descent parser
# ═══════════════════════════════════════════════════════════════════
#
#  Grammar (precedence: NOT > AND > OR):
#    expr     = or_expr
#    or_expr  = and_expr ("OR" and_expr)*
#    and_expr = not_expr ("AND" not_expr)*
#    not_expr = "NOT" not_expr | primary
#    primary  = condition | "(" expr ")"
#    condition = IDENT OP VALUE
#


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    @property
    def _cur(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._cur
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def _expect(self, t: TokenType, msg: str = "") -> Token:
        if self._cur.type != t:
            raise ParseError(msg or f"Expected {t.name}, got {self._cur.type.name} ({self._cur.text!r})")
        return self._advance()

    def parse(self) -> ASTNode | None:
        """Parse the token stream into an AST. Returns None for empty input."""
        if self._cur.type == TokenType.EOF:
            return None
        ast = self._parse_or()
        if self._cur.type != TokenType.EOF:
            raise ParseError(f"Unexpected token: {self._cur.type.name} ({self._cur.text!r})")
        return ast

    # ── or_expr = and_expr ("OR" and_expr)* ──
    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        while self._cur.type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = BinOp(left, "OR", right)
        return left

    # ── and_expr = not_expr ("AND" not_expr)* ──
    def _parse_and(self) -> ASTNode:
        left = self._parse_not()
        while self._cur.type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = BinOp(left, "AND", right)
        return left

    # ── not_expr = "NOT" not_expr | primary ──
    def _parse_not(self) -> ASTNode:
        if self._cur.type == TokenType.NOT:
            self._advance()
            return NotOp(self._parse_not())
        return self._parse_primary()

    # ── primary = condition | "(" expr ")" ──
    def _parse_primary(self) -> ASTNode:
        if self._cur.type == TokenType.LPAREN:
            self._advance()
            ast = self._parse_or()
            self._expect(TokenType.RPAREN, "Expected ')'")
            return ast
        return self._parse_condition()

    # ── condition = IDENT OP (VALUE|IDENT)  |  bare (VALUE|IDENT) ──
    def _parse_condition(self) -> Cond:
        if self._cur.type not in (TokenType.IDENT, TokenType.VALUE):
            raise ParseError(f"Expected property name or value, got {self._cur.type.name}")

        first = self._advance()

        # Look ahead: if followed by OP or another IDENT/VALUE, this is key=value
        if self._cur.type in (TokenType.OP, TokenType.IDENT, TokenType.VALUE):
            key = first.text
            if self._cur.type in (TokenType.IDENT, TokenType.VALUE):
                op = "="  # implicit equals: "script Latin" means script=Latin
            else:
                op_tok = self._advance()
                op = op_tok.text
                if self._cur.type not in (TokenType.IDENT, TokenType.VALUE):
                    raise ParseError(f"Expected value after operator {op}")
            val_tok = self._advance()
            return self._build_cond(key, op, val_tok.text)
        else:
            # Bare value → implicit name=value
            return self._build_cond("name", "=", first.text)

    def _build_cond(self, key: str, op: str, val: str) -> Cond:
        """Build a Cond node, applying pipe conversion for text fields."""
        key_lower = key.strip().lower()
        val = val.strip().strip('"').strip("'")
        negate = op == "!="
        wildcard = False
        comma = False
        values: list[str] = []

        # Apply pipe | boundary syntax for text name fields
        _force_wc = False
        if op == "=" and key_lower in _PIPE_FIELDS:
            val, _force_wc = _convert_pipe_to_wildcard(val)
            # Comma → space: "tangut,ideograph" matches "TANGUT IDEOGRAPH"
            val = val.replace(",", " ")

        if "*" in val or "?" in val or _force_wc:
            wildcard = True

        if "," in val and op not in (">=", "<="):
            comma = True
            values = [v.strip() for v in val.split(",") if v.strip()]
        else:
            values = [val]

        return Cond(
            key=key_lower,
            op=op,
            value=val,
            negate=negate,
            wildcard=wildcard,
            comma=comma,
            values=values,
        )


def parse_query(q: str) -> ASTNode | None:
    """Parse an advanced search query into an AST."""
    tokens = _tokenize(q)
    parser = Parser(tokens)
    return parser.parse()


def ast_to_text(ast: ASTNode) -> str:
    """Serialize an AST back to canonical query text."""
    if isinstance(ast, Cond):
        if ast.key == "name":
            return f"name={ast.value}"
        return f"{ast.key}={ast.value}"
    elif isinstance(ast, BinOp):
        left = ast_to_text(ast.left)
        right = ast_to_text(ast.right)
        return f"{left} {ast.op} {right}"
    elif isinstance(ast, NotOp):
        return f"NOT {ast_to_text(ast.expr)}"
    return ""


def normalize_query(q: str) -> str:
    """Parse a query and return its canonical AST form."""
    ast = parse_query(q)
    if ast is None:
        return q
    return ast_to_text(ast)


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════


def _find_block(cp: int, blocks: list[dict]) -> dict | None:
    lo, hi = 0, len(blocks) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        b = blocks[mid]
        if cp < b["start"]:
            hi = mid - 1
        elif cp > b["end"]:
            lo = mid + 1
        else:
            return b
    return None


def _resolve_key(k: str) -> dict | None:
    for p in ADV_PROPS:
        if k == p["key"] or k in p.get("alias", []):
            return p
    return None


def _match_val(val: str, target: str, wildcard: bool, whole_words: bool) -> bool:
    v, t = val.upper(), target.upper()
    if wildcard:
        return fnmatch.fnmatch(t, v)
    if whole_words:
        return bool(re.search(rf"\b{re.escape(v)}\b", t))
    return v in t


def _match_multi(val: str, vals: list[str], target: str, wildcard: bool, whole_words: bool) -> bool:
    return any(_match_val(v, target, wildcard, whole_words) for v in vals)


# ═══════════════════════════════════════════════════════════════════
#  AST evaluator — walk the tree for a single codepoint
# ═══════════════════════════════════════════════════════════════════


def _eval_cond(cond: Cond, cp: int, blocks: list[dict], whole_words: bool) -> bool:
    """Evaluate a single Condition against a codepoint."""
    prop = _resolve_key(cond.key)
    if not prop:
        return False

    key: str = prop["key"]
    val: str = cond.value
    op: str = cond.op
    negate: bool = cond.negate
    wildcard: bool = cond.wildcard
    vals: list[str] = cond.values

    try:
        # ── Name searches ──
        if key == "name":
            n = Unicode.get_character_name(cp)
            if not n:
                return negate
            return not negate if _match_multi(val, vals, n, wildcard, whole_words) else negate

        if key in ("formalalias", "unicode1name"):
            try:
                n = Unicode.get_unicode1_name(cp)
            except Exception:
                n = ""
            if not n:
                return negate
            return not negate if _match_multi(val, vals, n, wildcard, whole_words) else negate

        if key == "aliases":
            names = []
            n = Unicode.get_character_name(cp)
            if n:
                names.append(n)
            n1 = Unicode.get_unicode1_name(cp)
            if n1:
                names.append(n1)
            combined = " | ".join(names) if names else ""
            return not negate if _match_multi(val, vals, combined, wildcard, whole_words) else negate

        if key in ("notes", "crossreferences"):
            return negate

        if key == "wholewords":
            return True  # meta-flag, handled at search level

        # ── Categorical ──
        if key == "gc":
            m = str(Unicode.get_general_category(cp)).upper() in (v.upper() for v in vals)
            return not m if negate else m

        if key == "script":
            m = str(Unicode.get_script(cp)).upper() in (v.upper() for v in vals)
            return not m if negate else m

        if key == "block":
            blk = _find_block(cp, blocks)
            if not blk:
                return negate
            m = any(v.upper() in blk["name"].upper() for v in vals)
            return not m if negate else m

        if key == "bc":
            m = str(Unicode.get_bidi_class(cp)).upper() in (v.upper() for v in vals)
            return not m if negate else m

        if key == "bm":
            bm = Unicode.get_bidi_mirrored(cp)
            want = vals[0].lower() in ("true", "1", "yes")
            m = bm == want
            return not m if negate else m

        if key == "ccc":
            m = str(Unicode.get_canonical_combining_class(cp)) in vals
            return not m if negate else m

        if key == "dt":
            dt = str(Unicode.get_decomposition_type(cp))
            m = any(v.upper() in dt.upper() for v in vals)
            return not m if negate else m

        if key == "nt":
            nt = str(Unicode.get_numeric_type(cp)).upper()
            m = nt in (v.upper() for v in vals)
            return not m if negate else m

        if key == "lb":
            lb = str(Unicode.get_line_break(cp)).upper()
            m = lb in (v.upper() for v in vals)
            return not m if negate else m

        if key == "binary":
            m = any(Unicode.has_binary_property(cp, v) for v in vals)
            return not m if negate else m

        # ── Unicode version ──
        if key == "unicode":
            try:
                age = getattr(Unicode, "get_character_age", lambda c: "5.0")(cp)
            except Exception:
                age = "5.0"
            if not age:
                return True if op in (">=", ">") else negate
            m_ver = re.match(r"(\d+)\.?(\d+)?", str(age))
            m_val = re.match(r"(\d+)\.?(\d+)?", val)
            if not m_val:
                return negate
            age_num = float(f"{m_ver.group(1)}.{m_ver.group(2) or 0}") if m_ver else 5.0
            val_num = float(f"{m_val.group(1)}.{m_val.group(2) or 0}")
            if op == ">=":
                m = age_num >= val_num
            elif op == "<=":
                m = age_num <= val_num
            elif op == ">":
                m = age_num > val_num
            elif op == "<":
                m = age_num < val_num
            else:
                m = age_num == val_num
            return not m if negate else m

        # ── Exclusions ──
        if key == "nocjkui":
            want = vals[0].lower() in ("true", "1", "yes")
            blk = _find_block(cp, blocks)
            is_cjk = blk and "CJK Unified Ideograph" in blk["name"] if blk else False
            m = (not is_cjk) if want else True
            return not m if negate else m

        if key == "nopua":
            want = vals[0].lower() in ("true", "1", "yes")
            is_pua = (0xE000 <= cp <= 0xF8FF) or (0xF0000 <= cp <= 0xFFFFD) or (0x100000 <= cp <= 0x10FFFD)
            m = (not is_pua) if want else True
            return not m if negate else m

    except Exception:
        return negate

    return False


def evaluate(ast: ASTNode, cp: int, blocks: list[dict], whole_words: bool = False) -> bool:
    """Evaluate an AST against a single codepoint."""
    if isinstance(ast, Cond):
        prop = _resolve_key(ast.key)
        if prop is not None and prop["key"] == "wholewords":
            return True  # meta-flag, always passes
        return _eval_cond(ast, cp, blocks, whole_words)
    elif isinstance(ast, BinOp):
        left = evaluate(ast.left, cp, blocks, whole_words)
        if ast.op == "AND" and not left:
            return False  # short-circuit
        if ast.op == "OR" and left:
            return True  # short-circuit
        right = evaluate(ast.right, cp, blocks, whole_words)
        if ast.op == "AND":
            return left and right
        else:
            return left or right
    elif isinstance(ast, NotOp):
        return not evaluate(ast.expr, cp, blocks, whole_words)
    return False


# ═══════════════════════════════════════════════════════════════════
#  Search runner
# ═══════════════════════════════════════════════════════════════════


def _has_wholewords(ast: ASTNode) -> bool:
    """Check if the AST contains a wholewords=True flag."""
    if isinstance(ast, Cond):
        prop = _resolve_key(ast.key)
        return prop is not None and prop["key"] == "wholewords" and ast.value.lower() in ("true", "1", "yes")
    elif isinstance(ast, BinOp):
        return _has_wholewords(ast.left) or _has_wholewords(ast.right)
    elif isinstance(ast, NotOp):
        return _has_wholewords(ast.expr)
    return False


def search(
    q: str, blocks: list[dict], limit: int = 200, start_cp: int = 0, filter_no_block: bool = False
) -> list[dict]:
    """Run an advanced search query and return matching codepoints.

    If start_cp > 0, search starts from start_cp + 1 and wraps around.
    If filter_no_block is True, codepoints without an assigned block are skipped.
    """
    results: list[dict] = []
    for item in _search_iter(q, blocks, limit, start_cp, filter_no_block):
        if "_progress" not in item:
            results.append(item)
    return results


# ── Name index cache (speeds up simple name searches) ──────────────

_name_index: list[tuple[int, str]] | None = None


def _build_name_index(blocks: list[dict] | None = None):
    """Pre-build an index of (cp, name) for ALL codepoints with names,
    including algorithmic names (CJK, Tangut, Nushu, etc. — handled by Unicode core)."""
    global _name_index
    if _name_index is not None:
        return
    _name_index = []
    for cp in range(0x0000, 0x110000):
        if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
            continue
        n = Unicode.get_character_name(cp)
        if n:
            _name_index.append((cp, n))


def _is_simple_name_search(ast: ASTNode) -> bool:
    """Check if the AST is a single name=value condition (no AND/OR/NOT)."""
    if isinstance(ast, Cond):
        return ast.key == "name"
    return False


def _search_iter(q: str, blocks: list[dict], limit: int = 200, start_cp: int = 0, filter_no_block: bool = False):
    """Generator that yields dicts: matches have {codepoint, name, progress},
    progress-only updates have {_progress: float}.
    Uses name index for simple name searches to speed up iteration.
    limit=0 means no limit (return all matches).
    If filter_no_block is True, codepoints without an assigned block are skipped.

    Progress = distance from start_cp+1 to current cp, divided by total range.
    start_cp+1 → 0%, wrapping back to start_cp → 100%.
    """
    ast = parse_query(q)
    if ast is None:
        return

    whole_words = _has_wholewords(ast)
    yielded = 0
    checked = 0
    MAX_CP = 0x10FFFF
    TOTAL = MAX_CP + 1  # 0x110000 — full codepoint range

    def _progress_phase1(cp: int) -> float:
        """cp is in [start_cp+1, MAX_CP]."""
        return round((cp - start_cp - 1) / TOTAL * 100, 1)

    def _progress_phase2(cp: int) -> float:
        """cp is in [0, start_cp] after wrap."""
        return round((MAX_CP - start_cp + cp + 1) / TOTAL * 100, 1)

    def _progress_named(cp: int) -> float:
        """Progress for name index path: distance from start_cp+1."""
        if cp > start_cp:
            return _progress_phase1(cp)
        else:
            return _progress_phase2(cp)

    # Fast path: simple name search uses pre-built name index
    if _is_simple_name_search(ast):
        assert isinstance(ast, Cond)
        _build_name_index(blocks)
        assert _name_index is not None
        indexed = sorted(_name_index, key=lambda x: x[0])
        total = len(indexed)

        if start_cp > 0:
            lo, hi = 0, total - 1
            start_idx = total
            while lo <= hi:
                mid = (lo + hi) // 2
                if indexed[mid][0] <= start_cp:
                    lo = mid + 1
                else:
                    start_idx = mid
                    hi = mid - 1
            if start_idx >= total:
                start_idx = 0
            # Phase 1
            for i in range(start_idx, total):
                cp, n = indexed[i]
                checked += 1
                if checked % 500 == 0:
                    yield {"_progress": _progress_phase1(cp)}
                if _match_val(ast.value, n, ast.wildcard, whole_words):
                    yield {"codepoint": cp, "name": n, "progress": _progress_phase1(cp)}
                    yielded += 1
                    if limit > 0 and yielded >= limit:
                        return
            # Phase 2
            if limit == 0 or yielded < limit:
                for i in range(0, start_idx):
                    cp, n = indexed[i]
                    checked += 1
                    if checked % 500 == 0:
                        yield {"_progress": _progress_phase2(cp)}
                    if _match_val(ast.value, n, ast.wildcard, whole_words):
                        yield {"codepoint": cp, "name": n, "progress": _progress_phase2(cp)}
                        yielded += 1
                        if limit > 0 and yielded >= limit:
                            return
        else:
            for cp, n in indexed:
                checked += 1
                if checked % 500 == 0:
                    yield {"_progress": _progress_named(cp)}
                if _match_val(ast.value, n, ast.wildcard, whole_words):
                    yield {"codepoint": cp, "name": n, "progress": _progress_named(cp)}
                    yielded += 1
                    if limit > 0 and yielded >= limit:
                        return
        yield {"_progress": 100.0}
        return

    # Full scan path for complex queries
    if start_cp > 0:
        for cp in range(start_cp + 1, MAX_CP + 1):
            if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
                continue
            if filter_no_block and _find_block(cp, blocks) is None:
                continue
            checked += 1
            if checked % 5000 == 0:
                yield {"_progress": _progress_phase1(cp)}
            if evaluate(ast, cp, blocks, whole_words):
                yield {"codepoint": cp, "name": _cp_display_name(cp), "progress": _progress_phase1(cp)}
                yielded += 1
                if limit > 0 and yielded >= limit:
                    return
        if limit == 0 or yielded < limit:
            for cp in range(0, start_cp + 1):
                if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
                    continue
                if filter_no_block and _find_block(cp, blocks) is None:
                    continue
                checked += 1
                if checked % 5000 == 0:
                    yield {"_progress": _progress_phase2(cp)}
                if evaluate(ast, cp, blocks, whole_words):
                    yield {"codepoint": cp, "name": _cp_display_name(cp), "progress": _progress_phase2(cp)}
                    yielded += 1
                    if limit > 0 and yielded >= limit:
                        return
    else:
        for cp in range(0, MAX_CP + 1):
            if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
                continue
            if filter_no_block and _find_block(cp, blocks) is None:
                continue
            checked += 1
            if checked % 5000 == 0:
                yield {"_progress": _progress_named(cp)}
            if evaluate(ast, cp, blocks, whole_words):
                yield {"codepoint": cp, "name": _cp_display_name(cp), "progress": _progress_named(cp)}
                yielded += 1
                if limit > 0 and yielded >= limit:
                    return

    # Final progress: ensure bar reaches 100% when scan completes
    yield {"_progress": 100.0}


def search_stream_sse(q: str, blocks: list[dict], limit: int = 0, start_cp: int = 0, filter_no_block: bool = False):
    """SSE generator: first QUERY, then PROGRESS updates, results, then [DONE]."""
    import json

    normalized = normalize_query(q)
    yield f"data: QUERY {json.dumps(normalized)}\n\n"

    for item in _search_iter(q, blocks, limit, start_cp, filter_no_block):
        if "_progress" in item:
            yield f"data: PROGRESS {item['_progress']}\n\n"
        else:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def _cp_display_name(cp: int) -> str:
    """Get the display name for a codepoint."""
    n = Unicode.get_character_name(cp)
    if n:
        return n
    return f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:05X}"


# ── Legacy compatibility ───────────────────────────────────────────

# test_condition is kept for backward compatibility with any external callers.
# It now parses the single condition and evaluates via the AST evaluator.


def test_condition(cond: dict, cp: int, blocks: list[dict], whole_words: bool = False) -> bool:
    """Evaluate a legacy condition dict (for backward compat)."""
    c = Cond(
        key=cond.get("key", ""),
        op=cond.get("op", "="),
        value=cond.get("value", ""),
        negate=cond.get("negate", False),
        wildcard=cond.get("wildcard", False),
        comma=cond.get("comma", False),
        values=cond.get("values", [cond.get("value", "")]),
    )
    return _eval_cond(c, cp, blocks, whole_words)
