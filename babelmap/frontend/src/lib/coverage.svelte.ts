/**
 * Composite-font coverage — the frontend side of `backend/font_coverage.py`.
 *
 * The backend port of BabelMap's `CDialogConfig` produces, per Unicode block:
 *   - how many characters the block holds (`total`),
 *   - every font that covers it (`fonts`), with per-font covered counts,
 *   - the best font (`best_font`) and *why* it won,
 *   - the running coverage summary (`covered_blocks` / `covered_chars`).
 *
 * The scan is the expensive part, so the streaming endpoint (`/stream`) is used
 * and its progress bar is surfaced the same way Font Overview does it.
 */
import { API_BASE } from "./api";

export interface BlockFont {
  index: number;
  family: string;
  subfamily: string;
  weight: number;
  covered: number;
  total: number;
  ratio: number;
  preferred: boolean;
}

export interface BlockRow {
  name: string;
  start: number;
  end: number;
  plane: number;
  total: number;
  covered: number;
  ratio: number;
  best_font: string;
  best_subfamily: string;
  best_index: number;
  best_weight: number;
  preferred_font: string;
  pua: boolean;
  fonts: BlockFont[];
  font_count: number;
  /** Sample characters from this block, for the in-row preview. */
  preview: string;
}

export interface CoverageSummary {
  total_blocks: number;
  covered_blocks: number;
  total_chars: number;
  covered_chars: number;
  ratio: number;
}

export interface AutoAssignment {
  block: string;
  start: number;
  end: number;
  plane: number;
  font: string;
  subfamily: string;
  index: number;
  covered: number;
  total: number;
  ratio: number;
  pua: boolean;
  reason: string;
}

/**
 * One block's characters plus per-font coverage, as a **bitset**.
 *
 * ``masks[j]`` is base64 for the bitset of face ``fonts[j]``: bit ``i`` is set
 * when that face maps ``cps[i]``.  The server sends this instead of a
 * per-character ``supported_by`` index list because that form does not scale —
 * CJK Unified Ideographs is 20 992 chars × ~84 covering faces = 1.77 M integers
 * (~7 MB of JSON, ~4 s).  Decode with `maskHas()` / `supportSet()`.
 */
export interface BlockChars {
  name: string;
  start: number;
  end: number;
  plane: number;
  total: number;
  /** Ascending code points; index-aligned with the bits in every mask. */
  cps: number[];
  /** Face indices that cover at least one character of this block. */
  fonts: number[];
  /** Base64 bitsets, one per entry of `fonts`. */
  masks: string[];
}

/** A block's characters decoded for one face: code point → covered? */
export interface BlockSupport {
  cps: number[];
  chars: string[];
  has: Uint8Array;
  /** Number of characters in ``cps`` this face maps. */
  covered: number;
}

export const coverageStore = $state({
  blocks: [] as BlockRow[],
  summary: null as CoverageSummary | null,
  imported: 0,
  loading: false,
  loaded: false,
  error: "",
  /** Scan progress (same shape as the Font Overview scanner). */
  scanDone: 0,
  scanTotal: 0,
  scanFile: "",
  scanStarted: 0,
  scanElapsed: 0,
  /** Result of the last Auto run. */
  auto: [] as AutoAssignment[],
  autoSummary: null as null | {
    total_blocks: number;
    assigned_blocks: number;
    covered_blocks: number;
    unassigned_blocks: number;
  },
  autoRunning: false,
  /**
   * True once the scan has been kicked off.  The app starts it right after the
   * window is up (`startCoverageScan()`), so the expensive font analysis runs
   * while the user is reading the toolbar instead of when they finally open the
   * dialog, and the progress bar lives at the bottom of the app.
   */
  started: false,
  /**
   * Full character lists per block, keyed by block name.  Loaded on demand when
   * a block is selected — a block can hold 20 000+ characters, so they are not
   * part of the coverage table itself.
   */
  chars: {} as Record<string, BlockChars>,
  charLoading: false,
  /** Ticks while a scan runs so elapsed-time readouts re-render. */
  tick: 0,
});

/**
 * Keep ``tick`` moving while a scan is in flight.
 *
 * `scanElapsed()` reads the wall clock, so without something reactive changing
 * the elapsed readout would freeze at whatever it was on the last real event.
 * Called once from `App.svelte`; it starts/stops itself based on `loading`.
 */
export function startScanTicker(): void {
  setInterval(() => {
    if (coverageStore.loading) coverageStore.tick++;
  }, 250);
}

/** Scan progress 0–100. Svelte 5 modules cannot export `$derived` state, so
 * this is a plain function the caller invokes (it still re-runs reactively
 * because it reads the `$state` proxy). */
export function scanPct(): number {
  const s = coverageStore;
  void s.tick;
  return s.scanTotal > 0 ? Math.min(100, (s.scanDone / s.scanTotal) * 100) : 0;
}

/** Seconds elapsed since the current scan started (0 when idle).
 *
 * Reads `tick` so callers re-render while the ticker is running. */
export function scanElapsed(): number {
  const s = coverageStore;
  void s.tick;
  return s.scanStarted ? (Date.now() - s.scanStarted) / 1000 : 0;
}

