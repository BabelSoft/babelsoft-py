/**
 * Font stack — the single source of truth shared by the character grid and the
 * edit buffer.
 *
 * Modern model (BabelMap's "composite font"): a font stack IS a list of
 * `@font-face` rules applied from front to back — the browser walks the stack
 * and picks the first face whose `unicode-range` covers the character. So
 * *appending* an item means "use this as a later fallback", and the generated
 * CSS is simply the concatenation of every item in order.
 *
 * The dialog owns three things:
 *   1. `items`  — the structured list built by the point-and-click editor;
 *   2. `css`    — the user's hand-written CSS (validated by the backend);
 *   3. `stack`  — the final `font-family` value handed to CSS, i.e. the list of
 *                 family names in order, ending in a generic fallback.
 *
 * `inject()` writes both parts into a single <style> element in <head>, which
 * is what actually makes the table / buffer render with the stack.
 */
import { API_BASE } from "./api";

export type FontStyle = "normal" | "italic" | "oblique";

/** One point-and-click stack entry — compiles to exactly one @font-face rule.
 *
 * A "character", a "character range" and a "code point range" are the same
 * thing here: `unicodeRange` is always a normalized `U+XXXX` / `U+XXXX-YYYY`
 * list, so a single character is just a one-codepoint range.
 */
export interface StackItem {
  id: string;
  /** Either a system family name (used via local(...)) or a user-font id. */
  family: string;
  /** Set when `family` refers to a font uploaded to the backend registry. */
  userId?: string;
  /** How the font is reached: an installed family, or an uploaded file. */
  source: "system" | "user";
  style: FontStyle;
  /**
   * Variable-font axis settings, e.g. ``"wght 600"`` — replaces the old fixed
   * weight list.  Empty for a static face.
   */
  axis?: string;
  stretch: string; // "100%", …
  /** Normalized unicode-range list, e.g. "U+4E00-9FFF, U+3000-303F". */
  unicodeRange: string;
  /** Free-text human note ("CJK ideographs", …) — never sent to CSS verbatim. */
  note?: string;
  enabled: boolean;
}

export interface UserFont {
  id: string;
  name: string;
  file: string;
  ext: string;
  family: string;
  faces: number;
  /** Real face names declared by the file (name ID 2), e.g. ["Bold", "Italic"]. */
  subfamilies?: string[];
  glyphs: number;
  size: number;
  added: string;
}

/**
 * One block's chosen font — the Blocks tab's editable state.
 *
 * This is the layer *above* the stack: the user assigns one font to each
 * Unicode block (either by accepting the Auto winner or by editing a row), and
 * those assignments compile into the leading `@font-face` block of the CSS.
 * It is deliberately separate from `items` so the generated character-range
 * rules stay readable and re-generating never duplicates them.
 */
export interface BlockAssignment {
  /** Unicode block name — the key. */
  block: string;
  family: string;
  /** Set when the font comes from the uploaded-font registry. */
  userId?: string;
  source: "system" | "user";
  style: FontStyle;
  /**
   * Variable-font axis settings, e.g. ``"wght 600, wdth 87.5"``.
   * Empty/undefined for a static face.  There is no fixed weight list — a
   * variable font carries its own axes (read from ``fvar`` in the overview),
   * and a static font's weight is whatever the face already is.
   */
  axis?: string;
  /** Inclusize code point range of the block. */
  start: number;
  end: number;
  /** "auto" = accepted the Auto suggestion, "user" = chosen by hand. */
  origin: "auto" | "user";
}

