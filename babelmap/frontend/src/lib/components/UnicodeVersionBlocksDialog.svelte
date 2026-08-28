<script lang="ts">
  interface Props {
    show: boolean;
    version: string;
    blocks: {
      name: string;
      start: number;
      end: number;
      chars: number;
      version: string;
    }[];
    onClose: () => void;
  }

  let { show, version, blocks, onClose }: Props = $props();

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
  function hex4(n: number): string {
    return n.toString(16).toUpperCase().padStart(4, "0");
  }
</script>

{#if show}
  <div class="uvbd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="uvbd-header" onmousedown={onDragStart}>
      <span class="uvbd-title">Unicode Version {version} Blocks</span>
      <span class="uvbd-count">{blocks.length} blocks</span>
      <button class="uvbd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="uvbd-table-wrap">
      <table class="uvbd-table">
        <thead>
          <tr>
            <th>Block Name</th>
            <th>Range</th>
            <th>Characters</th>
            <th>Introduced in Version</th>
          </tr>
        </thead>
        <tbody>
          {#each blocks as b}
            <tr>
              <td>{b.name}</td>
              <td class="mono">U+{hex4(b.start)}..U+{hex4(b.end)}</td>
              <td class="num">{fmt(b.chars)}</td>
              <td class="num">{b.version}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="uvbd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .uvbd {
    position: fixed;
    z-index: 320;
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
  .uvbd.dragging,
  .uvbd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .uvbd-header {
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
  .uvbd-header:active {
    cursor: grabbing;
  }
  .uvbd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .uvbd-count {
    font-size: 11px;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.85);
  }
  .uvbd-close {
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
  .uvbd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .uvbd-table-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .uvbd-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: system-ui, sans-serif;
  }
  .uvbd-table th {
    position: sticky;
    top: 0;
    background: var(--bg2);
    color: var(--fg2);
    font-weight: 600;
    padding: 6px 8px;
    border-bottom: 1px solid var(--bd);
    text-align: right;
    white-space: nowrap;
    z-index: 1;
  }
  .uvbd-table th:first-child {
    text-align: left;
  }
  .uvbd-table td {
    padding: 4px 8px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .uvbd-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .uvbd-table td.mono {
    font-family: monospace;
  }
  .uvbd-table tr:hover td {
    background: var(--bg3);
  }
  .uvbd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
