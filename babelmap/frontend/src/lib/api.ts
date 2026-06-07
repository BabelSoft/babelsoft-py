/**
 * API client for the Python backend (FastAPI on localhost:17890)
 */
import type { BlockInfo, CodepointInfo, GridPage, PlaneInfo } from "./types";

const BASE = "http://127.0.0.1:17890/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

/** Get all Unicode planes */
export function getPlanes(): Promise<PlaneInfo[]> {
  return get("/planes");
}

/** Get blocks for a specific plane */
export function getBlocks(plane: number): Promise<BlockInfo[]> {
  return get(`/blocks/${plane}`);
}

/** Get all blocks (for the dropdown) */
export function getAllBlocks(): Promise<BlockInfo[]> {
  return get("/blocks");
}

/** Get the character grid for a plane at a scroll position */
export function getGrid(plane: number, scrollPosition: number, fontFamily: string, fontSize: number): Promise<GridPage> {
  const params = new URLSearchParams({
    scroll: scrollPosition.toString(),
    font: fontFamily,
    size: fontSize.toString(),
  });
  return get(`/grid/${plane}?${params}`);
}

/** Get detailed info about a single codepoint */
export function getCodepointInfo(cp: number): Promise<CodepointInfo> {
  return get(`/codepoint/${cp}`);
}

/** Get the glyph image for a codepoint */
export function getGlyphImage(cp: number, fontFamily: string, fontSize: number): Promise<{ codepoint: number; glyph_b64: string | null }> {
  const params = new URLSearchParams({
    font: fontFamily,
    size: fontSize.toString(),
  });
  return get(`/glyph/${cp}?${params}`);
}

/** Search characters by name */
export function searchByName(query: string): Promise<CodepointInfo[]> {
  return get(`/search/name?q=${encodeURIComponent(query)}`);
}

/** Get the available font list */
export function getFonts(): Promise<string[]> {
  return get("/fonts");
}

/** Convert edit buffer text to specified mode */
export function convertEditBuffer(text: string, mode: string): Promise<{ result: string }> {
  const params = new URLSearchParams({ text, mode });
  return get(`/convert/edit?${params}`);
}

/** Navigate: jump to a specific codepoint */
export function jumpToCodepoint(plane: number, cp: number): Promise<GridPage> {
  return get(`/grid/${plane}/goto/${cp}`);
}

/** Navigate: jump to a specific block */
export function jumpToBlock(plane: number, blockName: string): Promise<GridPage> {
  return get(`/grid/${plane}/block/${encodeURIComponent(blockName)}`);
}

/** Navigate: direction buttons */
export function navigateDirection(plane: number, scrollPosition: number, direction: string, fontFamily: string, fontSize: number): Promise<GridPage> {
  const params = new URLSearchParams({
    scroll: scrollPosition.toString(),
    direction,
    font: fontFamily,
    size: fontSize.toString(),
  });
  return get(`/grid/${plane}/navigate?${params}`);
}
