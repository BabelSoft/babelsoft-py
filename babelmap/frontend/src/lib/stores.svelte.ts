/**
 * Svelte 5 reactive global state —$state objects with .v property.
 * Usage: import * as store from "../stores.svelte"; store.currentPlane.value = 5;
 */
import type { BlockInfo, GridPage, PlaneInfo } from "./types";

export const currentPlane = $state({ v: 0 });
export const scrollPosition = $state({ v: 0 });
export const planes = $state<{ v: PlaneInfo[] }>({ v: [] });
export const blocks = $state<{ v: BlockInfo[] }>({ v: [] });
export const gridPage = $state<{ v: GridPage | null }>({ v: null });
export const selectedCell = $state<{ v: { row: number; col: number } | null }>({ v: null });

export function getSelectedCodepoint(): number | null {
  const g = gridPage.v;
  const s = selectedCell.v;
  if (!s || !g) return null;
  return g.cells[s.row]?.[s.col]?.codepoint ?? null;
}

export const fontFamily = $state({ v: "Arial" });
export const fontSize = $state({ v: 16 });
export const availableFonts = $state<{ v: string[] }>({ v: [] });
export const fontMode = $state<{ v: "composite" | "single" }>({ v: "composite" });
export const editBuffer = $state({ v: "" });
export const editBufferMode = $state<{ v: "char" | "ncr_hex" | "ncr_dec" | "html" | "ucn" }>({ v: "char" });
export const renderMode = $state<{ v: "glyph" | "text" }>({ v: "glyph" });
export const isLoading = $state({ v: false });
export const statusMessage = $state({ v: "Ready" });
