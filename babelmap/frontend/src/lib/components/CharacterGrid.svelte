<script lang="ts">
  import type { GridPage, GridCell } from "../types";
  import { settings } from "../settings.svelte";
  import { displayChar, isSymbolPua } from "../symbolMappings";
  import { cellColour } from "../colourCoding";

  interface Props {
    grid: GridPage | null;
    plane: number;
    sr: number;
    sc: number;
    /** Font stack (from CompositeFontDialog) — shared with the edit buffer. */
    stackFamily?: string;
    /**
     * Grid font size in px, or `null`/`0` for the original responsive
     * `clamp(15px, 4vh, 56px)` sizing (the default until Ctrl+wheel is used).
     */
    fontSize?: number | null;
    onSelect: (r: number, c: number) => void;
    onAddToBuffer: (r: number, c: number) => void;
    onWheel: (deltaY: number) => void;
    /** Ctrl+wheel over the grid changes the grid font size. */
    onZoom?: (deltaY: number) => void;
    onDblClick?: (r: number, c: number) => void;
  }

  let {
    grid,
    plane,
    sr,
    sc,
    stackFamily = "",
    fontSize = null,
    onSelect,
    onAddToBuffer,
    onWheel,
    onZoom = () => {},
    onDblClick = () => {},
  }: Props = $props();

  // Double-click detection via click timer (more reliable than relying on the
  // browser's dblclick event, which some environments suppress).
  let lastClick = 0;
  let lastRi = -1;
  let lastCi = -1;

  function rowLabel(row: GridCell[], ri: number): string {
    if (row.every((c) => c.codepoint < 0)) return "\u2014";
    const base =
      plane * 0x10000 +
      (grid!.row_bases?.[ri] ?? (grid!.scroll_position + ri) * 16);
    return base.toString(16).toUpperCase().padStart(4, "0").slice(0, -1) + "_";
  }

  function isRowVisible(
    row: GridCell[],
    ri: number,
    allRows: GridCell[][],
  ): boolean {
    return (
      row.some((c) => c.codepoint >= 0) ||
      allRows.slice(ri).every((r) => r.every((c) => c.codepoint < 0))
    );
  }

  /**
   * Options ▸ Character Grid ▸ Copy Character on Select.
   *
   * Copies the *character* (not the cell label) so the clipboard can be pasted
   * into a document straight away.
   */
  function copyIfNeeded(ri: number, ci: number) {
    if (!settings.copyOnSelect) return;
    const cp = grid?.cells[ri]?.[ci]?.codepoint ?? -1;
    if (cp <= 0) return;
    navigator.clipboard?.writeText(String.fromCodePoint(cp)).catch(() => {});
  }

  // ── Options ▸ Colour Coding ─────────────────────────────────────────
  /** The cell's background/foreground, or null when nothing is painted. */
  function colourFor(cell: GridCell) {
    if (settings.colourCoding === "none" || cell.codepoint < 0) return null;
    return cellColour(settings.colourCoding, cell, settings);
  }

  /**
   * Options ▸ Other ▸ Rotate Vertical Scripts.
   *
   * Unicode's two vertical scripts are Mongolian and Phags-pa; their glyphs are
   * rotated a quarter turn in the original's grid.  CSS does that with
   * `writing-mode`, applied per cell so horizontal rows stay intact.
   */
  function isVerticalScript(sc?: string): boolean {
    return sc === "Mongolian" || sc === "Phags_Pa" || sc === "Phags-pa";
  }

  // ── Options ▸ Popup Magnification Level ─────────────────────────────
  //
  // The magnifier is a *deliberate* gesture: it only appears while Ctrl is
  // held, and at a much larger size than the popup level alone would give.  It
  // is a fixed-position overlay that ignores the pointer, so the cells under
  // it — including the neighbours it covers — keep their own hover state.
  let magChar = $state("");
  let magX = $state(0);
  let magY = $state(0);
  let magBelow = $state(false);
  let ctrlHeld = $state(false);
  let hovered = $state<{ ri: number; ci: number; cell: GridCell } | null>(null);

  /**
   * The glyph is drawn at twice the popup level, so the largest setting fills
   * a good part of the screen, clamped so it can never outgrow the viewport.
   */
  function magFontPx(): number {
    if (typeof window === "undefined") return 144;
    const wanted = Math.max(36, settings.popupMag) * 2;
    const cap = Math.min(window.innerWidth, window.innerHeight) * 0.42;
    return Math.round(Math.min(wanted, Math.max(120, cap)));
  }

  function hideMag() {
    magChar = "";
  }

  function showMag() {
    const h = hovered;
    if (!h || !ctrlHeld || h.cell.codepoint < 0) {
      hideMag();
      return;
    }
    const el = document.querySelector(
      `button[data-ri="${h.ri}"][data-ci="${h.ci}"]`,
    ) as HTMLElement | null;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = magFontPx();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    // Size of the box: the glyph plus the padding the CSS adds.
    const boxW = px + 24;
    const boxH = px * 1.1 + 8 + 16;
    // Anchor on the cell's top edge, centred; flip below when there is no room
    // above, and keep the whole box inside the viewport.
    magBelow = r.top - boxH - 8 < 4;
    magX = Math.min(
      Math.max(r.left + r.width / 2, boxW / 2 + 6),
      vw - boxW / 2 - 6,
    );
    magY = magBelow ? r.bottom + 8 : r.top - 8;
    magChar = displayChar(h.cell.codepoint, settings.symbolMapping);
  }

  function hoverCell(ri: number, ci: number, cell: GridCell, ev?: MouseEvent) {
    hovered = { ri, ci, cell };
    // The pointer event's own `ctrlKey` is the authoritative signal: it also
    // covers Ctrl having been pressed before the pointer entered the window.
    const ctrl = ev ? ev.ctrlKey : ctrlHeld;
    if (ctrl) {
      ctrlHeld = true;
      showMag();
    } else {
      hideMag();
    }
  }

  function unhoverCell() {
    hovered = null;
    hideMag();
  }

  // Holding / releasing Ctrl while the pointer is already over a cell has to
  // switch the magnifier on / off without moving the mouse.
  function onCtrlKey(e: KeyboardEvent, down: boolean) {
    if (e.key !== "Control") return;
    if (ctrlHeld === down) return;
    ctrlHeld = down;
    if (down) showMag();
    else hideMag();
  }
