/**
 * Alternative representations of a code point — a port of the original's
 * `Unicode::ConvertToCharRef`, `Unicode::GetUTF8` and the `SetDescription()`
 * alt-code switch (`Dialogs/DialogMap.cpp`, `Unicode/Unicode.cpp`).
 *
 * Two callers share this:
 *
 * * **Options ▸ Alternative Representation** — the field next to the character
 *   name in the info bar (`m_pAltCode` in the original);
 * * **Edit ▸ Character Mode** — the same formats applied to the whole edit
 *   buffer (`eMapModeNCRHex` … `eMapModeUCN`).
 *
 * The formats are byte-for-byte what the original produces:
 *
 * | mode       | BMP `A`   | astral `😀`               |
 * | ---------- | --------- | ------------------------- |
 * | `decimal`  | `Decimal 65` | `Decimal 128512`       |
 * | `ucn`      | `\u0041`  | `\U0001F600`              |
 * | `ucn16`    | `\u0041`  | `\uD83D\uDE00`            |
 * | `ncr_hex`  | `&#x0041;`| `&#x1F600;`               |
 * | `ncr_dec`  | `&#65;`   | `&#128512;`               |
 * | `html`     | `A`       | `&#x1F600;`               |
 * | `utf8_hex` | `\x41`    | `\xF0\x9F\x98\x80`        |
 * | `utf8_oct` | `\101`    | `\360\237\230\200`        |
 */
import type { AltRepr, EditMode } from "./settings.svelte";

/** The five XML named entities the original emits (`ConvertToCharRef`). */
const XML_ENTITIES: Record<number, string> = {
  0x22: "&quot;",
  0x26: "&amp;",
  0x27: "&apos;",
  0x3c: "&lt;",
  0x3e: "&gt;",
};

/** UTF-8 bytes of one code point. */
export function utf8Bytes(cp: number): number[] {
  if (cp < 0x80) return [cp];
  if (cp < 0x800) return [0xc0 | (cp >> 6), 0x80 | (cp & 0x3f)];
  if (cp < 0x10000)
    return [0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f)];
  return [
    0xf0 | (cp >> 18),
    0x80 | ((cp >> 12) & 0x3f),
    0x80 | ((cp >> 6) & 0x3f),
    0x80 | (cp & 0x3f),
  ];
}

/** UTF-8 bytes as `\xXX…` (hex) or `\NNN…` (octal), like `Unicode::GetUTF8`. */
export function utf8Escaped(cp: number, octal = false): string {
  return utf8Bytes(cp)
    .map((b) =>
      octal ? "\\" + b.toString(8).padStart(3, "0") : "\\x" + b.toString(16).toUpperCase().padStart(2, "0"),
    )
    .join("");
}

const hex4 = (n: number) => n.toString(16).toUpperCase().padStart(4, "0");

/**
 * `Unicode::ConvertToCharRef` — one code point as an escape sequence.
 *
 * `convertBasicLatin` is Options ▸ Other ▸ Convert Basic Latin: when it is
 * *off* (the default, like the original's `eRegistryConvertASCII`), printable
 * ASCII is emitted literally instead of being escaped.
 */
export function charRef(
  cp: number,
  kind: EditMode | AltRepr,
  convertBasicLatin = false,
): string {
  if (cp > 0x1f && cp < 0x7f && !convertBasicLatin) {
    return String.fromCodePoint(cp);
  }
  switch (kind) {
    case "ncr_hex":
      return `&#x${hex4(cp)};`;
    case "ncr_dec":
      return `&#${cp};`;
    case "ucn":
      return cp < 0x10000
        ? `\\u${hex4(cp)}`
        : `\\U${cp.toString(16).toUpperCase().padStart(8, "0")}`;
    case "html": {
      const ent = XML_ENTITIES[cp];
      if (ent) return ent;
      if (cp > 0xffff || cp < 0x20) return `&#x${hex4(cp)};`;
      // 0x20..0x7E minus the five specials stay literal; everything above
      // (which is not a XML entity we know) falls back to a numeric reference.
      if (cp < 0x7f) return String.fromCodePoint(cp);
      return `&#x${hex4(cp)};`;
    }
    default:
      return String.fromCodePoint(cp);
  }
}

/**
 * The info bar's "alternative representation" field — `SetDescription()`'s
 * switch, including the literal `Decimal N` wording of the original.
 */
export function altRepresentation(
  cp: number | null | undefined,
  kind: AltRepr,
  convertBasicLatin = false,
): string {
  if (cp == null || cp < 0) return "";
  switch (kind) {
    case "decimal":
      return `Decimal ${cp}`;
    case "ucn":
      return charRef(cp, "ucn", true);
    case "ucn16":
      if (cp <= 0xffff) return charRef(cp, "ucn", true);
      // Surrogate pair, each half as its own UCN escape.
      return [0xd800 + ((cp - 0x10000) >> 10), 0xdc00 + ((cp - 0x10000) & 0x3ff)]
        .map((s) => charRef(s, "ucn", true))
        .join("");
    case "ncr_hex":
      return charRef(cp, "ncr_hex", true);
    case "ncr_dec":
      return charRef(cp, "ncr_dec", true);
    case "html":
      return charRef(cp, "html", true);
    case "utf8_hex":
      return utf8Escaped(cp, false);
    case "utf8_oct":
      return utf8Escaped(cp, true);
    default:
      return String(cp);
  }
}

/**
 * Parse an alternate representation back to characters (the inverse used by
 * Edit ▸ Character Mode when switching format).
 */
export function revertToChars(text: string, from: EditMode): string {
  if (from === "char") return text;
  if (from === "ncr_hex") {
    return text.replace(/&#x([0-9A-Fa-f]+);/g, (_, h) => {
      const cp = parseInt(h, 16);
      return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
    });
  }
  if (from === "ncr_dec") {
    return text.replace(/&#(\d+);/g, (_, d) => {
      const cp = parseInt(d, 10);
      return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
    });
  }
  if (from === "html") {
    return text
      .replace(/&#x([0-9A-Fa-f]+);/g, (_, h) =>
        String.fromCodePoint(parseInt(h, 16)),
      )
      .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
      .replace(/&quot;/g, '"')
      .replace(/&apos;/g, "'")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&amp;/g, "&");
  }
  if (from === "ucn") {
    return text
      .replace(/\\u([0-9A-Fa-f]{4})/g, (_, h) =>
        String.fromCodePoint(parseInt(h, 16)),
      )
      .replace(/\\U([0-9A-Fa-f]{8})/g, (_, h) =>
        String.fromCodePoint(parseInt(h, 16)),
      );
  }
  return text;
}
