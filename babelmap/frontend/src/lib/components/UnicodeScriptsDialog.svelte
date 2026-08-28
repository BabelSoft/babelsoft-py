<script lang="ts">
  import UnicodeScriptBlocksDialog from "./UnicodeScriptBlocksDialog.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
  }

  let { show, onClose }: Props = $props();

  const API = "http://127.0.0.1:18080/api";

  interface ScriptRow {
    code: string;
    name: string;
    french: string;
    script: string;
    chars: number;
    version: string;
    notes: string;
  }
  interface BlkRow {
    name: string;
    chars: number;
    ranges: string[];
  }

  let scripts = $state<ScriptRow[]>([]);
  let loaded = $state(false);
  let selCode = $state("");
  let blocks = $state<BlkRow[]>([]);
  let blocksLoading = $state(false);
  let showBlocks = $state(false);

  const sel = $derived(scripts.find((s) => s.code === selCode));

  // ── Drag / position state ──
  let x = $state(160);
  let y = $state(100);
  let w = $state(Math.min(1080, (typeof window !== "undefined" ? window.innerWidth : 1080) - 32));
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
      const r = await fetch(API + "/unicode/scripts");
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      scripts = data.scripts ?? [];
      if (scripts.length) selCode = scripts[0].code;
      loaded = true;
    } catch {
      /* ignore */
    }
  }

  async function loadBlocks(code: string) {
    blocksLoading = true;
    try {
      const r = await fetch(API + "/unicode/scripts/blocks?code=" + encodeURIComponent(code));
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      blocks = data.blocks ?? [];
    } catch {
      blocks = [];
    }
    blocksLoading = false;
  }

  function pick(code: string) {
    selCode = code;
    if (showBlocks) loadBlocks(code);
  }

  function toggleBlocks() {
    showBlocks = !showBlocks;
    if (showBlocks && selCode) loadBlocks(selCode);
  }

  $effect(() => {
    if (show) load();
  });

  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
</script>

{#if show}
  <div class="usd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="usd-header" onmousedown={onDragStart}>
      <span class="usd-title">Unicode Scripts</span>
      <button class="usd-blocks-btn" onclick={toggleBlocks}>
        {showBlocks ? "Hide Blocks" : "Show Blocks"}
      </button>
      <button class="usd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="usd-main">
      <!-- Left: script list -->
      <div class="usd-list">
        <div class="usd-list-head">Scripts ({scripts.length})</div>
        <div class="usd-list-wrap">
          <table class="usd-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Code</th>
                <th>Characters</th>
                <th>Version</th>
              </tr>
            </thead>
            <tbody>
              {#each scripts as s}
                <tr class:on={selCode === s.code} onclick={() => pick(s.code)}>
                  <td>
                    <div class="nm">
                      {s.name}{#if s.french}<span class="fr">&nbsp;&nbsp;{s.french}</span>{/if}
                    </div>
                    {#if s.notes}<div class="notes">{s.notes}</div>{/if}
                  </td>
                  <td class="mono">{s.code}</td>
                  <td class="num">{fmt(s.chars)}</td>
                  <td class="num">{s.version}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <UnicodeScriptBlocksDialog show={showBlocks} name={sel?.name ?? ""} code={selCode} {blocks} loading={blocksLoading} onClose={() => (showBlocks = false)} />

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="usd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .usd {
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
  .usd.dragging,
  .usd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .usd-header {
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
  .usd-header:active {
    cursor: grabbing;
  }
  .usd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .usd-close {
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
  .usd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .usd-blocks-btn {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .usd-blocks-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .usd-main {
    display: flex;
    flex: 1;
    min-height: 0;
  }
  .usd-list {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .usd-list-head {
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 700;
    color: var(--fg3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--bd);
  }
  .usd-list-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .usd-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: system-ui, sans-serif;
  }
  .usd-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg2);
    color: var(--fg2);
    font-weight: 600;
    padding: 4px 8px;
    border-bottom: 1px solid var(--bd);
    text-align: right;
    white-space: nowrap;
  }
  .usd-table th:first-child {
    text-align: left;
  }
  .usd-table td {
    padding: 3px 8px;
    border-bottom: 1px solid var(--bd);
  }
  .usd-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .usd-table td.mono {
    font-family: monospace;
    white-space: nowrap;
  }
  .usd-table td .nm {
    word-break: break-word;
  }
  .usd-table td .nm .fr {
    color: var(--fg3);
    font-size: 10px;
    font-style: italic;
  }
  .usd-table td .notes {
    color: var(--fg3);
    font-size: 10px;
    word-break: break-word;
  }
  .usd-table tbody tr {
    cursor: pointer;
  }
  .usd-table tbody tr:hover td {
    background: var(--bg2);
  }
  .usd-table tbody tr.on td {
    background: var(--ac);
    color: #fff;
  }
  .usd-table tbody tr.on td .notes {
    color: rgba(255, 255, 255, 0.8);
  }
  .usd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
