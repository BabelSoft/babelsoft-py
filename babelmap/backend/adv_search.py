"""Advanced character search: property definitions, expression parser, evaluator."""

import fnmatch
import re
from typing import Any

from src.unicode.core import Unicode

# ── Property definitions ───────────────────────────────────────────

ADV_PROPS: list[dict[str, Any]] = [
    {"key": "name", "label": "Name", "type": "text", "desc": "Character name (* wildcard)"},
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


# ── Expression parser ──────────────────────────────────────────────

_OPS_PAT = re.compile(r"(>=|<=|!=|=|:)")


def _split_toplevel(q: str) -> list[tuple[str, str]]:
    """Split query into (logic, expr) pairs, handling NOT(...) as single token."""
    parts: list[tuple[str, str]] = []
    i = 0
    q_len = len(q)
    logic = "AND"

    while i < q_len:
        while i < q_len and q[i].isspace():
            i += 1
        if i >= q_len:
            break

        w_start = i
        while i < q_len and q[i].isalpha():
            i += 1
        word = q[w_start:i].upper()

        if word in ("AND", "OR"):
            logic = word
            continue
        elif word == "NOT":
            while i < q_len and q[i].isspace():
                i += 1
            if i < q_len and q[i] == "(":
                depth = 1
                start = i
                i += 1
                while i < q_len and depth > 0:
                    if q[i] == "(":
                        depth += 1
                    elif q[i] == ")":
                        depth -= 1
                    i += 1
                inner = q[start + 1 : i - 1]
                for _, expr in _split_toplevel(inner):
                    parts.append(("NOT", expr))
            else:
                # Simple NOT before expression, rewind
                i = w_start
                while i < q_len and not q[i].isspace():
                    i += 1
                expr = q[w_start + 3 : i].strip()
                if expr:
                    parts.append(("NOT", expr))
            continue
        else:
            # Read expression until AND/OR/NOT boundary
            i = w_start
            while i < q_len:
                if q[i] == "(":
                    depth = 1
                    i += 1
                    while i < q_len and depth > 0:
                        if q[i] == "(":
                            depth += 1
                        elif q[i] == ")":
                            depth -= 1
                        i += 1
                else:
                    rest = q[i:].lstrip().upper()
                    if rest.startswith("AND ") or rest == "AND":
                        break
                    if rest.startswith("OR ") or rest == "OR":
                        break
                    if rest.startswith("NOT ") or rest.startswith("NOT("):
                        break
                    i += 1
            expr = q[w_start:i].strip()
            if expr:
                parts.append((logic, expr))
            logic = "AND"

    return parts


def parse_query(q: str) -> list[dict[str, Any]]:
    """Parse an advanced search query into conditions list."""
    parts = _split_toplevel(q)
    conditions: list[dict[str, Any]] = []
    for logic, expr in parts:
        cond = _parse_one_expr(expr)
        if cond is not None:
            cond["logic"] = logic
            conditions.append(cond)
    return conditions


def _parse_one_expr(expr: str) -> dict[str, Any] | None:
    """Parse a single expression like 'Name=lisu' or 'Script=Latn,Hani'."""
    expr = expr.strip()
    if not expr:
        return None

    cond: dict[str, Any] = {"negate": False, "wildcard": False, "comma": False, "op": "="}

    # Split on operator: >=, <=, !=, =, :
    parts = _OPS_PAT.split(expr, maxsplit=1)
    if len(parts) >= 3:
        key = parts[0]
        op = parts[1]
        val = parts[2]
    elif "=" in expr:
        key, val = expr.split("=", 1)
        op = "="
    else:
        key, val = expr, "True"
        op = "="

    cond["key"] = key.strip().lower()
    cond["op"] = op
    val = val.strip().strip('"').strip("'")

    if op == "!=":
        cond["negate"] = True

    if "*" in val or "?" in val:
        cond["wildcard"] = True

    if "," in val and op not in (">=", "<="):
        cond["comma"] = True
        cond["values"] = [v.strip() for v in val.split(",") if v.strip()]

    cond["value"] = val
    return cond


# ── Condition evaluator ────────────────────────────────────────────


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


def _name_for_cp(cp: int, blocks: list[dict]) -> str:
    blk = _find_block(cp, blocks)
    if blk:
        bn = blk["name"]
        h = f"{cp:04X}" if cp <= 0xFFFF else f"{cp:05X}"
        if "CJK" in bn and "Ideograph" in bn:
            return f"CJK UNIFIED IDEOGRAPH-{h}" if "Unified" in bn else f"CJK COMPATIBILITY IDEOGRAPH-{h}"
        if "Tangut" in bn and "Ideograph" in bn:
            return f"TANGUT IDEOGRAPH-{h}"
        if "Hangul" in bn:
            return f"HANGUL SYLLABLE-{h}"
    return f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:05X}"