/**
 * Load the per-block coverage table, streaming scan progress.
 *
 * `only` narrows the backend to a single block (much less JSON); passing it
 * replaces the table because the caller asked for a different view.
 */
export async function loadCoverage(only?: string): Promise<void> {
  const s = coverageStore;
  s.loading = true;
  s.error = "";
  s.scanDone = 0;
  s.scanTotal = 0;
  s.scanFile = "";
  s.scanStarted = Date.now();
  s.scanElapsed = 0;
  try {
    const q = only ? `?block=${encodeURIComponent(only)}` : "";
    const r = await fetch(API_BASE + "/fonts/coverage/stream" + q);
    if (!r.ok) throw new Error(String(r.status));
    const reader = r.body?.getReader();
    if (!reader) throw new Error("Stream not supported");
    const dec = new TextDecoder();
    let buf = "";
    let got = false;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") continue;
        if (payload.startsWith("SCAN ")) {
          try {
            const p = JSON.parse(payload.slice(5));
            s.scanDone = p.done ?? 0;
            s.scanTotal = p.total ?? 0;
            s.scanFile = p.file ?? "";
          } catch {
            /* skip malformed */
          }
        } else if (payload.startsWith("ERROR ")) {
          s.error = JSON.parse(payload.slice(6));
        } else if (payload.startsWith("RESULT ")) {
          const d = JSON.parse(payload.slice(7));
          s.blocks = d.blocks ?? [];
          s.summary = d.summary ?? null;
          s.imported = d.imported ?? 0;
          got = true;
        }
      }
    }
    if (!got && !s.error) throw new Error("No data");
    s.loaded = true;
  } catch (e: any) {
    s.error = e?.message || "Failed to load coverage";
  }
  s.loading = false;
}

/**
 * Kick the coverage scan off at app start (idempotent).
 *
 * Called from `App.svelte` once the shell is mounted, so the CPU-heavy font
 * analysis overlaps with the user's first interactions.  Failing here is fine:
 * the dialog retries on demand.
 */
export function startCoverageScan(): void {
  const s = coverageStore;
  if (s.started || s.loading || s.loaded) return;
  s.started = true;
  void loadCoverage();
}

/**
 * Load the full character list of one block (cached per block name).
 *
 * The list is the packed bitset form — see `BlockChars`.  Decode per face with
 * `supportSet()`; the dialog does that once per (block, selected font).
 */
export async function loadBlockChars(block: string): Promise<void> {
  const s = coverageStore;
  if (!block || s.chars[block]) return;
  s.charLoading = true;
  try {
    const r = await fetch(
      API_BASE + "/fonts/coverage/chars?block=" + encodeURIComponent(block),
    );
    if (!r.ok) throw new Error(String(r.status));
    const d = (await r.json()) as BlockChars;
    s.chars = { ...s.chars, [block]: d };
  } catch (e: any) {
    s.error = e?.message || `Failed to load characters for ${block}`;
  }
  s.charLoading = false;
}

/** Decode a base64 bitset into a byte array (browser + Node safe). */
export function decodeMask(b64: string): Uint8Array {
  if (typeof atob === "function") {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  // Fallback for non-browser contexts (tests / SSR).
  const buf = (globalThis as any).Buffer;
  if (buf) return new Uint8Array(buf.from(b64, "base64"));
  throw new Error("No base64 decoder available");
}

/**
 * Decode one face's coverage of a block into a form the grid can index.
 *
 * Returns the block's code points and characters together with a byte-per-char
 * lookup array, so `has[i]` is the answer for `cps[i]` in O(1) — the preview
 * grid asks this question once per rendered cell.
 */
export function supportSet(data: BlockChars, faceIndex: number): BlockSupport {
  const cps = data.cps;
  const j = data.fonts.indexOf(faceIndex);
  const has = new Uint8Array(cps.length);
  let covered = 0;
  if (j >= 0) {
    const bits = decodeMask(data.masks[j]);
    for (let i = 0; i < cps.length; i++) {
      if (bits[i >> 3] & (1 << (i & 7))) {
        has[i] = 1;
        covered++;
      }
    }
  }
  return { cps, chars: cps.map((cp) => String.fromCodePoint(cp)), has, covered };
}

/** Run the backend **Auto** assignment (best font per block). */export async function runAuto(): Promise<void> {
  const s = coverageStore;
  s.autoRunning = true;
  s.error = "";
  try {
    const r = await fetch(API_BASE + "/fonts/coverage/auto");
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || String(r.status));
    s.auto = d.assignments ?? [];
    s.autoSummary = d.summary ?? null;
  } catch (e: any) {
    s.error = e?.message || "Auto failed";
  }
  s.autoRunning = false;
}

/** The Auto winner for one block, if Auto has been run. */
export function autoFor(block: string): AutoAssignment | undefined {
  return coverageStore.auto.find((a) => a.block === block);
}

/** `U+XXXX..U+YYYY` for a block row. */
export function blockRange(b: { start: number; end: number }): string {
  const h = (n: number) => n.toString(16).toUpperCase().padStart(4, "0");
  return `U+${h(b.start)}..U+${h(b.end)}`;
}

/** Format a count with thin thousands separators. */
export function fmtInt(n: number): string {
  return (n || 0).toLocaleString();
}
