/**
 * User settings — the persisted state behind the Fonts menu.
 *
 * The original BabelMap keeps this in the Windows registry and reflects it as
 * checkmarks / radio dots in the menu (`OnUpdateOptionsFonts` and friends).
 * A web app has no registry, so this module is the equivalent: one reactive
 * object, mirrored to `localStorage`, that both the menus and the renderers
 * read from.
 *
 * Ownership rules:
 *
 * * this object is the **source of truth** for user preferences;
 * * the live rendering values that other stores already expose
 *   (`fontStack.gridSize`, `fontStack.bufferSize`) are *mirrored* from here by
 *   `applySettings()`, so there is exactly one place a preference is stored.
 */
import { fontStack } from "./fontStack.svelte";

/**
 * The original's `CDialogMap::GridPointSize[][2]` table, in px.
 *
 * The first index is the Fonts ▸ Grid Font Size row (Very Small … Extra
 * Large), the second is the View ▸ Medium/Large Size column.  View ▸ Medium
 * Size and Large Size therefore have nothing to do with the *dialogs*: they
 * select which column of this table feeds the grid, which is why the original
 * passes `m_nDialogSize` into `LoadFont`.
 */
export const GRID_POINT_SIZES = [
  [12, 10],
  [16, 12],
  [20, 16],
  [24, 20],
  [28, 24],
] as const;

/** View ▸ Medium Size / Large Size — the column of `GRID_POINT_SIZES`. */
export type ViewSize = "medium" | "large";

/** The five grid font sizes in the View ▸ Large Size column. */
export const GRID_SIZES = GRID_POINT_SIZES.map((r) => r[0]);

/** Grid font size for a table row, honouring the View menu's size column. */
export function gridPxFor(index: number, viewSize: ViewSize = "medium"): number {
  const col = viewSize === "large" ? 0 : 1;
  const row = GRID_POINT_SIZES[Math.min(Math.max(index, 0), 4)];
  return row[col];
}

/** The Fonts ▸ Grid Font Size row whose *current column* matches `px`. */
export function gridIndexOf(px: number | null, viewSize: ViewSize = "medium"): number {
  if (px == null) return 2;
  const col = viewSize === "large" ? 0 : 1;
  return GRID_POINT_SIZES.findIndex((r) => r[col] === px);
}

/**
 * Font rasterisation quality — the seven `LOGFONT.lfQuality` values, in menu
 * order.  The value is also the index of the menu item, exactly like the
 * original (`nID - IDM_OPTIONS_FONT_QUALITY_DEFAULT`).
 */
export const QUALITY_NAMES = [
  "default",
  "draft",
  "proof",
  "non_antialiased",
  "antialiased",
  "cleartype",
  "cleartype_natural",
] as const;
export type FontQuality = (typeof QUALITY_NAMES)[number];

/**
 * The edit buffer's output format — the original's `eRegistryMapMode`
 * (`eMapModeCharacter` … `eMapModeUCN`, mirrored by Edit ▸ Character Mode).
 */
export type EditMode = "char" | "ncr_hex" | "ncr_dec" | "html" | "ucn";

/**
 * Options ▸ Alternative Representation — the eight `EAltRepr` values from
 * `Unicode/Unicode.h`, in menu order.
 */
export const ALT_REPRS = [
  "decimal",
  "ucn",
  "ucn16",
  "ncr_hex",
  "ncr_dec",
  "html",
  "utf8_hex",
  "utf8_oct",
] as const;
export type AltRepr = (typeof ALT_REPRS)[number];

/** Options ▸ CJKV Readings — `ECJKV` minus the unimplemented Japanese/archaic. */
export const CJKV_READINGS = [
  "mandarin",
  "cantonese",
  "korean",
  "quoc_ngu",
  "viqr",
  "zhuang",
] as const;
export type CjkvReading = (typeof CJKV_READINGS)[number];

/** Options ▸ Tangut Readings — `ETangutReading`, in menu order. */
export const TANGUT_READINGS = [
  "gong2008",
  "kychanov",
  "sofronov",
  "nishida",
  "miyake2012",
  "miyake2015",
] as const;
export type TangutReading = (typeof TANGUT_READINGS)[number];

/**
 * Options ▸ Colour Coding — the eight `EColourCoding` values. The grid paints
 * each cell from the matching property of the code point.
 */
