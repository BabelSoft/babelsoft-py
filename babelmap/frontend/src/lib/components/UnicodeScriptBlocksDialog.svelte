<script lang="ts">
  interface Props {
    show: boolean;
    name: string;
    code: string;
    blocks: {
      name: string;
      chars: number;
      ranges: string[];
    }[];
    loading: boolean;
    onClose: () => void;
  }

  let { show, name, code, blocks, loading, onClose }: Props = $props();

  // ── Drag / position state ──
  let x = $state(700);
  let y = $state(140);
  let w = $state(Math.min(760, (typeof window !== "undefined" ? window.innerWidth : 760) - 32));
  let h = $state(520);
  let dragging = $state(false);
  let dragStartX = $state(0);
  let dragStartY = $state(0);
  let winStartX = $state(0);
  let winStartY = $state(0);

  function onDragStart(e: MouseEvent) {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    winStartX = x;
    winStartY = y;
    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup", onDragEnd);
  }
  function onDragMove(e: MouseEvent) {
    x = winStartX + (e.clientX - dragStartX);
    y = winStartY + (e.clientY - dragStartY);
  }
  function onDragEnd() {
    dragging = false;
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
  }

  // ── Resize state ──
  let resizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartY = $state(0);
  let winStartW = $state(0);
  let winStartH = $state(0);

  function onResizeStart(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    resizing = true;
    resizeStartX = e.clientX;
    resizeStartY = e.clientY;
    winStartW = w;
    winStartH = h;
    document.addEventListener("mousemove", onResizeMove);
    document.addEventListener("mouseup", onResizeEnd);
  }
  function onResizeMove(e: MouseEvent) {
    w = Math.max(400, winStartW + (e.clientX - resizeStartX));
    h = Math.max(240, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
  function rng(r: string): string {
    const p = r.split("..");
    return p.length > 1 ? `U+${p[0]}..U+${p[1]}` : `U+${p[0]}`;
  }
  const total = $derived(blocks.reduce((a, b) => a + b.chars, 0));
</script>

{#if show}
  <div class="usbd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="usbd-header" onmousedown={onDragStart}>
      <span class="usbd-title">Blocks of {name} ({code})</span>
      <span class="usbd-count">{fmt(total)} chars</span>
      <button class="usbd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="usbd-wrap">
      {#if loading}
        <div class="usbd-loading">Loading…</div>
      {:else}
        <table class="usbd-table">
          <thead>
            <tr>
              <th>Block</th>
              <th>Characters</th>
              <th>Range(s)</th>
            </tr>
          </thead>
          <tbody>
            {#each blocks as b}
              <tr>
                <td>{b.name}</td>
                <td class="num">{fmt(b.chars)}</td>
                <td class="mono">{b.ranges.map(rng).join(", ")}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="usbd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .usbd {
    position: fixed;
    z-index: 310;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 400px;
    min-height: 240px;
    max-width: calc(100vw - 32px);
    user-select: none;
  }
  .usbd.dragging,
  .usbd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .usbd-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--ac);
    color: #fff;
    cursor: grab;
    flex-shrink: 0;
    user-select: none;
  }
  .usbd-header:active {
    cursor: grabbing;
  }
  .usbd-title {
    font-size: 13px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .usbd-count {
    font-size: 11px;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.85);
    flex-shrink: 0;
  }
  .usbd-close {
    margin-left: auto;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 4px;
    border-radius: 4px;
  }
  .usbd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .usbd-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .usbd-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: system-ui, sans-serif;
  }
  .usbd-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg3);
    color: var(--fg2);
    font-weight: 600;
    padding: 6px 8px;
    border-bottom: 1px solid var(--bd);
    text-align: right;
    white-space: nowrap;
  }
  .usbd-table th:first-child {
    text-align: left;
  }
  .usbd-table td {
    padding: 4px 8px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .usbd-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .usbd-table td.mono {
    font-family: monospace;
    font-size: 10px;
  }
  .usbd-table tr:hover td {
    background: var(--bg3);
  }
  .usbd-loading {
    padding: 20px;
    color: var(--fg3);
    text-align: center;
  }
  .usbd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
