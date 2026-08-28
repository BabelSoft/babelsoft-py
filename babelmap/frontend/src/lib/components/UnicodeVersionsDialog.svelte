<script lang="ts">
  import UnicodeVersionBlocksDialog from "./UnicodeVersionBlocksDialog.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
  }

  let { show, onClose }: Props = $props();

  const API = "http://127.0.0.1:18080/api";

  interface HistoryRow {
    version: string;
    date: string;
    scripts: number;
    blocks: number;
    total: number;
    assigned: number;
    unassigned: number;
    named: number;
    graphic: number;
    format: number;
    control: number;
    pua: number;
    nonchar: number;
    surrogate: number;
    added: number;
  }
  interface BlkRow {
    name: string;
    start: number;
    end: number;
    chars: number;
    version: string;
  }

  let history = $state<HistoryRow[]>([]);
  let blocksByVersion = $state<Record<string, BlkRow[]>>({});
  let loaded = $state(false);
  let selVersion = $state("1.0.0");

  // ── Drag / position state ──
  let x = $state(160);
  let y = $state(100);
  let w = $state(Math.min(1280, (typeof window !== "undefined" ? window.innerWidth : 1280) - 32));
  let h = $state(560);
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

  async function load() {
    if (loaded) return;
    try {
      const r = await fetch(API + "/unicode/versions");
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      history = data.history ?? [];
      blocksByVersion = data.blocks_by_version;
      if (!history.some((h) => h.version === selVersion)) {
        selVersion = history.at(-1)?.version ?? selVersion;
      }
      loaded = true;
    } catch {
      /* ignore */
    }
  }

  $effect(() => {
    if (show) load();
  });

  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
  function hex4(n: number): string {
    return n.toString(16).toUpperCase().padStart(4, "0");
  }

  const blocks = $derived(blocksByVersion[selVersion] ?? []);
  let showBlocks = $state(false);
</script>

{#if show}
  <div class="uvd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="uvd-header" onmousedown={onDragStart}>
      <span class="uvd-title">Unicode Versions</span>
      <button class="uvd-blocks-btn" onclick={() => (showBlocks = !showBlocks)}>
        {showBlocks ? "Hide Blocks" : "Show Blocks"}
      </button>
      <button class="uvd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="uvd-main">
      <!-- Left: version history -->
      <div class="uvd-hist">
        <div class="uvd-hist-head">Version History</div>
        <div class="uvd-hist-wrap">
          <table class="uvd-hist-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Date</th>
                <th>Scripts</th>
                <th>Blocks</th>
                <th>Total</th>
                <th>Assigned</th>
                <th>Unassigned</th>
                <th>Named</th>
                <th>Graphic</th>
                <th>Format</th>
                <th>Control</th>
                <th>Priv. Use</th>
                <th>Nonchars</th>
                <th>Surrogates</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {#each history as h}
                <tr class:on={selVersion === h.version} onclick={() => (selVersion = h.version)}>
                  <td class="num mono">{h.version}</td>
                  <td class="date">{h.date}</td>
                  <td class="num">{fmt(h.scripts)}</td>
                  <td class="num">{fmt(h.blocks)}</td>
                  <td class="num">{fmt(h.total)}</td>
                  <td class="num">{fmt(h.assigned)}</td>
                  <td class="num">{fmt(h.unassigned)}</td>
                  <td class="num">{fmt(h.named)}</td>
                  <td class="num">{fmt(h.graphic)}</td>
                  <td class="num">{fmt(h.format)}</td>
                  <td class="num">{fmt(h.control)}</td>
                  <td class="num">{fmt(h.pua)}</td>
                  <td class="num">{fmt(h.nonchar)}</td>
                  <td class="num">{fmt(h.surrogate)}</td>
                  <td class="num">{fmt(h.added)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="uvd-resize" onmousedown={onResizeStart}></div>

    <UnicodeVersionBlocksDialog show={showBlocks} version={selVersion} {blocks} onClose={() => (showBlocks = false)} />
  </div>
{/if}

<style>
  .uvd {
    position: fixed;
    z-index: 300;
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
  .uvd.dragging,
  .uvd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .uvd-header {
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
  .uvd-header:active {
    cursor: grabbing;
  }
  .uvd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .uvd-close {
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
  .uvd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .uvd-main {
    display: flex;
    flex: 1;
    min-height: 0;
  }
  .uvd-hist {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .uvd-hist-head {
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 700;
    color: var(--fg3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--bd);
  }
  .uvd-hist-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .uvd-hist-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 10px;
    font-family: system-ui, sans-serif;
  }
  .uvd-hist-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg2);
    color: var(--fg2);
    font-weight: 600;
    padding: 4px 6px;
    border-bottom: 1px solid var(--bd);
    text-align: right;
    white-space: nowrap;
  }
  .uvd-hist-table th:first-child {
    text-align: left;
  }
  .uvd-hist-table td {
    padding: 3px 6px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .uvd-hist-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .uvd-hist-table td.mono {
    font-family: monospace;
  }
  .uvd-hist-table td.date {
    color: var(--fg3);
  }
  .uvd-hist-table tbody tr {
    cursor: pointer;
  }
  .uvd-hist-table tbody tr:hover td {
    background: var(--bg2);
  }
  .uvd-hist-table tbody tr.on td {
    background: var(--ac);
    color: #fff;
  }
  .uvd-hist-table tbody tr.on td.date {
    color: rgba(255, 255, 255, 0.8);
  }
  .uvd-blocks-btn {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .uvd-blocks-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .uvd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