export const COLOUR_CODINGS = [
  "none",
  "gc",
  "bc",
  "bm",
  "dt",
  "nt",
  "script",
  "version",
] as const;
export type ColourCoding = (typeof COLOUR_CODINGS)[number];

/** Options ▸ Character Grid ▸ selection gesture. */
export type SelectClick = "single" | "double";

/** Options ▸ Status Bar ▸ the three independent name/annotation toggles. */
export interface StatusBarFlags {
  /** `eRegistryShowAllCharacterNames` — show algorithmic names (CJK-…, TANGUT-…). */
  algorithmicNames: boolean;
  /** `eRegistryShowCJKReferences` — append the CJK source references. */
  cjkRefs: boolean;
  /** `eRegistryShowTangutReferences` — append the Tangut source references. */
  tangutRefs: boolean;
}

export interface Settings {
  /** Composite = per-block fonts; single = one font for everything. */
  fontMode: "composite" | "single";
  /** The family used in single-font mode (also the grid's base font). */
  singleFamily: string;
  /** Enumerate every face of a family, not just its primary style. */
  allStyles: boolean;
  /** Use the legacy GDI face names instead of the typographic ones. */
  legacyEnum: boolean;
  /** Show symbol-font characters as their ASCII equivalents (U+F020–F0FF). */
  symbolMapping: boolean;
  /** Grid font size in px; `null` = the default row of the current View size. */
  gridSize: number | null;
  /** Edit-buffer font size in px; `null` = keep the CSS default. */
  bufferSize: number | null;
  /** View ▸ Medium/Large Size — the `GRID_POINT_SIZES` column. */
  viewSize: ViewSize;
  /** View ▸ Show Reserved Planes (default `false` = the 7 assigned planes). */
  showReservedPlanes: boolean;
  /** View ▸ Show Unassigned Ranges (`false` = hide unassigned blocks). */
  showReservedRanges: boolean;
  /** View ▸ Keep on Top (`eRegistryStayontop`; desktop shell only). */
  keepOnTop: boolean;
  /** Rasterisation quality index (see `QUALITY_NAMES`). */
  fontQuality: number;
  dark: boolean;
  // ── Edit menu (the original's Rendering Mode / Colour Rendering / Map Mode) ──
  /** Glyph mode (render the glyph) vs text mode (render the character). */
  glyphMode: boolean;
  /** Colour glyphs (`eRegistryColourRendering`). */
  colourGlyphs: boolean;
  /** The edit buffer's output format (`eRegistryMapMode`). */
  editMode: EditMode;
  /** Edit buffer visible (`eRegistryShowEditBuffer`, View ▸ Show Edit Buffer). */
  editBufferVisible: boolean;
  // ── Options menu (`eRegistry*` — one entry per menu item) ──
  /** Unicode Blocks ▸ Alphabetical (`true`) or code point order (`false`). */
  blocksSorted: boolean;
  /** Name Search ▸ Search Aliases (`eRegistrySearchAliases`). */
  searchAliases: boolean;
  /** Goto Codepoint ▸ hexadecimal (`eRegistryHexadecimal`, stored inverted). */
  gotoHex: boolean;
  /** Alternative representation shown for the current character. */
  altRepr: AltRepr;
  /** Which CJKV reading is appended to the description. */
  cjkvReading: CjkvReading;
  /** Uppercase the CJKV readings (`eRegistryUpperCaseReadings`). */
  cjkvUpperCase: boolean;
  /** Show CJKV tones as numbers instead of diacritics (`eRegistryToneNumbers`). */
  cjkvToneNumbers: boolean;
  /** Which Tangut reading source is appended to the description. */
  tangutReading: TangutReading;
  /** Show Tangut tones as numbers (`eRegistryTangutToneNumbers`). */
  tangutToneNumbers: boolean;
  /** Character Grid ▸ single- vs double-click selects a cell. */
  selectClick: SelectClick;
  /** Character Grid ▸ copy the cell as soon as it is selected. */
  copyOnSelect: boolean;
  /** Popup magnification size in px (`eRegistryTooltipSize`: 36/72/108/144). */
  popupMag: number;
  /** Colour coding mode for the character grid. */
  colourCoding: ColourCoding;
  /** Cut & Copy ▸ `plain` or `rtf` (`eRegistryRTFCutandCopy`, inverted). */
  cutCopy: "plain" | "rtf";
  /** Status Bar ▸ show algorithmic (CJK/Tangut/…) character names. */
  showAlgorithmicNames: boolean;
  /** Status Bar ▸ append the CJK source references to the description. */
  showCjkRefs: boolean;
  /** Status Bar ▸ append the Tangut source references to the description. */
  showTangutRefs: boolean;
  /** Other ▸ turn printable ASCII into its NCR form when converting. */
  convertBasicLatin: boolean;
  /** Other ▸ render vertically-oriented scripts rotated (`eRegistryRotateVertical`). */
  rotateVertical: boolean;
  /** Other ▸ close to the system tray instead of quitting (desktop shell only). */
  closeToTray: boolean;
  /** Colour overrides from Options ▸ Customise Colours…, keyed `mode:value`. */
  colourOverrides: Record<string, { bg: string; fg: string }>;
  /**
   * Bookmarks — the original's `eSectionNameBookmarks` list (max 32).
   * The character name is captured when the bookmark is added because the
   * menu has to render it synchronously.
   */
  bookmarks: Bookmark[];
}

