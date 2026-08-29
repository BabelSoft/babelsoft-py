<script lang="ts">
  // Emojipedia-style Emoji Lookup.
  //   Header: title + result count + close (drag to move).
  //   Toolbar: live search by name / keyword / codepoint.
  //   Body: colored emoji grid, grouped by CLDR group (browse) or as search
  //   results, each cell showing the glyph + CLDR short name.
  // Clicking an emoji jumps the main BabelMap grid to its first codepoint.

  interface EmojiRec {
    codepoints: number[];
    string: string;
    status: string;
    version: string;
    name: string;
    group: string;
    subgroup: string;
  }

  interface Props {
    show: boolean;
    onClose: () => void;
    onGotoCP: (cp: number) => void;
  }
  let { show, onClose, onGotoCP }: Props = $props();

  const API = "http://127.0.0.1:18080/api";
  let q = $state("");
  let results = $state<EmojiRec[]>([]);
  let browse = $state<EmojiRec[]>([]);
  let loading = $state(false);
  let loaded = $state(false);
  let _timer: ReturnType<typeof setTimeout> | undefined;

  // ── Drag / position ──
  let x = $state(120);
  let y = $state(70);
  let w = $state(Math.min(980, (typeof window !== "undefined" ? window.innerWidth : 980) - 24));
  let h = $state(Math.min(680, (typeof window !== "undefined" ? window.innerHeight : 680) - 40));
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

  // ── Resize ──
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
    w = Math.max(480, winStartW + (e.clientX - resizeStartX));
    h = Math.max(300, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  // ── initial browse load ──
  $effect(() => {
    if (show && !loaded) loadBrowse();
  });
  async function loadBrowse() {
    loading = true;
    try {
      const r = await fetch(API + "/emoji/list");
      if (r.ok) {
        const d = await r.json();
        browse = d.results ?? [];
        results = browse;
      }
    } catch {
      results = [];
    }
    loaded = true;
    loading = false;
  }

  // ── live (debounced) search ──
  function onInput(e: Event) {
    const v = (e.target as HTMLInputElement).value;
    q = v;
    clearTimeout(_timer);
    _timer = setTimeout(() => doSearch(v), 180);
  }
  async function doSearch(v: string) {
    if (!v.trim()) {
      results = browse;
      return;
    }
    loading = true;
    try {
      const r = await fetch(API + "/emoji/search?q=" + encodeURIComponent(v.trim()) + "&limit=120");
      if (r.ok) {
        const d = await r.json();
        results = d.results ?? [];
      }
    } catch {
      results = [];
    }
    loading = false;
  }

  // ── grouping ──
  const grouped = $derived(groupResults(results));
  function groupResults(list: EmojiRec[]): [string, EmojiRec[]][] {
    const m = new Map<string, EmojiRec[]>();
    for (const e of list) {
      if (!m.has(e.group)) m.set(e.group, []);
      m.get(e.group)!.push(e);
    }
    return [...m.entries()];
  }

  function goto(e: EmojiRec) {
    onGotoCP(e.codepoints[0]);
  }
  function cpLabel(e: EmojiRec): string {
    return e.codepoints.map((c) => "U+" + c.toString(16).toUpperCase().padStart(4, "0")).join(" ");
  }

  // ── keyboard: Enter = close? use Escape ──
  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }
</script>

<svelte:window onkeydown={onKey} />

