"""Font container / format normalisation for the shaping engines.

The shaping engines disagree about what they accept, so BabelMap normalises the
font *before* handing it over — exactly like a real text stack (GDI / DirectWrite
/ CoreText) would:

* **TrueType / OpenType collections** (``.ttc`` / ``.otc`` — ``ttcf``) hold
  several faces in one file.  uharfbuzz and HarfRust take a face index, but
  DWriteCore / Uniscribe / Graphite / ICU / FreeType have no way to be told, and
  Yudit's ``SFontTTF`` refuses collections outright
  (``BAD TTF file ... sfntVersion=74746366``).
* **WOFF / WOFF2** wrap a single sfnt in a compressed container that no shaping
  engine reads directly.

:func:`prepare` therefore resolves *what to give the engine* — see
:data:`DELIVERIES`:

``auto`` (default)
    Pass a plain single-face sfnt through untouched; flatten anything else
    (collection / WOFF / WOFF2) into a standalone single-face sfnt.  This is the
    mode that makes every engine behave the same on every input.
``flatten``
    Always hand over a flattened standalone sfnt (even for a plain sfnt, which is
    re-sliced byte-for-byte).
``raw``
    Hand the original bytes *plus* the face index to the engine — only meaningful
    for the engines that support a face index (HarfBuzz / HarfRust); useful to
    compare an engine's own collection handling against our extraction.

Flattening is a **byte-level sfnt slice**, not a fontTools re-serialisation: the
chosen face's table directory is copied, each referenced table is copied
verbatim (4-byte aligned, offsets rebased) and ``head.checkSumAdjustment`` is
recomputed, so nothing about the glyph data can change.  ``zlib`` (WOFF) and
fontTools+``brotli`` (WOFF2) are used only to unwrap the container.

The dialog uses :func:`describe` to offer a face picker and shows which delivery
mode was applied (see the *Font source* controls in ``OpenTypeTestDialog``).
"""

from __future__ import annotations

import io
import struct
import zlib
from dataclasses import dataclass, field

__all__ = [
    "DELIVERIES",
    "FaceInfo",
    "FaceNotFound",
    "FontSourceError",
    "Prepared",
    "container_of",
    "describe",
    "face_count",
    "flatten",
    "prepare",
]

#: Delivery modes accepted by :func:`prepare` (also the UI's dropdown values).
DELIVERIES = ("auto", "flatten", "raw")

_SFNT_MAGIC = b"\x00\x01\x00\x00"
_SFNT_TAGS = (b"OTTO", b"true", b"typ1")
_TTC_MAGIC = b"ttcf"
_WOFF_MAGIC = b"wOFF"
_WOFF2_MAGIC = b"wOF2"

# Container labels reported to the UI.
_CONTAINER_LABELS = {
    "sfnt": "sfnt (single face)",
    "ttc": "TTC/OTC collection",
    "woff": "WOFF",
    "woff2": "WOFF2",
    "unknown": "unknown",
}


class FontSourceError(ValueError):
    """The font container/format could not be handled."""


class FaceNotFound(FontSourceError):
    """The requested face index does not exist in this font (user error)."""


# ── container detection ──────────────────────────────────────────────────────


def container_of(data: bytes) -> str:
    """Classify ``data``: ``sfnt`` / ``ttc`` / ``woff`` / ``woff2`` / ``unknown``."""
    if len(data) < 4:
        return "unknown"
    magic = bytes(data[:4])
    if magic == _TTC_MAGIC:
        return "ttc"
    if magic == _SFNT_MAGIC or magic in _SFNT_TAGS:
        return "sfnt"
    if magic == _WOFF_MAGIC:
        return "woff"
    if magic == _WOFF2_MAGIC:
        return "woff2"
    return "unknown"


def _label(container: str) -> str:
    return _CONTAINER_LABELS.get(container, container)


# ── low-level sfnt assembly ──────────────────────────────────────────────────


def _ttc_face_offsets(data: bytes) -> list[int]:
    """Face offsets from a ``ttcf`` header (absolute, into this file)."""
    if len(data) < 12:
        raise FontSourceError("truncated TTC header")
    version, num_fonts = struct.unpack_from(">II", data, 4)
    if version not in (0x00010000, 0x00020000):
        raise FontSourceError(f"unsupported TTC version 0x{version:08X}")
    if num_fonts <= 0 or 12 + 4 * num_fonts > len(data):
        raise FontSourceError("TTC header declares an impossible face count")
    return [struct.unpack_from(">I", data, 12 + 4 * i)[0] for i in range(num_fonts)]


