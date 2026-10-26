<script lang="ts">
  import type { GridPage, GridCell } from "../types";

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
</script>

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
  onclick={(e) => {
    const b = (e.target as HTMLElement).closest(
      "button[data-ri]",
    ) as HTMLElement | null;
    if (b) {
      const ri = +b.dataset.ri!;
      const ci = +b.dataset.ci!;
      const now = Date.now();
      if (ri === lastRi && ci === lastCi && now - lastClick < 350) {
        // double-click on the same cell → open character properties
        lastClick = 0;
        onSelect(ri, ci);
        onDblClick(ri, ci);
        return;
      }
      lastClick = now;
      lastRi = ri;
      lastCi = ci;
      onSelect(ri, ci);
      onAddToBuffer(ri, ci);
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
            title={cell.char_name ||
              (cell.codepoint >= 0
                ? `U+${cell.codepoint.toString(16).toUpperCase().padStart(4, "0")}`
                : "")}
          >
            {#if cell.codepoint >= 0}<span class="gc2"
                >{String.fromCodePoint(cell.codepoint)}</span
              >{/if}
          </button>
        {/each}
      {/if}
    {/each}
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