{#if show}
  <div class="ed" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ed-header" onmousedown={onDragStart}>
      <span class="ed-title">Emoji Lookup</span>
      <span class="ed-count">{q.trim() ? results.length : browse.length} emoji</span>
      <button class="ed-close" onclick={onClose} title="Close">✕</button>
    </div>

    <div class="ed-toolbar">
      <input class="ed-search" value={q} oninput={onInput} placeholder="Search by name, keyword or codepoint — e.g. grinning, heart, flag, 1f600" />
      {#if q.trim()}<button
          class="ed-clear"
          onclick={() => {
            q = "";
            results = browse;
          }}
          title="Clear">✕</button
        >{/if}
    </div>

    <div class="ed-body">
      {#if loading && results.length === 0}
        <div class="ed-empty">Loading emoji…</div>
      {:else if results.length === 0}
        <div class="ed-empty">No matching emoji for “{q}”.</div>
      {:else}
        <div class="ed-scroll">
          {#each grouped as [g, list]}
            <div class="ed-group">
              <div class="ed-group-title">{g}<span class="ed-group-count">{list.length}</span></div>
              <div class="ed-grid">
                {#each list as e}
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <button class="ed-cell" title="{e.name} · {cpLabel(e)} · E{e.version}" onclick={() => goto(e)}>
                    <span class="ed-glyph">{e.string}</span>
                    <span class="ed-name">{e.name}</span>
                    <span class="ed-sub">{e.subgroup} · E{e.version}</span>
                  </button>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ed-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .ed {
    position: fixed;
    z-index: 1200;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--bg3, #3a3b4f);
    border-radius: 8px;
    background: var(--bg2, #232440);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
    overflow: hidden;
    font-size: 13px;
    color: var(--fg, #e4e6f0);
  }
  .ed.dragging {
    user-select: none;
  }
  .ed.resizing {
    user-select: none;
  }
  .ed-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
    z-index: 5;
  }
  .ed-resize::after {
    content: "";
    position: absolute;
    right: 3px;
    bottom: 3px;
    width: 8px;
    height: 8px;
    border-right: 2px solid var(--fg3, #6e7191);
    border-bottom: 2px solid var(--fg3, #6e7191);
    border-bottom-right-radius: 3px;
  }
  .ed-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    background: var(--bg3, #2d2e4a);
    cursor: move;
    flex: none;
  }
  .ed-title {
    font-weight: 600;
    font-size: 13px;
  }
  .ed-count {
    color: var(--fg3, #6e7191);
    font-size: 12px;
    margin-left: auto;
  }
  .ed-close {
    border: none;
    background: transparent;
    color: var(--fg2, #b0b3cc);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 2px 6px;
  }
  .ed-close:hover {
    color: var(--fg, #fff);
  }
  .ed-toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    background: var(--bg2, #232440);
    border-bottom: 1px solid var(--bg3, #3a3b4f);
    flex: none;
  }
  .ed-search {
    flex: 1;
    padding: 6px 10px;
    border: 1px solid var(--bg3, #3a3b4f);
    border-radius: 6px;
    background: var(--bg, #1a1b2e);
    color: var(--fg, #e4e6f0);
    font-size: 13px;
    outline: none;
  }
  .ed-search:focus {
    border-color: #6ea8fe;
  }
  .ed-clear {
    border: none;
    background: var(--bg3, #3a3b4f);
    color: var(--fg2, #b0b3cc);
    border-radius: 50%;
    cursor: pointer;
    width: 22px;
    height: 22px;
    line-height: 1;
  }
  .ed-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .ed-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 6px 10px 14px;
  }
  .ed-empty {
    padding: 30px;
    text-align: center;
    color: var(--fg3, #6e7191);
  }
  .ed-group {
    margin-top: 12px;
  }
  .ed-group-title {
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--fg2, #b0b3cc);
    margin: 4px 2px 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .ed-group-count {
    background: var(--bg3, #3a3b4f);
    color: var(--fg3, #6e7191);
    border-radius: 10px;
    font-size: 11px;
    padding: 0 7px;
  }
  .ed-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 6px;
  }
  .ed-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 8px 6px 6px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: var(--bg, #1a1b2e);
    cursor: pointer;
    text-align: center;
    overflow: hidden;
  }
  .ed-cell:hover {
    border-color: #6ea8fe;
    background: var(--bg3, #2d2e4a);
  }
  .ed-glyph {
    font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Twemoji Mozilla", sans-serif;
    font-size: 30px;
    line-height: 1.25;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ed-name {
    font-size: 11px;
    color: var(--fg, #e4e6f0);
    line-height: 1.25;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }
  .ed-sub {
    font-size: 10px;
    color: var(--fg3, #6e7191);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }
</style>