export const fontStack = $state({
  /** The structured entries, in stack order (append-to-end = later fallback). */
  items: [] as StackItem[],
  /** Hand-written CSS, validated as a whole on the backend. */
  css: "",
  /** Last validation result from the backend. */
  report: null as null | {
    ok: boolean;
    errors: { level: string; message: string; line: number; col: number }[];
    warnings: { level: string; message: string; line: number; col: number }[];
    families: { family: string; line: number }[];
    stats: { fontFaceRules: number; uniqueFamilies: number; errors: number; warnings: number };
  },
  /** True when the stack is actually applied to the grid / buffer. */
  applied: false,
  /**
   * Grid and edit buffer share the stack but keep separate sizes.
   *
   * `null` means "not set yet": the grid then keeps its original responsive
   * `clamp(15px, 4vh, 56px)` and the buffer keeps its CSS row height, so both
   * look exactly like they did before the stack existed.  Ctrl+wheel sets a
   * number and takes over from there.
   */
  gridSize: null as number | null,
  bufferSize: null as number | null,
  /** Names of uploaded fonts, refreshed by the dialog. */
  userFonts: [] as UserFont[],
  /**
   * Per-Unicode-block font choices from the Blocks tab.
   *
   * These compile to the *leading* `@font-face` rules, so a block's font is
   * consulted before any point-and-click entry — matching the reading order of
   * the CSS, which applies front-to-back.
   */
  blocks: [] as BlockAssignment[],
});

let _seq = 0;
export function newItemId(): string {
  return "fs" + Date.now().toString(36) + (_seq++).toString(36);
}

/** Escape a family name for use inside a CSS declaration. */
function quoteFamily(name: string): string {
  return `"${name.replace(/"/g, '\\"')}"`;
}

/**
 * Compile the structured items into `@font-face` rules.
 *
 * Each rule gets a *unique* family name (`<base>__<id>`) so that several items
 * using the same physical font but different ranges/styles never merge into one
 * face. The name exposed to `font-family` is that unique name, which is what
 * makes front-to-back ordering reliable.
 */
export function compileItems(items: StackItem[]): string {
  const out: string[] = [];
  for (const it of items) {
    if (!it.enabled) continue;
    if (!it.family && !it.userId) continue;
    const uniq = itemFamily(it);
    const src = fontSrc(it.source, it.userId, it.family);
    const decl = [
      `font-family: ${quoteFamily(uniq)}`,
      `src: ${src}`,
      it.style && it.style !== "normal" ? `font-style: ${it.style}` : "",
      it.stretch && it.stretch !== "100%" ? `font-stretch: ${it.stretch}` : "",
      variationDecl(it.axis),
      it.unicodeRange ? `unicode-range: ${it.unicodeRange}` : "",
    ].filter(Boolean);
    out.push(`@font-face {\n  ${decl.join(";\n  ")};\n}`);
  }
  return out.join("\n\n");
}

/** The `src:` value for a face — registry URL for uploads, `local()` otherwise. */
function fontSrc(
  source: "system" | "user",
  userId: string | undefined,
  family: string,
): string {
  return source === "user" && userId
    ? `url("${API_BASE}/fonts/user_file?id=${encodeURIComponent(userId)}")`
    : `local(${quoteFamily(family)})`;
}

/**
 * A `font-variation-settings` declaration from an axis string.
 *
 * ``"wght 600, wdth 87.5"`` → ``font-variation-settings: "wght" 600, "wdth" 87.5``.
 * Returns an empty string for a static face (no axes), so nothing is emitted.
 */
function variationDecl(axis?: string): string {
  const parts = (axis || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.replace(/^"?([A-Za-z0-9]{4})"?\s*[:= ]\s*(.+)$/, '"$1" $2'))
    .filter((s) => /^"[A-Za-z0-9]{4}"\s*-?[\d.]+$/.test(s));
  return parts.length ? `font-variation-settings: ${parts.join(", ")}` : "";
}