def _face_directory(data: bytes, face_offset: int) -> tuple[bytes, list[tuple[bytes, int, int, int]]]:
    """``(sfnt_version, [(tag, checksum, offset, length), ...])`` for one face."""
    if face_offset + 12 > len(data):
        raise FontSourceError("face offset is past the end of the file")
    version = bytes(data[face_offset : face_offset + 4])
    if version not in (_SFNT_MAGIC, *_SFNT_TAGS):
        raise FontSourceError(f"face at {face_offset} is not an sfnt table directory")
    num_tables = struct.unpack_from(">H", data, face_offset + 4)[0]
    if num_tables <= 0 or num_tables > 512:
        raise FontSourceError(f"implausible table count {num_tables}")
    tables: list[tuple[bytes, int, int, int]] = []
    for i in range(num_tables):
        rec = face_offset + 12 + 16 * i
        if rec + 16 > len(data):
            raise FontSourceError("truncated table directory")
        tag, checksum, offset, length = struct.unpack_from(">4sIII", data, rec)
        if offset + length > len(data):
            raise FontSourceError(f"table {tag!r} runs past the end of the file")
        tables.append((tag, checksum, offset, length))
    return version, tables


def _assemble_sfnt(version: bytes, tables: list[tuple[bytes, int, bytes]]) -> bytes:
    """Build a standalone sfnt from ``(tag, checksum, payload)`` triples."""
    num_tables = len(tables)
    # searchRange / entrySelector / rangeShift, per the OpenType spec.
    entry_selector = max(num_tables.bit_length() - 1, 0)
    search_range = (1 << entry_selector) * 16
    range_shift = num_tables * 16 - search_range

    # Lay the tables out 4-byte aligned after the directory, then write both.
    positions: list[int] = []
    pos = 12 + 16 * num_tables
    for _, _, payload in tables:
        pos += (-pos) % 4
        positions.append(pos)
        pos += len(payload)

    out = bytearray()
    out += version
    out += struct.pack(">HHHH", num_tables, search_range, entry_selector, range_shift)
    for (tag, checksum, payload), table_pos in zip(tables, positions):
        out += struct.pack(">4sIII", tag, checksum, table_pos, len(payload))
    for (_, _, payload), table_pos in zip(tables, positions):
        out += b"\0" * (table_pos - len(out))
        out += payload

    _fix_head_checksum(out)
    return bytes(out)


def _fix_head_checksum(out: bytearray) -> None:
    """Recompute ``head.checkSumAdjustment`` for the freshly assembled font.

    Best-effort: the value only matters to validators (shaping never reads it),
    so any problem here must not fail the extraction.
    """
    try:
        num_tables = struct.unpack_from(">H", out, 4)[0]
        head_offset = None
        for i in range(num_tables):
            tag, _checksum, offset, _length = struct.unpack_from(">4sIII", out, 12 + 16 * i)
            if tag == b"head":
                head_offset = offset
                break
        if head_offset is None or head_offset + 12 > len(out):
            return
        struct.pack_into(">I", out, head_offset + 8, 0)  # zero before summing
        if len(out) % 4:
            out += b"\0" * (4 - len(out) % 4)
        total = sum(struct.unpack(f">{len(out) // 4}I", bytes(out))) & 0xFFFFFFFF
        struct.pack_into(">I", out, head_offset + 8, (0xB1B0AFBA - total) & 0xFFFFFFFF)
    except Exception:  # pragma: no cover - never break extraction over a checksum
        pass


# ── flattening ───────────────────────────────────────────────────────────────


def _flatten_ttc(data: bytes, face_index: int) -> bytes:
    offsets = _ttc_face_offsets(data)
    if not 0 <= face_index < len(offsets):
        raise FaceNotFound(
            f"face {face_index} does not exist — {len(offsets)} face(s) available (0-{len(offsets) - 1})"
        )
    version, tables = _face_directory(data, offsets[face_index])
    return _assemble_sfnt(version, [(tag, checksum, bytes(data[o : o + n])) for tag, checksum, o, n in tables])


