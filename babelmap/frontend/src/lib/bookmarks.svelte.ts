/**
 * Bookmarks — the port of the original's registry bookmark list
 * (`Registry::AddBookmark` / `DeleteBookmark` / `DeleteAllBookmarks`, used by
 * the Bookmarks menu and `CDialogBookmarks`).
 *
 * Two details are inherited on purpose:
 *
 * * the list is **capped at 32** (`CDialogBookmarks::MaxBookmarks`), and
 * * order is meaningful — the menu lists the bookmarks in insertion order, and
 *   the manage dialog can reorder them by sorting a column
 *   (`ReorderBookmarks()` writes the list back in the new order).
 */
import { settings, type Bookmark } from "./settings.svelte";

/** `CDialogBookmarks::MaxBookmarks`. */
export const MAX_BOOKMARKS = 32;

/** The bookmark list (never `undefined`). */
export function bookmarks(): Bookmark[] {
  return settings.bookmarks ?? [];
}

export function isBookmarked(cp: number): boolean {
  return bookmarks().some((b) => b.cp === cp);
}

/**
 * Append a code point.  Returns the new index, or `-1` when the list is full or
 * the character is already bookmarked (both are silent no-ops in the original,
 * except that the Add button greys out at 32).
 */
export function addBookmark(cp: number, name = ""): number {
  if (!Number.isFinite(cp) || cp < 0 || cp > 0x10ffff) return -1;
  const list = bookmarks();
  if (list.length >= MAX_BOOKMARKS) return -1;
  if (list.some((b) => b.cp === cp)) return -1;
  const next: Bookmark[] = [...list, { cp, name: name || `U+${hex(cp)}` }];
  settings.bookmarks = next;
  return next.length - 1;
}

/** Remove a code point.  Returns whether it was in the list. */
export function removeBookmark(cp: number): boolean {
  const list = bookmarks();
  const next = list.filter((b) => b.cp !== cp);
  if (next.length === list.length) return false;
  settings.bookmarks = next;
  return true;
}

export function clearBookmarks(): void {
  settings.bookmarks = [];
}

/** Replace the whole list (the manage dialog's Remove / reorder path). */
export function setBookmarks(list: Bookmark[]): void {
  settings.bookmarks = list.slice(0, MAX_BOOKMARKS);
}

/** `U+4E00` — the menu label prefix the original uses. */
export function hex(cp: number): string {
  return cp.toString(16).toUpperCase().padStart(4, "0");
}

/** The menu label of one bookmark: `U+4E00 CJK UNIFIED IDEOGRAPH-4E00`. */
export function bookmarkLabel(b: Bookmark): string {
  return `U+${hex(b.cp)} ${b.name}`.trim();
}

/**
 * Parse the Add dialog's input — space-separated hexadecimal code points, the
 * same syntax `BabelString::CodepointsToArray` accepts (also tolerates `U+`,
 * `0x`, commas and decimal `#123`).
 */
export function parseCodepointList(text: string): number[] {
  const out: number[] = [];
  for (const token of (text || "").split(/[\s,;]+/)) {
    const t = token.trim();
    if (!t) continue;
    const decimal = t.startsWith("#");
    const body = t.replace(/^(U\+|0x|#|\$)/i, "");
    const cp = parseInt(body, decimal ? 10 : 16);
    if (!Number.isNaN(cp) && cp >= 0 && cp <= 0x10ffff) out.push(cp);
  }
  return out;
}