/** The unique family name one stack item exposes to `font-family`. */
export function itemFamily(it: StackItem): string {
  const base = (it.source === "user" ? it.family || it.userId || "userfont" : it.family || "font")
    .replace(/["\\]/g, "")
    .trim();
  return `${base}__${it.id}`;
}

/** The family name a block assignment exposes (deterministic, per block). */
export function blockFamilyName(a: BlockAssignment): string {
  const base = (a.family || (a.source === "user" ? a.userId : "") || "font")
    .replace(/["\\]/g, "")
    .trim();
  return `${base}__blk_${blockSlug(a.block)}`;
}

/** A CSS-identifier-safe slug for a block name ("Basic Latin" → "Basic_Latin"). */
export function blockSlug(name: string): string {
  return name.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

/** A block's inclusive range as a CSS `unicode-range` value. */
export function blockRangeCss(a: BlockAssignment): string {
  const h = (n: number) => n.toString(16).toUpperCase();
  return a.start === a.end ? `U+${h(a.start)}` : `U+${h(a.start)}-${h(a.end)}`;
}

/**
 * Compile the block assignments into `@font-face` rules.
 *
 * Emitted in code-point order so the generated CSS reads like the Unicode
 * charts, and *before* the point-and-click entries: `unicode-range` is
 * non-overlapping between blocks, and where a later entry does overlap, the
 * later one wins — which is what "append a manual override" means.
 */
export function compileBlocks(blocks: BlockAssignment[]): string {
  const out: string[] = [];
  for (const a of [...blocks].sort((p, q) => p.start - q.start)) {
    if (!a.family && !a.userId) continue;
    const uniq = blockFamilyName(a);
    const decl = [
      `font-family: ${quoteFamily(uniq)}`,
      `src: ${fontSrc(a.source, a.userId, a.family)}`,
      a.style && a.style !== "normal" ? `font-style: ${a.style}` : "",
      variationDecl(a.axis),
      `unicode-range: ${blockRangeCss(a)}`,
    ].filter(Boolean);
    out.push(`/* ${a.block} */\n@font-face {\n  ${decl.join(";\n  ")};\n}`);
  }
  return out.join("\n\n");
}

/** Set (or replace) one block's font, appending in code-point order. */
export function setBlockAssignment(
  a: Omit<BlockAssignment, "origin">,
  origin: "auto" | "user" = "user",
): void {
  const rest = fontStack.blocks.filter((b) => b.block !== a.block);
  fontStack.blocks = [...rest, { ...a, origin }].sort((p, q) => p.start - q.start);
}

/** Drop a block's assignment (reverts the row to "—"). */
export function clearBlockAssignment(block: string): void {
  fontStack.blocks = fontStack.blocks.filter((b) => b.block !== block);
}

/**
 * The `font-family` value for the table / buffer: every block's family first
 * (a block assignment is the most specific match), then every enabled entry's
 * unique family, then the font the user picked as the *base* (if any) and
 * finally a generic family so unstyled characters still render.
 */
export function stackFamily(items: StackItem[], base?: string): string {
  const names = fontStack.blocks
    .filter((a) => a.family || a.userId)
    .map(blockFamilyName);
  names.push(
    ...items.filter((i) => i.enabled && (i.family || i.userId)).map(itemFamily),
  );
  if (base) names.push(quoteFamily(base));
  names.push("serif");
  return names.join(", ");
}

/** Full CSS injected into <head>: block faces, the user's CSS, then entries. */
export function buildCss(items: StackItem[], css: string): string {
  const blocks = compileBlocks(fontStack.blocks);
  const compiled = compileItems(items);
  const user = css.trim();
  const parts = [
    blocks ? `/* ── block assignments ── */\n${blocks}` : "",
    user,
    compiled ? `/* ── stack entries ── */\n${compiled}` : "",
  ].filter(Boolean);
  return parts.join("\n\n");
}

const STYLE_ID = "babelmap-font-stack";

/**
 * Write the stack CSS into <head>. Passing an empty string removes the rules,
 * which restores the grid / buffer to their default styling.
 */
export function inject(css: string): void {
  let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
  if (!css.trim()) {
    if (el) el.textContent = "";
    return;
  }
  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ID;
    document.head.appendChild(el);
  }
  el.textContent = css;
}

/** Normalize free-form user input into a canonical unicode-range list.
 *
 * Accepts: single code points ("4E00", "U+4E00", "你"), ranges ("4E00-9FFF"),
 * comma / whitespace / semicolon separated lists, and `?` wildcards
 * ("U+4E??"). Returns `{range, error}` — `range` is CSS-ready and `error` is
 * set when some token could not be understood.
 */
export function parseRange(input: string): { range: string; error?: string } {
  const raw = (input || "").trim();
  if (!raw) return { range: "" };
  const parts = raw.split(/[,;\s]+/).filter(Boolean);
  const out: string[] = [];
  for (const p of parts) {
    const t = p.trim();
    if (!t) continue;
    // A single literal character → its code point.
    if ([...t].length === 1 && t.codePointAt(0)! > 0x7f) {
      out.push("U+" + t.codePointAt(0)!.toString(16).toUpperCase());
      continue;
    }
    const body = t.replace(/^U\+/i, "");
    if (/^[0-9A-Fa-f]{1,6}\?{1,6}$/.test(body)) {
      out.push("U+" + body.toUpperCase());
      continue;
    }
    const m = body.match(/^([0-9A-Fa-f]{1,6})(?:-([0-9A-Fa-f]{1,6}))?$/);
    if (!m) return { range: out.join(", "), error: `Cannot parse “${t}”` };
    const lo = parseInt(m[1], 16);
    const hi = m[2] ? parseInt(m[2], 16) : lo;
    if (lo > hi) return { range: out.join(", "), error: `“${t}” start is greater than end` };
    if (hi > 0x10ffff) return { range: out.join(", "), error: `“${t}” is beyond U+10FFFF` };
    out.push(hi === lo ? "U+" + m[1].toUpperCase() : `U+${m[1].toUpperCase()}-${m[2].toUpperCase()}`);
  }
  return { range: out.join(", ") };
}

/** Load the list of uploaded fonts from the backend registry. */
export async function loadUserFonts(): Promise<UserFont[]> {
  try {
    const r = await fetch(API_BASE + "/fonts/user");
    const d = await r.json();
    fontStack.userFonts = (d.fonts ?? []) as UserFont[];
  } catch {
    fontStack.userFonts = [];
  }
  return fontStack.userFonts;
}

/** Upload a font file (a File from an <input type=file>) to the registry. */
export async function uploadFont(file: File): Promise<UserFont> {
  const buf = await file.arrayBuffer();
  let bin = "";
  const bytes = new Uint8Array(buf);
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  const res = await fetch(API_BASE + "/fonts/user", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_name: file.name, data_b64: btoa(bin) }),
  });
  const d = await res.json();
  if (!res.ok) throw new Error(d.error || `Upload failed (${res.status})`);
  await loadUserFonts();
  return d as UserFont;
}

/** Remove a font from the registry (the inverse of uploadFont). */
export async function removeUserFont(id: string): Promise<void> {
  const res = await fetch(API_BASE + "/fonts/user/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.error || `Remove failed (${res.status})`);
  await loadUserFonts();
}

/** Validate the user CSS on the backend (compile check). */
export async function validateCss(css: string): Promise<void> {
  try {
    const res = await fetch(API_BASE + "/fonts/composite/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ css }),
    });
    fontStack.report = await res.json();
  } catch {
    fontStack.report = null;
  }
}

/**
 * Apply everything: compile, validate, inject.
 * Returns the compile report so the caller can show 编译通过 / 失败.
 */
export async function applyStack(): Promise<void> {
  const css = buildCss(fontStack.items, fontStack.css);
  inject(css);
  fontStack.applied = true;
  await validateCss(css);
}

/** Turn the stack off entirely (grid / buffer revert to default fonts). */
export function clearStack(): void {
  inject("");
  fontStack.applied = false;
}