def _flatten_woff(data: bytes) -> bytes:
    if len(data) < 44:
        raise FontSourceError("truncated WOFF header")
    flavor = bytes(data[4:8])
    num_tables = struct.unpack_from(">H", data, 12)[0]
    tables: list[tuple[bytes, int, bytes]] = []
    for i in range(num_tables):
        rec = 44 + 20 * i
        if rec + 20 > len(data):
            raise FontSourceError("truncated WOFF table directory")
        tag, offset, comp_len, orig_len, orig_checksum = struct.unpack_from(">4sIIII", data, rec)
        blob = bytes(data[offset : offset + comp_len])
        if comp_len != orig_len:
            try:
                blob = zlib.decompress(blob)
            except zlib.error as exc:
                raise FontSourceError(f"WOFF table {tag!r} failed to inflate: {exc}") from exc
        tables.append((tag, orig_checksum, blob))
    return _assemble_sfnt(flavor, tables)


def _flatten_woff2(data: bytes) -> bytes:
    """WOFF2 → sfnt via fontTools (needs the optional ``brotli`` dependency)."""
    try:
        from fontTools.ttLib import woff2  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - very old fontTools
        raise FontSourceError(f"WOFF2 needs fontTools' woff2 module: {exc}") from exc
    # fontTools exposes `haveBrotli` as a bool in current releases and as a
    # function in older ones — accept both.
    have = getattr(woff2, "haveBrotli", None)
    missing = have is False if isinstance(have, bool) else bool(callable(have) and not have())
    if missing:
        raise FontSourceError("WOFF2 needs the 'brotli' package (pip install brotli)")
    try:
        out = io.BytesIO()
        woff2.decompress(io.BytesIO(bytes(data)), out)
        sfnt = out.getvalue()
    except Exception as exc:
        raise FontSourceError(f"WOFF2 decompression failed: {exc}") from exc
    return sfnt


def flatten(data: bytes, face_index: int = 0) -> bytes:
    """Return a **standalone single-face sfnt** for face ``face_index``.

    A plain sfnt is returned unchanged; collections/WOFF are re-assembled
    byte-for-byte (see the module docstring).
    """
    container = container_of(data)
    if container == "sfnt":
        if face_index:
            raise FaceNotFound("this file holds a single face (only face 0 exists)")
        return bytes(data)
    if container == "ttc":
        return _flatten_ttc(data, int(face_index))
    if container == "woff":
        if face_index:
            raise FaceNotFound("this file holds a single face (only face 0 exists)")
        return _flatten_woff(data)
    if container == "woff2":
        sfnt = _flatten_woff2(data)
        # Decompressed WOFF2 is normally a single face, but stay honest if not.
        if container_of(sfnt) in ("ttc", "woff", "woff2"):
            return flatten(sfnt, face_index)
        return sfnt
    raise FontSourceError("not a recognised font container (sfnt/TTC/WOFF/WOFF2)")


# ── face enumeration ─────────────────────────────────────────────────────────


@dataclass
class FaceInfo:
    """One face inside the supplied font data."""

    index: int
    family: str | None = None
    subfamily: str | None = None
    full_name: str | None = None
    glyph_count: int | None = None
    outlines: str | None = None  # "CFF" | "glyf"
    error: str | None = None

    @property
    def label(self) -> str:
        """Human label for the UI's face dropdown."""
        bits = [b for b in (self.family, self.subfamily) if b]
        name = " ".join(bits) if bits else f"face {self.index}"
        extra = []
        if self.glyph_count:
            extra.append(f"{self.glyph_count} glyphs")
        if self.outlines:
            extra.append(self.outlines)
        return f"{self.index}: {name}" + (f" · {', '.join(extra)}" if extra else "")

    def as_dict(self) -> dict:
        d = {
            "index": self.index,
            "family": self.family,
            "subfamily": self.subfamily,
            "full_name": self.full_name,
            "glyph_count": self.glyph_count,
            "outlines": self.outlines,
            "label": self.label,
        }
        if self.error:
            d["error"] = self.error
        return d


def _face_infos_from_fonttools(data: bytes, index: int) -> FaceInfo:
    info = FaceInfo(index=index)
    try:
        from fontTools.ttLib import TTFont

        tt = TTFont(io.BytesIO(bytes(data)), fontNumber=index, lazy=True)
        name = tt["name"]
        info.family = name.getDebugName(1)
        info.subfamily = name.getDebugName(2)
        info.full_name = name.getDebugName(4)
        if "maxp" in tt:
            info.glyph_count = int(tt["maxp"].numGlyphs)  # type: ignore[attr-defined]
        tables = set(getattr(tt.reader, "tables", {}) or {})
        if tables & {"CFF ", "CFF2"}:
            info.outlines = "CFF"
        elif "glyf" in tables:
            info.outlines = "glyf"
        tt.close()
    except Exception as exc:
        info.error = f"{type(exc).__name__}: {exc}"
    return info


