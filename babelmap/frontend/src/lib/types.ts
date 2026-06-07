/** Unicode Plane definitions */
export interface PlaneInfo {
  plane: number;
  name: string;
  abbreviation: string;
  rangeStart: number;
  rangeEnd: number;
}

/** Block (Unicode block) information */
export interface BlockInfo {
  name: string;
  start: number;
  end: number;
  count: number;
  plane: number;
}

/** Information about a single Unicode character / codepoint */
export interface CodepointInfo {
  codepoint: number;
  name: string;
  general_category: string;
  canonical_combining_class: number;
  bidi_class: string;
  decomposition_type: string;
  decomposition_mapping: string;
  script: string;
  block: string;
  east_asian_width: string;
  age: string;
  /** CJK-specific fields (optional) */
  pinyin?: string[];
  jyutping?: string[];
  korean?: string;
  radical?: string;
  radical_stroke?: string;
  simplified?: number;
  traditional?: number;
}

/** A single cell in the character grid */
export interface GridCell {
  codepoint: number;
  char_name: string | null;
  reserved?: boolean;
}

/** A page of character grid data */
export interface GridPage {
  plane: number;
  block_name: string;
  block_start: number;
  block_end: number;
  block_count: number;
  block_assigned: number;
  scroll_position: number;
  max_scroll: number;
  cells: GridCell[][]; // 8 rows × 16 cols
  row_bases: number[]; // actual codepoint offset (cp - plane*0x10000) for each row
  block_boundaries: number[]; // row indices (0-7) that start a new block
}

/** Edit buffer mode */
export type EditBufferMode = "char" | "ncr_hex" | "ncr_dec" | "html" | "ucn";

/** Rendering mode */
export type RenderMode = "glyph" | "text";

/** Font mode */
export type FontMode = "composite" | "single";

/** Navigation direction */
export type Direction = "plane_start" | "plane_end" | "block_prev" | "block_next" | "page_prev" | "page_next" | "radical_prev" | "radical_next" | "row_start" | "row_end";

/** Status bar info */
export interface StatusInfo {
  message: string;
  current_char: string;
  current_codepoint: number | null;
}
