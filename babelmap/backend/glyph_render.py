"""Glyph rasterisation with selectable quality — the Fonts ▸ Quality engine.

Windows lets an application pick *how* a glyph is turned into pixels through
``LOGFONT.lfQuality``.  A browser cannot: WebView2 owns the text pipeline, so
the character grid will always use the system's own rasterisation.  What we can
do is rasterise ourselves, with the same FreeType library GDI/Chrome sit on top
of, and expose the seven ``lfQuality`` modes:

    DEFAULT           grayscale AA, hinted  (what the grid itself looks like)
    DRAFT             monochrome, no hinting, no AA (coarse outline)
    PROOF             grayscale AA, unhinted (exact shape, real side bearings)
    NONANTIALIASED    monochrome, hinted (crisp 1-bit stems)
    ANTIALIASED       grayscale AA, hinted
    CLEARTYPE         LCD subpixel + 5-tap filter (hinted)
    CLEARTYPE_NATURAL LCD subpixel, unfiltered, natural spacing

Every mode maps onto a `FT_LOAD_TARGET_*` flag plus a hinting flag and, for the
ClearType modes, `FT_Library_SetLcdFilter`.  Nothing here is simulated: the
bitmaps come straight out of the font's outlines.

The results drive two features:

* Fonts ▸ Quality      — a live seven-way comparison of the same sample text;
* Fonts ▸ Export Font Glyphs — a zip of one PNG/BMP per code point.

They are also what a "quality" setting means when it has to be honest: the grid
is not affected, because CSS cannot select a rasteriser.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import freetype
from PIL import Image, ImageChops

# ── Quality modes ────────────────────────────────────────────────────

#: Menu order == `LOGFONT.lfQuality` value == index here.
QUALITY_KEYS = (
    "default",
    "draft",
    "proof",
    "non_antialiased",
    "antialiased",
    "cleartype",
    "cleartype_natural",
)


def _lcd_filter(value):
    """Set the global LCD filter (best-effort: older builds may lack it)."""
    try:
        freetype.FT_Library_SetLcdFilter(freetype.get_handle(), value)
    except Exception:
        pass


def quality_spec(quality: int) -> dict:
    """FreeType settings for one ``lfQuality`` value.

    Returns ``{"flags", "mode", "lcd", "antialiased"}`` where ``mode`` is the
    pixel mode we expect back and ``lcd`` is the subpixel filter to install.
    """
    q = int(quality) % len(QUALITY_KEYS)
    F = freetype
    load = F.FT_LOAD_RENDER | F.FT_LOAD_NO_BITMAP
    if q == 0:  # DEFAULT — what the system itself picks: light hinting + AA
        return {"flags": load | F.FT_LOAD_TARGET_LIGHT, "lcd": None, "aa": True}
    if q == 1:  # DRAFT — GDI's "draft" is unhinted and unpolished
        return {
            "flags": load | F.FT_LOAD_TARGET_MONO | F.FT_LOAD_NO_HINTING,
            "lcd": None,
            "aa": False,
        }
    if q == 2:  # PROOF — exact outlines, grayscale AA, no hinting
        return {
            "flags": load | F.FT_LOAD_TARGET_NORMAL | F.FT_LOAD_NO_HINTING,
            "lcd": None,
            "aa": True,
        }
    if q == 3:  # NONANTIALIASED — hinted 1-bit
        return {"flags": load | F.FT_LOAD_TARGET_MONO, "lcd": None, "aa": False}
    if q == 4:  # ANTIALIASED — hinted grayscale
        return {"flags": load | F.FT_LOAD_TARGET_NORMAL, "lcd": None, "aa": True}
    if q == 5:  # CLEARTYPE — subpixel + 5-tap filter
        return {
            "flags": load | F.FT_LOAD_TARGET_LCD,
            "lcd": F.FT_LCD_FILTER_DEFAULT,
            "aa": True,
        }
    # CLEARTYPE_NATURAL — subpixel, no filtering, natural advances
    return {
        "flags": load | F.FT_LOAD_TARGET_LCD | F.FT_LOAD_NO_HINTING,
        "lcd": F.FT_LCD_FILTER_NONE,
        "aa": True,
    }


# ── Font resolution ──────────────────────────────────────────────────

#: family (lower-cased) -> [(path, face_index, style)] — built once, cheap.
_INDEX: dict[str, list[tuple[str, int, str]]] | None = None


def _font_dirs() -> list[str]:
    from babelmap.backend.font_overview import DEFAULT_DIRS, EXTENSIONS

    dirs = [d for d in DEFAULT_DIRS if os.path.isdir(d)]
    try:
        from babelmap.backend import font_registry

        reg = font_registry.REGISTRY_DIR
        if reg.is_dir():
            for sub in reg.iterdir():
                if sub.is_dir() and any((sub / f).suffix.lower() in EXTENSIONS for f in os.listdir(sub)):
                    dirs.append(str(sub))
    except Exception:
        pass
    return dirs


def build_index(force: bool = False) -> dict[str, list[tuple[str, int, str]]]:
    """Enumerate installed faces with FreeType itself (fast, no fontTools).

    A family can be spread over several files (regular / bold / …) and a file
    can hold several faces (.ttc), so the value is a list of
    ``(path, face_index, style)`` ordered with Regular first.
    """
    global _INDEX
    if _INDEX is not None and not force:
        return _INDEX
    from babelmap.backend.font_overview import EXTENSIONS

    index: dict[str, list[tuple[str, int, str]]] = {}
    for d in _font_dirs():
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            if not name.lower().endswith(EXTENSIONS):
                continue
            path = os.path.join(d, name)
            try:
                face = freetype.Face(path)
                count = face.num_faces
            except Exception:
                continue
            for i in range(max(1, count)):
                try:
                    f = freetype.Face(path, i)
                    fam = (f.family_name or b"").decode("utf-8", "replace")
                    style = (f.style_name or b"Regular").decode("utf-8", "replace")
                except Exception:
                    continue
                if not fam:
                    continue
                index.setdefault(fam.strip().lower(), []).append((path, i, style))
    for faces in index.values():
        faces.sort(key=lambda t: (t[2].lower() != "regular", t[2].lower()))
    _INDEX = index
    return index


def resolve_face(family: str = "", style: str = "") -> tuple[str, int, str]:
    """Find ``(path, face_index, style)`` for a family/style pair.

    ``family`` may also be a direct path (the export dialog passes one) or a
    registry id.  Raises ``KeyError`` when nothing matches.
    """
    if family and os.path.isfile(family):
        return (family, 0, "")

    # Uploaded fonts are addressed as ``u:<id>`` by the frontend.
    if family.startswith("u:"):
        from babelmap.backend import font_registry

        entry = font_registry.resolve(family[2:])
        if entry:
            return (str(font_registry.REGISTRY_DIR / entry["id"] / entry["file"]), 0, "")

    index = build_index()
    want = (family or "Arial").strip().lower()
    faces = index.get(want)
    if not faces:
        # Prefix / substring fallback so "Arial" still finds "Arial Narrow" etc.
        for key, val in index.items():
            if want and (key.startswith(want) or want in key):
                faces = val
                break
    if not faces:
        faces = index.get("arial") or []
    if not faces:
        raise KeyError(f"font not found: {family!r}")
    if style:
        s = style.strip().lower()
        for path, i, st in faces:
            if st.lower() == s:
                return (path, i, st)
        for path, i, st in faces:
            if s in st.lower():
                return (path, i, st)
    return faces[0]


# ── Rendering ────────────────────────────────────────────────────────


def _hex_rgba(value: str, default: str) -> tuple[int, int, int, int]:
    v = (value or default).lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) == 6:
        v += "ff"
    try:
        return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4, 6))  # type: ignore[return-value]
    except Exception:
        return _hex_rgba(default, default)


def _coverage_image(face, bitmap) -> Image.Image:
    """Turn a FreeType bitmap into an 8-bit coverage mask (or RGB for LCD)."""
    w, h, pitch = bitmap.width, bitmap.rows, bitmap.pitch
    if w == 0 or h == 0:
        return Image.new("RGB" if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_LCD else "L", (1, 1), 0)
    buf = bytes(bitmap.buffer)
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_LCD:
        # For LCD bitmaps FreeType reports `width` in *subpixels* (3 per pixel),
        # one byte each, with rows padded up to `pitch`.
        pw = w // 3
        rows = [buf[y * pitch : y * pitch + pw * 3] for y in range(h)]
        return Image.frombytes("RGB", (max(1, pw), h), b"".join(rows))
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_MONO:
        # 1 bit per pixel, MSB first, rows padded to `pitch`.
        out = bytearray(w * h)
        for y in range(h):
            row = buf[y * pitch : y * pitch + (w + 7) // 8]
            for x in range(w):
                bit = (row[x >> 3] >> (7 - (x & 7))) & 1
                out[y * w + x] = 255 if bit else 0
        return Image.frombytes("L", (w, h), bytes(out))
    # FT_PIXEL_MODE_GRAY (also BGRA→use gray channel defensively)
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_BGRA:
        return Image.frombytes(
            "RGBA", (w, h), b"".join(buf[y * pitch : y * pitch + w * 4] for y in range(h))
        ).getchannel("A")
    rows = [buf[y * pitch : y * pitch + w] for y in range(h)]
    return Image.frombytes("L", (w, h), b"".join(rows))


def _blend(mask: Image.Image, fg: tuple[int, int, int, int], bg: tuple[int, int, int, int]) -> Image.Image:
    """Apply a coverage mask to the foreground colour."""
    if mask.mode == "L":
        out = Image.new("RGBA", mask.size, fg)
        out.putalpha(mask)
        return out
    # LCD: per-subpixel coverage, so blend each channel separately.
    fg_img = Image.new("RGB", mask.size, fg[:3])
    bg_img = Image.new("RGB", mask.size, bg[:3])
    bands = []
    for i in range(3):
        a = mask.getchannel(i)
        band = ImageChops.add(
            ImageChops.multiply(bg_img.getchannel(i), ImageChops.invert(a)),
            ImageChops.multiply(fg_img.getchannel(i), a),
        )
        bands.append(band)
    out = Image.merge("RGB", bands).convert("RGBA")
    out.putalpha(255)
    return out


def _size_and_ascent(face, size: int) -> tuple[int, int]:
    face.set_pixel_sizes(0, max(1, int(size)))
    asc = face.size.ascender / 64.0
    desc = face.size.descender / 64.0
    return int(round(asc)), int(round(abs(desc)))


def render_glyph(
    cp: int,
    *,
    family: str = "Arial",
    style: str = "",
    size: int = 32,
    quality: int = 4,
    fg: str = "#000000",
    bg: str = "#ffffff",
    cell: tuple[int, int] | None = None,
    scale: int = 1,
) -> Image.Image:
    """Rasterise one code point into a cell image."""
    path, index, _ = resolve_face(family, style)
    face = freetype.Face(path, index)
    spec = quality_spec(quality)
    if spec["lcd"] is not None:
        _lcd_filter(spec["lcd"])
    asc, desc = _size_and_ascent(face, size * max(1, scale))
    try:
        face.load_char(int(cp), spec["flags"])
    except Exception:
        face.load_char(0, spec["flags"])
    bitmap = face.glyph.bitmap
    mask = _coverage_image(face, bitmap)
    layer = _blend(mask, _hex_rgba(fg, "#000000"), _hex_rgba(bg, "#ffffff"))

    if cell is None:
        w = max(mask.width, int(round(face.glyph.advance.x / 64.0)))
        h = asc + desc
        cell = (max(1, w), max(1, h))
    cw, ch = max(1, cell[0]), max(1, cell[1])
    img = Image.new("RGBA", (cw, ch), _hex_rgba(bg, "#ffffff"))
    x = (cw - mask.width) // 2
    # Baseline-centred vertical placement: the glyph's bitmap_top is the
    # distance from the baseline to its top edge.
    baseline = (ch + asc - desc) // 2
    y = baseline - face.glyph.bitmap_top
    img.alpha_composite(layer, (x, y))
    return img


def render_text(
    text: str,
    *,
    family: str = "Arial",
    style: str = "",
    size: int = 32,
    quality: int = 4,
    fg: str = "#000000",
    bg: str = "#ffffff",
    scale: int = 1,
) -> Image.Image:
    """Rasterise a whole line — the Font Quality dialog's sample."""
    path, index, _ = resolve_face(family, style)
    face = freetype.Face(path, index)
    spec = quality_spec(quality)
    if spec["lcd"] is not None:
        _lcd_filter(spec["lcd"])
    asc, desc = _size_and_ascent(face, size * max(1, scale))
    fgc = _hex_rgba(fg, "#000000")
    bgc = _hex_rgba(bg, "#ffffff")

    pen_x = 0
    pen_y = asc
    placed: list[tuple[Image.Image, int, int]] = []
    for ch in text or " ":
        cp = ord(ch)
        if ch == "\n":
            continue
        try:
            face.load_char(cp, spec["flags"])
        except Exception:
            pen_x += int(size * 0.4)
            continue
        mask = _coverage_image(face, face.glyph.bitmap)
        layer = _blend(mask, fgc, bgc)
        placed.append((layer, pen_x + face.glyph.bitmap_left, pen_y - face.glyph.bitmap_top))
        pen_x += int(round(face.glyph.advance.x / 64.0))

    width = max(1, pen_x) + int(size * 0.25)
    height = max(1, asc + desc) + 4
    img = Image.new("RGBA", (width, height), bgc)
    for layer, x, y in placed:
        img.alpha_composite(layer, (x, y + 2))
    return img


