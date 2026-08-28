<script lang="ts">
  import UnicodePlaneBlocksDialog from "./UnicodePlaneBlocksDialog.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
  }

  let { show, onClose }: Props = $props();

  const API = "http://127.0.0.1:18080/api";

  interface PlaneRow {
    plane: number;
    name: string;
    abbreviation: string;
    reserved: boolean;
    blocks: number;
    chars: number;
    unassigned: number;
  }
  interface BlkRow {
    name: string;
    start: number;
    end: number;
    count: number;
  }

  let planes = $state<PlaneRow[]>([]);
  let loaded = $state(false);
  let selPlane = $state(0);
  let blocks = $state<BlkRow[]>([]);
  let blocksLoading = $state(false);
  let showBlocks = $state(false);

  const sel = $derived(planes.find((p) => p.plane === selPlane));

  // ── Drag / position state ──
  let x = $state(160);
  let y = $state(100);
  let w = $state(Math.min(900, (typeof window !== "undefined" ? window.innerWidth : 900) - 32));
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
    w = Math.max(500, winStartW + (e.clientX - resizeStartX));
    h = Math.max(240, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  async function load() {
    if (loaded) return;
    try {
      const r = await fetch(API + "/unicode/planes");
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      planes = data.planes ?? [];
      loaded = true;
    } catch {
      /* ignore */
    }
  }

  async function loadBlocks(plane: number) {
    blocksLoading = true;
    try {
      const r = await fetch(API + `/unicode/planes/${plane}/blocks`);
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      blocks = data.blocks ?? [];
    } catch {
      blocks = [];
    }
    blocksLoading = false;
  }

  function pick(plane: number) {
    selPlane = plane;
    if (showBlocks) loadBlocks(plane);
  }

  function toggleBlocks() {
    showBlocks = !showBlocks;
    if (showBlocks) loadBlocks(selPlane);
  }

  $effect(() => {
    if (show) load();
  });

  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
</script>

{#if show}
  <div class="upd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="upd-header" onmousedown={onDragStart}>
      <span class="upd-title">Unicode Planes</span>
      <button class="upd-blocks-btn" onclick={toggleBlocks}>
        {showBlocks ? "Hide Blocks" : "Show Blocks"}
      </button>
      <button class="upd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="upd-wrap">
      <table class="upd-table">
        <thead>
          <tr>
            <th>Plane</th>
            <th>Plane Name</th>
            <th>Abbreviation</th>
            <th>Blocks</th>
            <th>Characters</th>
            <th>Unassigned Code Points</th>
          </tr>
        </thead>
        <tbody>
          {#each planes as p}
            <tr class:on={selPlane === p.plane} onclick={() => pick(p.plane)}>
              <td class="num">{p.plane}</td>
              <td>{p.reserved ? "<reserved>" : p.name}</td>
              <td class="mono">{p.abbreviation}</td>
              <td class="num">{fmt(p.blocks)}</td>
              <td class="num">{fmt(p.chars)}</td>
              <td class="num">{fmt(p.unassigned)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <UnicodePlaneBlocksDialog
      show={showBlocks}
      plane={selPlane}
      name={sel?.name ?? ""}
      abbreviation={sel?.abbreviation ?? ""}
      reserved={sel?.reserved ?? false}
      {blocks}
      loading={blocksLoading}
      onClose={() => (showBlocks = false)}
    />

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="upd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .upd {
    position: fixed;
    z-index: 300;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 500px;
    min-height: 240px;
    max-width: calc(100vw - 32px);
    user-select: none;
  }
  .upd.dragging,
  .upd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .upd-header {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    padding: 8px 12px;
    background: var(--ac);
    color: #fff;
    cursor: grab;
    flex-shrink: 0;
    user-select: none;
  }
  .upd-header:active {
    cursor: grabbing;
  }
  .upd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .upd-close {
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
  .upd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .upd-blocks-btn {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .upd-blocks-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .upd-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .upd-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: system-ui, sans-serif;
  }
  .upd-table th {
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
  .upd-table th:nth-child(2) {
    text-align: left;
  }
  .upd-table td {
    padding: 4px 8px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .upd-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .upd-table td.mono {
    font-family: monospace;
  }
  .upd-table tbody tr {
    cursor: pointer;
  }
  .upd-table tbody tr:hover td {
    background: var(--bg2);
  }
  .upd-table tbody tr.on td {
    background: var(--ac);
    color: #fff;
  }
  .upd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