def _face_offsets(data: bytes) -> list[int]:
    """Face table-directory offsets for the container (``[]`` when not a TTC)."""
    if container_of(data) == "ttc":
        try:
            return _ttc_face_offsets(data)
        except FontSourceError:
            return []
    return [0]


def face_count(data: bytes) -> int:
    """Number of faces in the container — 1 for anything that is not a TTC/OTC.

    Cheap (reads the ``ttcf`` header only), so the font list can show it.
    """
    if container_of(data) != "ttc":
        return 1
    try:
        return len(_ttc_face_offsets(data))
    except FontSourceError:
        return 1


def describe(data: bytes) -> dict:
    """Report the container and its faces so the UI can offer a face picker.

    Returns ``{container, container_label, is_collection, face_count, faces,
    flatten_supported, note}``; ``faces`` entries are :meth:`FaceInfo.as_dict`.
    """
    container = container_of(data)
    offsets = _face_offsets(data)
    faces = [_face_infos_from_fonttools(data, i).as_dict() for i in range(len(offsets))] or [
        FaceInfo(index=0, error="unrecognised container").as_dict()
    ]

    note: str | None = None
    flatten_supported = True
    if container == "woff2":
        try:
            flatten(data, 0)
        except FontSourceError as exc:
            flatten_supported = False
            note = f"WOFF2 cannot be unwrapped here: {exc}"
    elif container == "unknown":
        flatten_supported = False
        note = "unrecognised font container — pass a .ttf/.otf/.ttc/.otc/.woff/.woff2 file"

    return {
        "container": container,
        "container_label": _label(container),
        "is_collection": container == "ttc",
        "face_count": len(offsets),
        "faces": faces,
        "flatten_supported": flatten_supported,
        "size": len(data),
        "note": note,
    }


# ── the entry point used by the API ──────────────────────────────────────────


@dataclass
class Prepared:
    """What :func:`prepare` decided to hand to the shaping engine."""

    data: bytes  # bytes for the engine
    face_index: int  # face index for the engine (0 after flattening)
    delivery: str  # mode actually applied
    container: str  # container of the input
    flattened: bool
    requested_face: int
    original: bytes = b""  # the untouched input bytes
    info: dict = field(default_factory=dict)  # serialisable summary for the API
    notes: list[str] = field(default_factory=list)


def prepare(data: bytes, *, delivery: str = "auto", face_index: int = 0) -> Prepared:
    """Resolve the engine-facing font bytes + face index (see module docstring).

    Never raises for an unsupported container: it falls back to the raw bytes and
    records why in ``notes``, so the shaping request still reports a real engine
    error rather than a font-source error.
    """
    data = bytes(data)
    requested_face = max(int(face_index or 0), 0)
    container = container_of(data)
    mode = delivery if delivery in DELIVERIES else "auto"
    notes: list[str] = []

    # `auto`: a plain sfnt goes through untouched, everything else is flattened.
    effective = "flatten" if (mode == "auto" and container != "sfnt") else mode
    if mode == "auto" and container == "sfnt":
        effective = "raw"

    out, out_face, flattened = data, requested_face, False
    if effective == "flatten":
        try:
            out = flatten(data, requested_face)
            out_face, flattened = 0, True
        except FaceNotFound:
            raise  # a bad face index is a user error — never silently ignored
        except FontSourceError as exc:
            notes.append(f"flatten failed, using the original bytes: {exc}")
            out, out_face = data, requested_face
            effective = "raw"

    if effective == "raw" and container == "ttc":
        notes.append(
            "handed over as a collection: only HarfBuzz/HarfRust honour the face "
            "index, the other engines will read face 0 or fail"
        )
    if container == "unknown":
        notes.append("unrecognised font container — the engine will report the failure")

    return Prepared(
        data=out,
        face_index=out_face,
        delivery=effective,
        container=container,
        flattened=flattened,
        requested_face=requested_face,
        original=data,
        notes=notes,
        info={
            "container": container,
            "container_label": _label(container),
            "is_collection": container == "ttc",
            "requested_face": requested_face,
            "face_index": out_face,
            "delivery": effective,
            "requested_delivery": mode,
            "flattened": flattened,
            "size_in": len(data),
            "size_out": len(out),
            "notes": notes,
        },
    )