def _encode(img: Image.Image, fmt: str, background: str) -> bytes:
    buf = io.BytesIO()
    f = (fmt or "png").lower()
    if f in ("jpg", "jpeg"):
        img.convert("RGB").save(buf, format="JPEG", quality=92)
    elif f == "bmp":
        img.convert("RGB").save(buf, format="BMP")
    elif f == "gif":
        img.convert("P", palette=Image.ADAPTIVE).save(buf, format="GIF")
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()


def preview_png(**kwargs) -> bytes:
    """PNG bytes for one code point (used by the /api/glyphs/* endpoints)."""
    fmt = kwargs.pop("fmt", "png")
    bg = kwargs.get("bg", "#ffffff")
    return _encode(render_glyph(**kwargs), fmt, bg)


def text_png(**kwargs) -> bytes:
    fmt = kwargs.pop("fmt", "png")
    bg = kwargs.get("bg", "#ffffff")
    return _encode(render_text(**kwargs), fmt, bg)


# ── Batch export ─────────────────────────────────────────────────────


def parse_codepoints(spec: str, limit: int = 20000) -> list[int]:
    """Parse ``"U+41, U+4E00-4E10, 30-39"`` into a code point list."""
    out: list[int] = []
    seen: set[int] = set()
    for token in (spec or "").replace(";", ",").split(","):
        t = token.strip().replace("U+", "").replace("u+", "")
        if not t:
            continue
        if "-" in t:
            lo_s, _, hi_s = t.partition("-")
            try:
                lo, hi = int(lo_s, 16), int(hi_s.lstrip("U+"), 16)
            except ValueError:
                continue
            if lo > hi:
                lo, hi = hi, lo
            for cp in range(lo, min(hi, 0x10FFFF) + 1):
                if cp not in seen:
                    seen.add(cp)
                    out.append(cp)
                if len(out) >= limit:
                    return out
        else:
            try:
                cp = int(t, 16)
            except ValueError:
                continue
            if cp not in seen and 0 <= cp <= 0x10FFFF:
                seen.add(cp)
                out.append(cp)
            if len(out) >= limit:
                return out
    return out


def export_zip(
    cps: list[int],
    *,
    family: str = "Arial",
    style: str = "",
    size: int = 32,
    quality: int = 4,
    fg: str = "#000000",
    bg: str = "#ffffff",
    cell: tuple[int, int] | None = None,
    fmt: str = "png",
    scale: int = 1,
) -> bytes:
    """One image per code point, zipped.  Named ``U+XXXX.png``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for cp in cps:
            try:
                img = render_glyph(
                    cp,
                    family=family,
                    style=style,
                    size=size,
                    quality=quality,
                    fg=fg,
                    bg=bg,
                    cell=cell,
                    scale=scale,
                )
            except Exception:
                continue
            z.writestr(f"U+{cp:04X}.{fmt}", _encode(img, fmt, bg))
    return buf.getvalue()
