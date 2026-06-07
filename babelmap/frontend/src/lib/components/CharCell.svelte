<script lang="ts">
  import type { GridCell } from "../types";

  interface Props {
    cell: GridCell;
    row: number;
    col: number;
    isSelected: boolean;
    onSelect: () => void;
    onDoubleClick: () => void;
  }

  let {
    cell,
    row,
    col,
    isSelected,
    onSelect,
    onDoubleClick,
  }: Props = $props();

  let tooltip = $state<{ text: string; x: number; y: number } | null>(null);

  function handleClick() {
    onSelect();
  }

  function handleDblClick() {
    onDoubleClick();
  }

  function handleMouseEnter(e: MouseEvent) {
    if (cell.codepoint === 0) return;
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    const name = cell.char_name || `U+${cell.codepoint.toString(16).toUpperCase().padStart(4, "0")}`;
    tooltip = { text: name, x: rect.left + rect.width / 2, y: rect.bottom + 4 };
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
  class="char-cell"
  class:selected={isSelected}
  class:empty={cell.codepoint === 0}
  role="button"
  tabindex="0"
  onclick={handleClick}
  ondblclick={handleDblClick}
  onkeydown={(e) => { if (e.key === 'Enter') handleClick(); }}
  onmouseenter={handleMouseEnter}
  onmouseleave={() => (tooltip = null)}
>
  {#if cell.glyph_b64}
    <img
      src="data:image/png;base64,{cell.glyph_b64}"
      alt={cell.char_name || `U+${cell.codepoint.toString(16)}`}
      class="glyph-img"
    />
  {:else if cell.codepoint > 0}
    <span class="glyph-char">
      {String.fromCodePoint(cell.codepoint)}
    </span>
  {:else}
    <span class="empty-cell"></span>
  {/if}
  <span class="cell-code">
    {cell.codepoint > 0
      ? cell.codepoint.toString(16).toUpperCase().padStart(4, "0")
      : ""}
  </span>
</div>

{#if tooltip}
  <div class="tooltip" style="left:{tooltip.x}px;top:{tooltip.y}px;transform:translateX(-50%)">
    {tooltip.text}
  </div>
{/if}

<style>
  .char-cell {
    flex: 1;
    max-width: 52px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-right: 1px solid var(--border-color);
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-cell);
    cursor: pointer;
    position: relative;
    transition: background 0.1s;
  }
  .char-cell:hover {
    background: var(--bg-cell-hover);
  }
  .char-cell.selected {
    background: var(--bg-cell-selected);
    outline: 1px solid var(--accent);
    z-index: 1;
  }
  .char-cell.empty {
    background: var(--bg-primary);
    cursor: default;
  }

  .glyph-img {
    width: 28px;
    height: 28px;
    object-fit: contain;
  }

  .glyph-char {
    font-size: 22px;
    line-height: 1;
    color: var(--text-primary);
    font-family: inherit;
  }

  .cell-code {
    font-size: 9px;
    font-family: var(--font-mono);
    color: var(--text-muted);
    margin-top: 1px;
  }
</style>
