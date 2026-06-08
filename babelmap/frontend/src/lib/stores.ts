import { writable } from "svelte/store";
import type { BlockInfo, GridPage, PlaneInfo } from "./types";

export const currentPlane = writable(0);
export const scrollPosition = writable(0);
export const planes = writable<PlaneInfo[]>([]);
export const blocks = writable<BlockInfo[]>([]);
export const gridPage = writable<GridPage | null>(null);
export const selectedCell = writable<{ row: number; col: number } | null>(null);

let _g: GridPage | null = null;
gridPage.subscribe((v) => (_g = v));
let _s: { row: number; col: number } | null = null;
selectedCell.subscribe((v) => (_s = v));
export function getSelectedCodepoint(): number | null {
  if (!_s || !_g) return null;
  return _g.cells[_s.row]?.[_s.col]?.codepoint ?? null;
}

export const fontFamily = writable("Arial");
export const fontSize = writable(16);
export const availableFonts = writable<string[]>([]);
export const fontMode = writable<"composite" | "single">("composite");
export const editBuffer = writable("");
export const editBufferMode = writable<"char" | "ncr_hex" | "ncr_dec" | "html" | "ucn">("char");
export const renderMode = writable<"glyph" | "text">("glyph");
export const isLoading = writable(false);
export const statusMessage = writable("Ready");
