/**
 * Colour coding for the character grid 鈥?Options 鈻?Colour Coding.
 *
 * The original paints each cell from a colour table per coding mode
 * (`m_csGenCatColours`, `m_csBidiClassColours`, `m_csScriptColours`,
 * `m_csVersionColours`, 鈥?in `Dialogs/DialogMap.cpp`).  Those tables are
 * hand-tuned and the script one has an entry for every one of the ~170 scripts,
 * so they cannot be copied one-to-one into a small module.
 *
 * This module therefore has two layers:
 *
 * 1. **Curated** colours for the values people actually look at 鈥?the 30
 *    General Categories, the 23 Bidi Classes, the 2 Mirroring states, the 17
 *    Decomposition Types, the 4 Numeric Types, the major scripts and the 17
 *    Unicode versions.  These are hand-picked, like the original.
 * 2. **Derived** colours for everything else (mostly the long tail of scripts),
 *    where the hue comes from a stable hash of the value so a script always
 *    gets the same colour between sessions and machines.
 *
 * Options 鈻?Customise Colours鈥?stores per-value overrides in
 * `settings.colourOverrides` and they win over both layers.
 */
import type { ColourCoding, Settings } from "./settings.svelte";

/** A cell's background / foreground pair. */
export interface CellColour {
  bg: string;
  fg: string;
}

/** Readability threshold: dark backgrounds get white text. */
function fgFor(bg: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(bg);
  if (!m) return "#000000";
  const n = parseInt(m[1], 16);
  const r = (n >> 16) & 0xff;
  const g = (n >> 8) & 0xff;
  const b = n & 0xff;
  // ITU-R BT.601 luma
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#101010" : "#ffffff";
}

/** Stable hash 鈫?hue, used for values without a curated colour. */
function hueOf(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) >>> 0;
  return h % 360;
}

function pastel(hue: number, sat = 62, light = 84): string {
  return hsl(hue, sat, light);
}

function hsl(h: number, s: number, l: number): string {
  // HSL 鈫?hex, so the value can go straight into `settings.colourOverrides`.
  const a = (s / 100) * Math.min(l / 100, 1 - l / 100);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const c = l / 100 - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)));
    return Math.round(255 * c)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * General Category 鈥?one colour per two-letter code.  Grouped by meaning:
 * letters green/blue, marks purple, numbers orange, punctuation yellow,
 * symbols pink, separators grey, and the "other" family dark.
 */
const GC: Record<string, string> = {
  Lu: "#cfe3ff",
  Ll: "#e2f0ff",
  Lt: "#bfd7ff",
  Lm: "#d8ecff",
  Lo: "#e8f5e9",
  Mn: "#f3e5f5",
  Mc: "#e8d5f0",
  Me: "#dcc6ea",
  Nd: "#ffe9c7",
  Nl: "#ffdab0",
  No: "#fff0d6",
  Pc: "#fff9c4",
  Pd: "#fdf3b0",
  Ps: "#fbeea1",
  Pe: "#fbeea1",
  Pi: "#f7e6a1",
  Pf: "#f7e6a1",
  Po: "#f4f1b6",
  Sm: "#ffd9e6",
  Sc: "#ffc9dc",
  Sk: "#ffe0ec",
  So: "#ffe9f1",
  Zs: "#e6e8ea",
  Zl: "#dadee1",
  Zp: "#dadee1",
  Cc: "#c9cdd2",
  Cf: "#dde1e5",
  Cs: "#b9bec4",
  Co: "#e4dcd3",
  Cn: "#f4f5f6",
};

/** Bidi Class 鈥?the 23 values of Bidi_Class.txt. */
const BC: Record<string, string> = {
  L: "#dfe9f5",
  R: "#f8dfe0",
  AL: "#f5cfd2",
  EN: "#fdeccd",
  ES: "#fbefd8",
  ET: "#f9f2de",
  AN: "#f6e6bd",
  CS: "#f3f0cf",
  B: "#d6d9dd",
  S: "#e2e5e8",
  WS: "#eceef0",
  ON: "#e9eef3",
  LRE: "#d8e4f0",
  LRO: "#cfdcec",
  RLE: "#f2dbe4",
  RLO: "#eccbd8",
  PDF: "#e5e8ec",
  LRI: "#d8e4f0",
  RLI: "#f2dbe4",
  FSI: "#eee2ef",
  PDI: "#e5e8ec",
  BN: "#dcdfe2",
  NSM: "#eee9f6",
};

/** Bidi_Mirrored */
const BM: Record<string, string> = { True: "#ffe0ec", False: "#eef1f4" };

