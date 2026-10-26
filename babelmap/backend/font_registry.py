"""User font registry — fonts the user brings in from *outside* the system font
directories, plus the composite-font CSS rules built on top of them.

Why this exists
---------------
The browser already knows every font the OS exposes (``local("Font Name")``
resolves them inside a ``@font-face``), but a user often wants to test a font
that is *not* installed — a downloaded ``.woff2``, a project ``.ttf``, a font
sitting on a USB stick.  Those files cannot be reached by ``local()``, so the
frontend uploads them here; we copy them into a managed ``user_fonts`` folder
and serve them back over ``/api/fonts/user_file`` so a ``@font-face`` rule can
carry a real ``src: url(...)``.

Layout on disk::

    babelmap/backend/var/user_fonts/<id>/<original-file-name>

``<id>`` is a stable, filesystem-safe token so two fonts with the same file name
(e.g. two ``NotoSans-Regular.otf`` from different sources) never collide.

Public API:
- :func:`register` — store an uploaded font, return its registry entry.
- :func:`unregister` — delete a stored font (the inverse of ``register``).
- :func:`list_fonts` — every registered font, newest first.
- :func:`resolve` — id → on-disk path + face count (used by the file endpoint).
- :func:`analyze` — fontTools metadata for one registered font.
- :func:`validate_css` — compile/validate user-written composite-font CSS.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_DIR = Path(__file__).resolve().parent / "var" / "user_fonts"

# Font containers the Shape engines and the browser can both consume.  WOFF /
# WOFF2 are accepted because they are what the web (and font vendors) hand out.
ALLOWED_EXTS = (".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2")

# A hard ceiling so a mis-click on a 200 MB variable collection bounces instead
# of filling the disk.  48 MB comfortably fits any real webfont subset.
MAX_BYTES = 48 * 1024 * 1024

_MEDIA = {
    ".ttf": "font/ttf",
    ".ttc": "font/collection",
    ".otc": "font/collection",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


# ── on-disk registry ─────────────────────────────────────────────────


def _safe_name(name: str) -> str:
    """Strip any directory part and characters that are unsafe on Windows."""
    base = os.path.basename(name or "").strip()
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
    return base or "font.bin"


def _registry_file() -> Path:
    return REGISTRY_DIR / "registry.json"


def _read_index() -> dict:
    try:
        with open(_registry_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("fonts"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"fonts": []}


def _write_index(index: dict) -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _registry_file().with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, _registry_file())


def register(file_name: str, data: bytes, *, source: str = "upload") -> dict:
    """Store an uploaded font and return its registry entry.

    Raises ``ValueError`` for an unacceptable extension or oversized payload so
    the endpoint can turn it into a 400 with the message intact.
    """
    ext = os.path.splitext(file_name or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"Unsupported font extension '{ext or file_name}'. Allowed: {', '.join(ALLOWED_EXTS)}")
    if not data:
        raise ValueError("Empty font file")
    if len(data) > MAX_BYTES:
        raise ValueError(f"Font is {len(data) / 1048576:.1f} MB; the limit is {MAX_BYTES // 1048576} MB")

    fid = uuid.uuid4().hex[:12]
    folder = REGISTRY_DIR / fid
    folder.mkdir(parents=True, exist_ok=True)
    name = _safe_name(file_name)
    dest = folder / name
    dest.write_bytes(data)

    entry = {
        "id": fid,
        "name": os.path.splitext(name)[0],
        "file": name,
        "ext": ext.lstrip("."),
        "path": str(dest),
        "size": len(data),
        "source": source,
        "added": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Read the family/face metadata straight away so the UI can show a real name
    # in the list without a second round-trip.
    entry.update(_face_meta(dest))
    entry["subfamilies"] = _subfamilies(dest)

    index = _read_index()
    index["fonts"].append(entry)
    _write_index(index)
    return entry


def unregister(font_id: str) -> bool:
    """Delete a registered font.  Returns ``False`` when the id is unknown."""
    index = _read_index()
    kept, hit = [], None
    for e in index["fonts"]:
        if e.get("id") == font_id:
            hit = e
        else:
            kept.append(e)
    if hit is None:
        return False
    folder = REGISTRY_DIR / font_id
    try:
        shutil.rmtree(folder)
    except OSError:
        # The folder may already be gone; the registry entry still has to go.
        pass
    index["fonts"] = kept
    _write_index(index)
    return True


def list_fonts() -> list[dict]:
    """Every registered font, skipping entries whose file vanished on disk."""
    index = _read_index()
    out = []
    for e in index["fonts"]:
        p = e.get("path")
        if p and os.path.isfile(p):
            out.append(e)
    if len(out) != len(index["fonts"]):
        index["fonts"] = out
        _write_index(index)
    out.sort(key=lambda e: e.get("added") or "", reverse=True)
    return out


def resolve(font_id: str) -> dict | None:
    """Look a registered font up by id → entry (or ``None`` when unknown)."""
    for e in list_fonts():
        if e.get("id") == font_id:
            return e
    return None


def media_type(ext: str) -> str:
    return _MEDIA.get("." + (ext or "").lstrip(".").lower(), "application/octet-stream")


# ── metadata / analysis ──────────────────────────────────────────────


def _face_meta(path: Path) -> dict:
    """Family / face-count / glyph-count for one file, via fontTools.

    Never raises — a corrupt or unsupported file still gets registered (the
    user may want to delete it) and simply reports empty metadata.
    """
    meta = {"family": "", "faces": 0, "glyphs": 0, "kind": ""}
    try:
        from fontTools.ttLib import TTCollection, TTFont

        if path.suffix.lower() in (".ttc", ".otc"):
            coll = TTCollection(str(path), lazy=True)
            try:
                meta["faces"] = len(coll.fonts)
                if coll.fonts:
                    first = coll.fonts[0]
                    meta["family"] = _family_name(first)
                    meta["glyphs"] = _glyph_count(first)
                    meta["kind"] = "collection"
            finally:
                coll.close()
            return meta

        tt = TTFont(str(path), lazy=True, fontNumber=0)
        try:
            meta["faces"] = 1
            meta["family"] = _family_name(tt)
            meta["glyphs"] = _glyph_count(tt)
            meta["kind"] = "woff2" if path.suffix.lower() == ".woff2" else path.suffix.lower().lstrip(".")
        finally:
            tt.close()
    except Exception:
        pass
    return meta


def _family_name(tt) -> str:
    try:
        for rec in tt["name"].names:
            if rec.nameID == 1:
                try:
                    return str(rec.toUnicode()).strip()
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def _glyph_count(tt) -> int:
    try:
        return int(tt["maxp"].numGlyphs)
    except Exception:
        return 0


def _subfamilies(path: Path) -> list[str]:
    """The face names held in one file — ``["Regular"]``, ``["Bold", "Italic"]``…

    Read from name ID 2 (subfamily) of every face in a collection.  These are
    the real style names the font declares, which is what the overview shows as
    face chips for installed fonts; deriving them (rather than assuming
    "Regular") keeps an uploaded font's rows truthful.

    Never raises: an unreadable file yields an empty list.
    """
    out: list[str] = []
    try:
        from fontTools.ttLib import TTCollection, TTFont

        if path.suffix.lower() in (".ttc", ".otc"):
            coll = TTCollection(str(path), lazy=True)
            try:
                for f in coll.fonts:
                    out.append(_subfamily_name(f))
            finally:
                coll.close()
        else:
            tt = TTFont(str(path), lazy=True, fontNumber=0)
            try:
                out.append(_subfamily_name(tt))
            finally:
                tt.close()
    except Exception:
        pass
    return [s for s in out if s]


def _subfamily_name(tt) -> str:
    """name ID 2 (subfamily), falling back to name ID 4 (full name)."""
    try:
        for rec in tt["name"].names:
            if rec.nameID == 2:
                try:
                    s = str(rec.toUnicode()).strip()
                    if s:
                        return s
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def analyze(font_id: str) -> dict | None:
    """Full fontTools analysis of a registered font: identity, metrics, tables,
    cmap coverage and OpenType feature/language tags.

    Shape mirrors the subset of ``font_overview._face_entry`` the composite-font
    dialog needs (identity + coverage + OpenType), so the dialog can describe an
    uploaded font exactly like an installed one.
    """
    entry = resolve(font_id)
    if entry is None:
        return None
    path = Path(entry["path"])
    if not path.is_file():
        return None

    out = {
        "id": font_id,
        "name": entry.get("name") or path.stem,
        "file": entry.get("file"),
        "ext": entry.get("ext"),
        "size": entry.get("size"),
        "family": entry.get("family") or "",
        "faces": entry.get("faces") or 1,
        # Real style names of the faces in this file — the overview renders them
        # as face chips, exactly like an installed family's.
        "subfamilies": entry.get("subfamilies") or [],
        "glyphs": entry.get("glyphs") or 0,
        "upem": 0,
        "tables": [],
        "variable": False,
        "axes": [],
        "ot_langs": [],
        "ot_features": [],
        "coverage": 0,
        "cmap_ranges": [],
        "blocks": [],
    }

    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(str(path), lazy=True, fontNumber=0)
        try:
            out["family"] = _family_name(tt) or out["family"]
            out["glyphs"] = _glyph_count(tt) or out["glyphs"]
            # Registrations made before ``subfamilies`` existed have no entry
            # field, so read the face names here rather than showing invented
            # "Regular" chips.
            if not out["subfamilies"]:
                out["subfamilies"] = _subfamilies(path)
            try:
                out["upem"] = int(tt["head"].unitsPerEm)
            except Exception:
                pass
            try:
                out["tables"] = sorted(tt.keys())
            except Exception:
                pass

            # Variable-font axes
            try:
                fvar = tt["fvar"]
                out["variable"] = True
                for a in fvar.axes:
                    out["axes"].append(
                        {
                            "tag": a.axisTag,
                            "min": round(a.minValue, 3),
                            "default": round(a.defaultValue, 3),
                            "max": round(a.maxValue, 3),
                        }
                    )
            except Exception:
                pass

            # OpenType language systems + layout feature tags
            try:
                from babelmap.backend.font_overview import _read_ot_features, _read_ot_langs

                out["ot_langs"] = sorted(_read_ot_langs(tt))
                out["ot_features"] = _read_ot_features(tt)
            except Exception:
                pass

            # cmap coverage → count + coalesced ranges + block histogram
            try:
                cmap = tt.getBestCmap() or {}
                cps = sorted(cmap.keys())
                out["coverage"] = len(cps)
                out["cmap_ranges"] = _coalesce(cps)
                out["blocks"] = _block_histogram(cps)
            except Exception:
                pass
        finally:
            tt.close()
    except Exception:
        pass

    return out


def _coalesce(points: list[int]) -> list[list[int]]:
    """Sorted codepoints → coalesced ``[[start, end], ...]`` ranges."""
    if not points:
        return []
    out = [[points[0], points[0]]]
    for cp in points[1:]:
        if cp == out[-1][1] + 1:
            out[-1][1] = cp
        else:
            out.append([cp, cp])
    return out


def _block_histogram(points: list[int]) -> list[dict]:
    """How many covered codepoints fall in each Unicode block (largest first)."""
    try:
        from babelsoft.unicode.core import Unicode

        table, names = Unicode._block_data()
    except Exception:
        return []
    if not table:
        return []
    import bisect

    out = []
    for start, end, idx in table:
        lo = bisect.bisect_left(points, start)
        hi = bisect.bisect_right(points, end)
        if hi > lo:
            out.append({"name": names[idx], "start": start, "end": end, "covered": hi - lo})
    out.sort(key=lambda e: e["covered"], reverse=True)
    return out


# ── composite-font CSS validation ────────────────────────────────────


# font-family: <quoted or bare name> ;  — deliberately permissive on the name so
# "Noto Sans CJK SC", 'Noto Sans CJK SC' and NotoSansCJKsc all pass.
_RE_FONT_FACE_OPEN = re.compile(r"@font-face\s*\{", re.IGNORECASE)
_RE_FONT_FAMILY = re.compile(
    r"""font-family\s*:\s*(?:"([^"]*)"|'([^']*)'|([^;{}]+))""",
    re.IGNORECASE,
)
_RE_SRC = re.compile(r"\bsrc\s*:", re.IGNORECASE)
_RE_SRC_URL = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)""", re.IGNORECASE)
_RE_SRC_LOCAL = re.compile(r"""local\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)""", re.IGNORECASE)
_RE_UNICODE_RANGE = re.compile(r"unicode-range\s*:\s*([^;{}]+)", re.IGNORECASE)
_RE_FONT_WEIGHT = re.compile(r"font-weight\s*:\s*([^;{}]+)", re.IGNORECASE)
_RE_FONT_STYLE = re.compile(r"font-style\s*:\s*([^;{}]+)", re.IGNORECASE)
_RE_FONT_STRETCH = re.compile(r"font-stretch\s*:\s*([^;{}]+)", re.IGNORECASE)
_RE_DECL = re.compile(r"([-\w]+)\s*:\s*([^;{}]*)")

_VALID_STYLE = {"normal", "italic", "oblique"}
_VALID_WEIGHT_KEYWORDS = {"normal", "bold", "bolder", "lighter"}


class CssIssue:
    """One validation finding, rendered as a marker in the editor gutter."""

    def __init__(self, level: str, message: str, line: int = 0, col: int = 0):
        self.level = level  # "error" | "warning"
        self.message = message
        self.line = line
        self.col = col

    def to_dict(self) -> dict:
        return {"level": self.level, "message": self.message, "line": self.line, "col": self.col}


def _line_of(css: str, pos: int) -> int:
    return css.count("\n", 0, pos) + 1


def validate_css(css: str, *, known_families: list[str] | None = None) -> dict:
    """Compile-validate user composite-font CSS.

    Checks performed (each producing an error or warning):

    * balanced braces / unterminated strings and comments (syntax);
    * every ``@font-face`` has a ``font-family`` and a ``src``;
    * ``src: url(...)`` points at an existing file when it is a ``/api/...``
      path we served ourselves — anything else is a warning (the browser may
      still fetch it);
    * ``src: local(...)`` names a font that actually exists on this system
      (checked against ``font_overview`` families) — otherwise a warning;
    * ``unicode-range`` parses as ``U+X``, ``U+X-Y`` or ``U+XX??`` with sane
      bounds (``U+0``–``U+10FFFF``, start ≤ end);
    * ``font-weight`` / ``font-style`` / ``font-stretch`` values are legal.

    Returns ``{ok, errors, warnings, stats, families}`` where ``ok`` is true
    only when ``errors`` is empty — the dialog treats ``ok`` as "编译通过".
    """
    issues: list[CssIssue] = []

    # ── 1. Lexical sanity: strings / comments / braces ──
    stripped, lex_issues = _strip_comments_and_strings(css)
    issues.extend(lex_issues)
    depth, bad_at = 0, -1
    for i, ch in enumerate(stripped):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                bad_at = i
                break
    if bad_at >= 0:
        issues.append(CssIssue("error", "Unmatched '}'", _line_of(css, bad_at)))
    elif depth > 0:
        issues.append(CssIssue("error", f"Unclosed '{{' — {depth} block(s) still open"))

    # ── 2. Per @font-face block ──
    # Block *boundaries* are found on the masked text (so braces inside strings
    # or comments cannot confuse them), but declarations are read from the
    # ORIGINAL css so quoted font names survive intact.
    families: list[dict] = []
    known = {f.lower() for f in (known_families or [])}
    for m in _RE_FONT_FACE_OPEN.finditer(stripped):
        start = m.end()
        end = stripped.find("}", start)
        stop = end if end >= 0 else len(stripped)
        block = css[start:stop]
        line0 = _line_of(css, m.start())

        fam_m = _RE_FONT_FAMILY.search(block)
        if not fam_m:
            issues.append(CssIssue("error", "@font-face is missing font-family", line0))
            family = ""
        else:
            family = (fam_m.group(1) or fam_m.group(2) or fam_m.group(3) or "").strip()
            if not family:
                issues.append(CssIssue("error", "@font-face has an empty font-family", line0))

        if not _RE_SRC.search(block):
            issues.append(CssIssue("error", f"@font-face '{family or '?'}' is missing src", line0))
        else:
            # local(...) must name a font that exists; url(...) to our own
            # /api path must point at a stored file.
            for lm in _RE_SRC_LOCAL.finditer(block):
                name = (lm.group(1) or lm.group(2) or lm.group(3) or "").strip()
                if name and known and name.lower() not in known:
                    issues.append(
                        CssIssue(
                            "warning",
                            f"local('{name}') is not among the detected system fonts — "
                            "the browser will skip it if it is not installed",
                            _line_of(css, start + lm.start()),
                        )
                    )
            for um in _RE_SRC_URL.finditer(block):
                url = (um.group(1) or um.group(2) or um.group(3) or "").strip()
                if url.startswith("/api/fonts/user_file"):
                    qid = _query_param(url, "id")
                    if qid and resolve(qid) is None:
                        issues.append(
                            CssIssue(
                                "error",
                                f"src url references unknown registered font id '{qid}'",
                                _line_of(css, start + um.start()),
                            )
                        )
                elif url and not url.startswith(("data:", "http://", "https://", "file:")):
                    issues.append(
                        CssIssue(
                            "warning",
                            f"src url('{url}') is a relative path the backend cannot verify",
                            _line_of(css, start + um.start()),
                        )
                    )

        for dm in _RE_UNICODE_RANGE.finditer(block):
            raw = dm.group(1).strip()
            for tok in raw.split(","):
                tok = tok.strip()
                if not tok:
                    continue
                err = _check_unicode_range_token(tok)
                if err:
                    issues.append(CssIssue("error", err, _line_of(css, start + dm.start())))

        for rx, label in (
            (_RE_FONT_WEIGHT, "font-weight"),
            (_RE_FONT_STYLE, "font-style"),
            (_RE_FONT_STRETCH, "font-stretch"),
        ):
            for vm in rx.finditer(block):
                val = vm.group(1).strip().lower()
                err = _check_face_value(label, val)
                if err:
                    issues.append(CssIssue("error", err, _line_of(css, start + vm.start())))

        # Per-declaration sanity (catches "font-famly:" style typos as warnings)
        for dm in _RE_DECL.finditer(block):
            prop = dm.group(1).strip().lower()
            if prop.startswith("-") or prop in _KNOWN_DECLS:
                continue
            if prop.startswith("unicode") or prop.startswith("font") or prop.startswith("src"):
                issues.append(
                    CssIssue(
                        "warning", f"Unknown property '{prop}' inside @font-face", _line_of(css, start + dm.start())
                    )
                )

        if family:
            families.append({"family": family, "line": line0})

    # Duplicate family names across @font-face blocks are legal (each block adds
    # glyphs) but usually a mistake when the src is identical.
    seen: dict[str, int] = {}
    for f in families:
        key = f["family"].lower()
        seen[key] = seen.get(key, 0) + 1
    for f in families:
        if seen[f["family"].lower()] > 1:
            issues.append(
                CssIssue(
                    "warning",
                    f"font-family '{f['family']}' is declared more than once — "
                    "several @font-face blocks with the same family form one stack",
                    f["line"],
                )
            )

    errors = [i.to_dict() for i in issues if i.level == "error"]
    warnings = [i.to_dict() for i in issues if i.level == "warning"]
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "families": families,
        "stats": {
            "fontFaceRules": len(families),
            "uniqueFamilies": len(seen),
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


_KNOWN_DECLS = {
    "font-family",
    "src",
    "unicode-range",
    "font-weight",
    "font-style",
    "font-stretch",
    "font-display",
    "font-feature-settings",
    "font-variation-settings",
    "font-named-instance",
    "font-language-override",
    "ascent-override",
    "descent-override",
    "line-gap-override",
    "size-adjust",
}


def _query_param(url: str, key: str) -> str:
    from urllib.parse import parse_qs, urlparse

    q = parse_qs(urlparse(url).query)
    return (q.get(key) or [""])[0]


def _check_unicode_range_token(tok: str) -> str | None:
    """Validate one ``unicode-range`` token; return an error message or None."""
    t = tok.strip()
    if not t.upper().startswith("U+"):
        return f"unicode-range token '{tok}' must start with 'U+'"
    body = t[2:]
    if "?" in body:
        if not re.fullmatch(r"[0-9A-Fa-f]{1,6}\?{1,6}", body):
            return f"unicode-range wildcard '{tok}' is malformed (expected U+XX??)"
        lo = int(body.replace("?", "0"), 16)
        hi = int(body.replace("?", "F"), 16)
    elif "-" in body:
        a, _, b = body.partition("-")
        try:
            lo, hi = int(a, 16), int(b, 16)
        except ValueError:
            return f"unicode-range '{tok}' has a non-hex bound"
        if lo > hi:
            return f"unicode-range '{tok}' start is greater than end"
    else:
        try:
            lo = hi = int(body, 16)
        except ValueError:
            return f"unicode-range '{tok}' is not valid hex"
    if lo < 0 or hi > 0x10FFFF:
        return f"unicode-range '{tok}' is outside U+0000–U+10FFFF"
    if 0xD800 <= lo <= 0xDFFF or 0xD800 <= hi <= 0xDFFF:
        return f"unicode-range '{tok}' targets surrogate code points"
    return None


def _check_face_value(prop: str, val: str) -> str | None:
    if prop == "font-style":
        v = val.split()[0]
        if v not in _VALID_STYLE:
            return f"font-style '{val}' is not normal | italic | oblique"
    elif prop == "font-weight":
        v = val.split()[0]
        if v in _VALID_WEIGHT_KEYWORDS:
            return None
        if re.fullmatch(r"\d+(\.\d+)?", v):
            n = float(v)
            if not 1 <= n <= 1000:
                return f"font-weight {v} is outside 1–1000"
            return None
        # A pair "400 700" is legal for variable fonts
        parts = val.split()
        if len(parts) == 2 and all(re.fullmatch(r"\d+", p) for p in parts):
            return None
        return f"font-weight '{val}' is not a keyword or number"
    elif prop == "font-stretch":
        # percentages or keywords
        if re.fullmatch(r"\d+(\.\d+)?%", val):
            return None
        if val in {
            "normal",
            "ultra-condensed",
            "extra-condensed",
            "condensed",
            "semi-condensed",
            "semi-expanded",
            "expanded",
            "extra-expanded",
            "ultra-expanded",
        }:
            return None
        if len(val.split()) == 2 and all(re.fullmatch(r"\d+(\.\d+)?%", p) for p in val.split()):
            return None
        return f"font-stretch '{val}' is not a percentage or stretch keyword"
    return None


def _strip_comments_and_strings(css: str) -> tuple[str, list[CssIssue]]:
    """Blank out comments and string bodies (keeping positions) and report
    lexical problems — unterminated comments/strings.

    Returns the masked text (same length as the input, so offsets stay valid)
    plus any lexical issues.
    """
    issues: list[CssIssue] = []
    out = list(css)
    i, n = 0, len(css)
    while i < n:
        ch = css[i]
        if ch == "/" and i + 1 < n and css[i + 1] == "*":
            j = css.find("*/", i + 2)
            if j < 0:
                issues.append(CssIssue("error", "Unterminated comment", _line_of(css, i)))
                for k in range(i, n):
                    out[k] = " "
                break
            for k in range(i, j + 2):
                out[k] = " "
            i = j + 2
        elif ch in "\"'":
            j = i + 1
            while j < n:
                if css[j] == "\\":
                    j += 2
                    continue
                if css[j] == ch:
                    break
                j += 1
            if j >= n:
                issues.append(CssIssue("error", "Unterminated string", _line_of(css, i)))
                for k in range(i, n):
                    out[k] = " "
                break
            for k in range(i + 1, j):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out), issues