/** One entry of the Bookmarks menu / dialog. */
export interface Bookmark {
  cp: number;
  name: string;
}

const KEY = "babelmap.settings.v1";

function defaults(): Settings {
  return {
    fontMode: "composite",
    singleFamily: "Arial",
    allStyles: false,
    legacyEnum: false,
    symbolMapping: false,
    gridSize: null,
    bufferSize: null,
    viewSize: "medium",
    showReservedPlanes: false,
    showReservedRanges: false,
    keepOnTop: false,
    fontQuality: 0,
    dark: false,
    glyphMode: true,
    colourGlyphs: false,
    editMode: "char",
    editBufferVisible: true,
    blocksSorted: true,
    searchAliases: false,
    gotoHex: true,
    altRepr: "decimal",
    cjkvReading: "mandarin",
    cjkvUpperCase: false,
    cjkvToneNumbers: false,
    tangutReading: "gong2008",
    tangutToneNumbers: false,
    selectClick: "single",
    copyOnSelect: false,
    popupMag: 72,
    colourCoding: "none",
    cutCopy: "rtf",
    showAlgorithmicNames: true,
    showCjkRefs: true,
    showTangutRefs: true,
    convertBasicLatin: false,
    rotateVertical: false,
    closeToTray: false,
    colourOverrides: {},
    bookmarks: [],
  };
}

export const settings = $state<Settings>(defaults());

/** Read the saved settings (no-op where there is no `localStorage`). */
export function loadSettings(): void {
  if (typeof localStorage === "undefined") return;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return;
    const d = JSON.parse(raw) as Partial<Settings>;
    const base = defaults();
    for (const k of Object.keys(base) as (keyof Settings)[]) {
      const v = d[k];
      if (v !== undefined && v !== null && typeof v === typeof base[k]) {
        (settings as any)[k] = v;
      } else if (v === null && (k === "gridSize" || k === "bufferSize")) {
        (settings as any)[k] = null;
      }
    }
  } catch {
    // A corrupt entry must never stop the app from starting.
  }
}

/** Write the current settings back. Called from a debounced effect. */
export function saveSettings(): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // Quota / private mode — preferences just stop persisting.
  }
}

/**
 * Push the preferences into the stores that actually render.
 *
 * `fontStack` owns the live sizes (the grid and buffer read them straight from
 * CSS custom properties), so this is a one-way mirror on startup and after
 * every change to a mirrored field.
 */
export function applySettings(): void {
  fontStack.gridSize = settings.gridSize;
  fontStack.bufferSize = settings.bufferSize;
  fontStack.mode = settings.fontMode;
  fontStack.singleFamily = settings.singleFamily;
}

/** True when `gridSize` matches one of the five menu presets. */
export function gridSizeIndex(): number {
  return gridIndexOf(settings.gridSize, settings.viewSize);
}

/**
 * Options ▸ Reset — put every preference back to its default.
 *
 * The original's `OnOptionsReset` asks for confirmation, calls
 * `m_pRegistry->Reset()` and then rebuilds the whole window; here the caller
 * confirms, calls this, and the reactive settings re-render everything, so no
 * reload is needed.
 */
export function resetSettings(): void {
  const base = defaults();
  for (const k of Object.keys(base) as (keyof Settings)[]) {
    (settings as any)[k] = (base as any)[k];
  }
  applySettings();
  saveSettings();
}

// Load immediately so the first render already reflects saved preferences.
loadSettings();
applySettings();