/** Decomposition_Type */
const DT: Record<string, string> = {
  None_: "#f1f3f5",
  Canonical: "#dceff7",
  Compat: "#e3f2dc",
  Circle: "#fbe9c8",
  Final: "#f2e2f7",
  Font: "#e7e9fb",
  Fraction: "#fde8cf",
  Initial: "#efe3f8",
  Isolated: "#f5e0f2",
  Medial: "#eadff5",
  Narrow: "#e0f2ee",
  Nobreak: "#e8eef9",
  Small: "#f0ece0",
  Square: "#f6eccd",
  Sub: "#e2f4e9",
  Super: "#e8f6e2",
  Vertical: "#f0e8f7",
  Wide: "#ddf0f4",
};

/** Numeric_Type */
const NT: Record<string, string> = {
  Decimal: "#ffe4b8",
  Digit: "#ffedcb",
  Numeric: "#fff4de",
};

/**
 * Major scripts get a hand-picked colour so common blocks stay recognisable;
 * everything else is derived from the name hash.
 */
const SC: Record<string, string> = {
  Latin: "#e3f0ff",
  Greek: "#e6f5ec",
  Cyrillic: "#efe4f7",
  Armenian: "#f7e6dd",
  Hebrew: "#fde8d8",
  Arabic: "#dff0e3",
  Syriac: "#efe8d8",
  Thaana: "#e0ecef",
  Devanagari: "#f9e3ea",
  Bengali: "#e5eaf9",
  Gurmukhi: "#fbe9d8",
  Gujarati: "#e2f0ee",
  Tamil: "#e8e4f6",
  Telugu: "#f6e3e8",
  Kannada: "#e3efe0",
  Malayalam: "#f3e8da",
  Thai: "#e6eef7",
  Lao: "#f0e6f2",
  Tibetan: "#f6e0e2",
  Myanmar: "#e2e9f6",
  Georgian: "#f7e4ea",
  Hangul: "#e7f0f7",
  Ethiopic: "#eef0dd",
  Cherokee: "#efe6e0",
  Canadian_Aboriginal: "#e4f0e4",
  Khmer: "#e6efe9",
  Mongolian: "#e9e6f7",
  Han: "#f7ecdf",
  Hiragana: "#fbe6ef",
  Katakana: "#efe6fb",
  Common: "#eef1f4",
  Inherited: "#f4f1ec",
  Unknown: "#f5f5f5",
};

/** Unicode version major 鈫?a cool鈫抴arm gradient (1.0 鈫?17.0). */
function versionColour(ver: string): string {
  const n = parseInt(ver, 10);
  if (!Number.isFinite(n)) return "#f2f3f4";
  const t = Math.max(0, Math.min(1, (n - 1) / 16));
  return hsl(210 - 210 * t, 55, 88);
}

/** The value of `cell` that a coding mode keys on. */
export function codingKey(
  mode: ColourCoding,
  cell: { gc?: string; bc?: string; bm?: string; dt?: string; nt?: string; sc?: string; ver?: string },
): string {
  switch (mode) {
    case "gc":
      return cell.gc || "";
    case "bc":
      return cell.bc || "";
    case "bm":
      return cell.bm || "";
    case "dt":
      return cell.dt || "";
    case "nt":
      return cell.nt || "";
    case "script":
      return cell.sc || "";
    case "version":
      return cell.ver || "";
    default:
      return "";
  }
}

/** Every distinct value a mode can show, for the Customise Colours dialog. */
export function knownValues(mode: ColourCoding): string[] {
  switch (mode) {
    case "gc":
      return Object.keys(GC);
    case "bc":
      return Object.keys(BC);
    case "bm":
      return Object.keys(BM);
    case "dt":
      return Object.keys(DT);
    case "nt":
      return Object.keys(NT);
    case "script":
      return Object.keys(SC);
    case "version":
      return Array.from({ length: 17 }, (_, i) => String(i + 1));
    default:
      return [];
  }
}

/** The default background for one value of a mode (before any override). */
export function defaultColour(mode: ColourCoding, value: string): string {
  switch (mode) {
    case "gc":
      return GC[value] ?? pastel(hueOf(value));
    case "bc":
      return BC[value] ?? pastel(hueOf(value));
    case "bm":
      return BM[value] ?? pastel(hueOf(value));
    case "dt":
      return DT[value] ?? pastel(hueOf(value));
    case "nt":
      return NT[value] ?? pastel(hueOf(value));
    case "script":
      return SC[value] ?? pastel(hueOf(value));
    case "version":
      return versionColour(value);
    default:
      return "";
  }
}

/**
 * The colours for one cell, or `null` when nothing should be painted.
 *
 * `settings.colourOverrides` is keyed `mode:value`, so switching mode keeps the
 * customisations of every other mode intact.
 */
export function cellColour(
  mode: ColourCoding,
  cell: Parameters<typeof codingKey>[1],
  s: Pick<Settings, "colourOverrides">,
): CellColour | null {
  if (mode === "none") return null;
  const key = codingKey(mode, cell);
  if (!key) return null;
  const over = s.colourOverrides?.[`${mode}:${key}`];
  const bg = over?.bg || defaultColour(mode, key);
  if (!bg) return null;
  return { bg, fg: over?.fg || fgFor(bg) };
}