</script>

<svelte:window
  onkeydown={(e) => onCtrlKey(e, true)}
  onkeyup={(e) => onCtrlKey(e, false)}
  onblur={() => {
    ctrlHeld = false;
    hideMag();
  }}
/>

<div
  class="gb"
  role="grid"
  tabindex="0"
  style="--grid-font: {stackFamily || 'inherit'};{fontSize
    ? `--grid-size: ${fontSize}px;`
    : ''}"
  onwheel={(e: WheelEvent) => {
    e.preventDefault();
    if (e.ctrlKey) onZoom(e.deltaY);
    else onWheel(e.deltaY);
  }}
  onmousemove={(e: MouseEvent) => {
    // Safety net for a Ctrl release whose keyup never reached the window
    // (focus elsewhere): the first pointer move without Ctrl clears it.
    if (!e.ctrlKey && (ctrlHeld || magChar)) {
      ctrlHeld = false;
      hideMag();
    }
  }}
  onclick={(e) => {
    const b = (e.target as HTMLElement).closest(
      "button[data-ri]",
    ) as HTMLElement | null;
    if (b) {
      const ri = +b.dataset.ri!;
      const ci = +b.dataset.ci!;
      const now = Date.now();
      const isDouble = ri === lastRi && ci === lastCi && now - lastClick < 350;
      if (isDouble) {
        lastClick = 0;
        onSelect(ri, ci);
        if (settings.selectClick === "double") {
          // Double-click mode: the first click only focuses, the double click
          // does the selection work.
          onAddToBuffer(ri, ci);
          copyIfNeeded(ri, ci);
        } else {
          onDblClick(ri, ci);
        }
        return;
      }
      lastClick = now;
      lastRi = ri;
      lastCi = ci;
      // Options ▸ Character Grid ▸ Single Click Selection
      if (settings.selectClick !== "double") {
        onSelect(ri, ci);
        onAddToBuffer(ri, ci);
        copyIfNeeded(ri, ci);
      }
    }
  }}
  onkeydown={(e) => {
    if (
      !(
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
    )
      e.preventDefault();
  }}
>
  {#if grid}
    {#each grid.cells as row, ri (ri)}
      {@const isBB = grid.block_boundaries.includes(ri)}
      {#if isRowVisible(row, ri, grid.cells)}
        <span class="rl" class:bb={isBB}>{rowLabel(row, ri)}</span>
        {#each row as cell, ci (ci)}
          {@const s = sr === ri && sc === ci}
          {@const nch =
            cell.codepoint > 0 &&
            ((cell.codepoint & 0xfffe) === 0xfffe ||
              (cell.codepoint >= 0xfdd0 && cell.codepoint <= 0xfdef))}
          {@const filler = row.every((c) => c.codepoint < 0)}
          {@const cc = colourFor(cell)}
          {@const vert =
            settings.rotateVertical &&
            cell.codepoint >= 0 &&
            isVerticalScript(cell.sc)}
          <button
            class="cel"
            class:empty={cell.codepoint < 0}
            class:reserved={cell.reserved === true}
            class:nonchar={nch}
            class:filler
            class:sel={s}
            class:bb={isBB}
            data-ri={ri}
            data-ci={ci}
            style:background={cc?.bg}
            style:color={cc?.fg}
            title={cell.char_name ||
              (cell.codepoint >= 0
                ? `U+${cell.codepoint.toString(16).toUpperCase().padStart(4, "0")}`
                : "")}
            onmouseenter={(e) => hoverCell(ri, ci, cell, e)}
            onmouseleave={unhoverCell}
          >
            {#if cell.codepoint >= 0}<span
                class="gc2"
                class:sym={settings.symbolMapping &&
                  isSymbolPua(cell.codepoint)}
                class:vert
                title={settings.symbolMapping && isSymbolPua(cell.codepoint)
                  ? `U+${cell.codepoint.toString(16).toUpperCase()} → U+${displayChar(
                      cell.codepoint,
                      true,
                    )
                      .codePointAt(0)!
                      .toString(16)
                      .toUpperCase()}`
                  : undefined}
                >{displayChar(cell.codepoint, settings.symbolMapping)}</span
              >{/if}
          </button>
        {/each}
      {/if}
    {/each}
  {/if}
  {#if magChar}
    <!-- Ctrl + hover: the pointed-at glyph, magnified. -->
    <div
      class="mag"
      class:below={magBelow}
      style:left="{magX}px"
      style:top="{magY}px"
      style:font-size="{magFontPx()}px"
      style:font-family={stackFamily || "inherit"}
    >
      {magChar}
    </div>
  {/if}
</div>

<style>
  .gb {
    flex: 1;
    overflow: visible;
    display: grid;
    grid-template-columns: 64px repeat(16, 1fr);
    grid-auto-rows: 1fr;
    gap: 0;
    min-height: 0;
  }
  .gb::-webkit-scrollbar {
    width: 6px;
  }
  .gb::-webkit-scrollbar-thumb {
    background: var(--sc);
    border-radius: 3px;
  }
  .rl {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 6px;
    font-size: 13px;
    font-family: monospace;
    color: var(--fg3);
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    position: sticky;
    left: 0;
    z-index: 1;
  }
  .cel {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid var(--bd);
    border-right: 1px solid var(--bd);
    background: var(--celbg);
    border-radius: 0;
    color: var(--fg);
    outline: none;
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    transition: all 0.15s;
    overflow: hidden;
  }
  .cel.sel {
    overflow: visible;
    z-index: 2;
    background: var(--ac) !important;
    color: #fff !important;
    border-radius: 2px;
    outline: none;
  }
  .gc2 {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: var(--grid-size, clamp(15px, 4vh, 56px));
    font-family: var(--grid-font, inherit);
    line-height: 1;
    color: inherit;
    pointer-events: none;
  }
  /* A character shown through the symbol-font mapping: the PUA code point is
     replaced by the ASCII/CP1252 character it stands for, so mark it. */
  .gc2.sym {
    color: var(--ac);
  }
  /* Options ▸ Other ▸ Rotate Vertical Scripts */
  .gc2.vert {
    writing-mode: vertical-lr;
    text-orientation: sideways;
  }
  .mag {
    position: fixed;
    z-index: 250;
    padding: 4px 8px;
    background: var(--bg2);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    pointer-events: none;
    line-height: 1.1;
    white-space: nowrap;
    /* Anchored on the cell: centred above it, or below when there is no room. */
    transform: translate(-50%, -100%);
  }
  .mag.below {
    transform: translate(-50%, 0);
  }
  .cel.bb {
    border-top: 2px solid var(--fg);
  }
  .cel:hover {
    background: var(--celh);
  }
  .cel.empty {
    background: var(--nonchar);
    opacity: 1;
  }
  .cel.filler {
    background: var(--bg3);
    opacity: 0.5;
  }
  .cel.reserved {
    background: var(--bg3);
    opacity: 0.55;
  }
  .cel.reserved .gc2 {
    opacity: 0.35;
  }
  .cel.nonchar {
    background: var(--nonchar);
    opacity: 1;
  }
  .cel.nonchar .gc2 {
    opacity: 0.25;
  }
  .cel.sel .gc2 {
    background: var(--ac);
    color: #fff;
    border-radius: 2px;
  }
</style>
