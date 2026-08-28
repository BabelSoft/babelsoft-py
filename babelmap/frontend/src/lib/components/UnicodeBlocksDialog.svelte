<script lang="ts">
  import UnicodeBlockCharactersDialog from "./UnicodeBlockCharactersDialog.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
  }

  let { show, onClose }: Props = $props();

  const API = "http://127.0.0.1:18080/api";

  interface BlkRow {
    name: string;
    start: number;
    end: number;
    chars: number;
    version: string;
    code_points: number;
  }

  let version = $state("");
  let blocks = $state<BlkRow[]>([]);
  let loaded = $state(false);
  let selName = $state("");
  let characters = $state<{ codepoint: number; char: string; name: string }[]>([]);
  let charactersLoading = $state(false);
  let showCharacters = $state(false);

  const sel = $derived(blocks.find((b) => b.name === selName));

  // ── Drag / position state ──
  let x = $state(160);
  let y = $state(100);
  let w = $state(Math.min(980, (typeof window !== "undefined" ? window.innerWidth : 980) - 32));
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
    w = Math.max(560, winStartW + (e.clientX - resizeStartX));
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
      const r = await fetch(API + "/unicode/blocks");
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      version = data.version ?? "";
      blocks = data.blocks ?? [];
      if (blocks.length) selName = blocks[0].name;
      loaded = true;
    } catch {
      /* ignore */
    }
  }

  async function loadCharacters(name: string) {
    charactersLoading = true;
    try {
      const r = await fetch(API + "/unicode/blocks/" + encodeURIComponent(name) + "/characters");
      if (!r.ok) throw Error(String(r.status));
      const data = await r.json();
      characters = data.characters ?? [];
    } catch {
      characters = [];
    }
    charactersLoading = false;
  }

  function pick(name: string) {
    selName = name;
    if (showCharacters) loadCharacters(name);
  }

  function toggleCharacters() {
    showCharacters = !showCharacters;
    if (showCharacters && selName) loadCharacters(selName);
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
</script>

{#if show}
  <div class="ubd" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ubd-header" onmousedown={onDragStart}>
      <span class="ubd-title">Unicode Blocks ({version})</span>
      <button class="ubd-chars-btn" onclick={toggleCharacters}>
        {showCharacters ? "Hide Characters" : "Show Characters"}
      </button>
      <button class="ubd-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="ubd-wrap">
      <table class="ubd-table">
        <thead>
          <tr>
            <th>Block Name</th>
            <th>Range</th>
            <th>Code Points</th>
            <th>Characters</th>
            <th>Unicode Version</th>
          </tr>
        </thead>
        <tbody>
          {#each blocks as b}
            <tr class:on={selName === b.name} onclick={() => pick(b.name)}>
              <td>{b.name}</td>
              <td class="mono">U+{hex4(b.start)}..U+{hex4(b.end)}</td>
              <td class="num">{fmt(b.code_points)}</td>
              <td class="num">{fmt(b.chars)}</td>
              <td class="num">{b.version}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <UnicodeBlockCharactersDialog show={showCharacters} blockName={selName} {characters} loading={charactersLoading} onClose={() => (showCharacters = false)} />

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ubd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .ubd {
    position: fixed;
    z-index: 300;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 560px;
    min-height: 240px;
    max-width: calc(100vw - 32px);
    user-select: none;
  }
  .ubd.dragging,
  .ubd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .ubd-header {
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
  .ubd-header:active {
    cursor: grabbing;
  }
  .ubd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .ubd-close {
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
  .ubd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .ubd-chars-btn {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .ubd-chars-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .ubd-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .ubd-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    font-family: system-ui, sans-serif;
  }
  .ubd-table th {
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
  .ubd-table th:first-child {
    text-align: left;
  }
  .ubd-table td {
    padding: 4px 8px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .ubd-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .ubd-table td.mono {
    font-family: monospace;
  }
  .ubd-table tbody tr {
    cursor: pointer;
  }
  .ubd-table tbody tr:hover td {
    background: var(--bg2);
  }
  .ubd-table tbody tr.on td {
    background: var(--ac);
    color: #fff;
  }
  .ubd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