def _match_val(val: str, target: str, wildcard: bool, whole_words: bool) -> bool:
    v, t = val.upper(), target.upper()
    if wildcard:
        return fnmatch.fnmatch(t, v)
    if whole_words:
        return bool(re.search(rf"\b{re.escape(v)}\b", t))
    return v in t


def _match_multi(val: str, vals: list[str], target: str, wildcard: bool, whole_words: bool) -> bool:
    return any(_match_val(v, target, wildcard, whole_words) for v in vals)


def test_condition(cond: dict, cp: int, blocks: list[dict], whole_words: bool = False) -> bool:
    prop = _resolve_key(cond["key"])
    if not prop:
        return False
    key: str = prop["key"]
    val: str = cond.get("value", "")
    op: str = cond.get("op", "=")
    negate: bool = cond.get("negate", False)
    wildcard: bool = cond.get("wildcard", False)
    vals: list[str] = cond.get("values", [val]) if cond.get("comma") else [val]

    try:
        # ── Name searches ──
        if key == "name":
            n = Unicode.get_character_name(cp)
            if not n or n.startswith("<"):
                n = _name_for_cp(cp, blocks)
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
            try:
                n = Unicode.get_character_name(cp)
                if n and not n.startswith("<"):
                    names.append(n)
            except Exception:
                pass
            try:
                n1 = Unicode.get_unicode1_name(cp)
                if n1:
                    names.append(n1)
            except Exception:
                pass
            combined = " | ".join(names) if names else _name_for_cp(cp, blocks)
            return not negate if _match_multi(val, vals, combined, wildcard, whole_words) else negate

        if key in ("notes", "crossreferences"):
            return negate

        if key == "wholewords":
            return True  # meta-flag

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


# ── Search runner ──────────────────────────────────────────────────


def search(q: str, blocks: list[dict], limit: int = 200) -> list[dict]:
    """Run an advanced search query and return matching codepoints."""
    conditions = parse_query(q)
    if not conditions:
        return []

    whole_words = any(
        _resolve_key(c.get("key", "")) is not None
        and _resolve_key(c["key"])["key"] == "wholewords"
        and c.get("value", "").lower() in ("true", "1", "yes")
        for c in conditions
    )

    results: list[dict] = []
    for cp in range(0x0000, 0x110000):
        if cp > 0x10FFFF:
            break
        if Unicode.is_surrogate(cp) or not Unicode.is_valid_code_point(cp):
            continue

        match = None
        for cond in conditions:
            if _resolve_key(cond.get("key", "")) is not None and _resolve_key(cond["key"])["key"] == "wholewords":
                continue
            m = test_condition(cond, cp, blocks, whole_words)
            logic = cond["logic"]
            if logic == "OR":
                match = (match or m) if match is not None else m
            elif logic == "NOT":
                match = (match and not m) if match is not None else (not m)
            else:
                match = (match and m) if match is not None else m

        if match:
            name = f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:05X}"
            try:
                n = Unicode.get_character_name(cp)
                if n and not n.startswith("<"):
                    name = n
            except Exception:
                pass
            results.append({"codepoint": cp, "name": name})
            if len(results) >= limit:
                break

    return results
