<script lang="ts">
  interface Props {
    results: { codepoint: number; name: string }[];
    idx: number;
    query: string;
    progress: number;
    show: boolean;
    loading: boolean;
    onResultClick: (cp: number) => void;
    onClose: () => void;
    onLoadMore: () => void;
  }

  let { results, idx, query, progress, show, loading, onResultClick, onClose, onLoadMore }: Props = $props();

  // ── Scroll-to-bottom → load more ──
  let listEl = $state<HTMLDivElement>();

  function onScroll() {
    if (!listEl) return;
    const { scrollTop, scrollHeight, clientHeight } = listEl;
    if (scrollHeight - scrollTop - clientHeight < 40) {
      onLoadMore();
    }
  }

  // ── Auto-scroll selected into view ──
  $effect(() => {
    void idx;
    if (listEl && idx >= 0) {
      const item = listEl.children[idx] as HTMLElement | undefined;
      item?.scrollIntoView({ block: "nearest" });
    }
  });

  // ── Drag state ──
  let x = $state(100);
  let y = $state(80);
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
  let w = $state(340);
  let h = $state(320);
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
    w = Math.max(200, winStartW + (e.clientX - resizeStartX));
    h = Math.max(120, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }
</script>

{#if show && results.length > 0}
  <div class="srw" style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;" class:dragging class:resizing>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="srw-header" onmousedown={onDragStart}>
      <span class="srw-title">{results.length} results — <code>{query}</code></span>
      <button class="srw-close" onclick={onClose} title="Close">✕</button>
    </div>
    <div class="srw-bar">
      <div class="srw-bar-fill" style="width:{progress}%"></div>
    </div>
    <div class="srw-list" bind:this={listEl} onscroll={onScroll}>
      {#each results as r, i}
        <button class="srw-item" class:active={i === idx} onclick={() => onResultClick(r.codepoint)}>
          <span class="srw-cp"
            >U+{r.codepoint
              .toString(16)
              .toUpperCase()
              .padStart(r.codepoint > 0xffff ? 5 : 4, "0")}</span
          >
          <span class="srw-name">{r.name}</span>
        </button>
      {/each}
      {#if loading}
        <div class="srw-loading">Loading more…</div>
      {/if}
    </div>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="srw-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .srw {
    position: fixed;
    z-index: 200;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 200px;
    min-height: 120px;
    user-select: none;
  }
  .srw.dragging,
  .srw.resizing {
    opacity: 0.92;
    transition: none;
  }
  .srw-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    background: var(--ac);
    color: #fff;
    cursor: grab;
    flex-shrink: 0;
    user-select: none;
  }
  .srw-header:active {
    cursor: grabbing;
  }
  .srw-title {
    font-size: 12px;
    font-weight: 600;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .srw-title code {
    font-weight: 400;
    opacity: 0.85;
    font-family: monospace;
    font-size: 11px;
  }
  .srw-bar {
    height: 4px;
    background: var(--bg3);
    flex-shrink: 0;
  }
  .srw-bar-fill {
    height: 100%;
    background: var(--ac);
    transition: width 0.15s ease;
    border-radius: 0 2px 2px 0;
  }
  .srw-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.8);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 4px;
    border-radius: 4px;
  }
  .srw-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .srw-list {
    overflow-y: auto;
    flex: 1;
    padding: 2px;
  }
  .srw-item {
    display: flex;
    align-items: baseline;
    gap: 10px;
    width: 100%;
    padding: 4px 10px;
    font-size: 12px;
    font-family: inherit;
    text-align: left;
    background: transparent;
    color: var(--fg);
    border: none;
    border-radius: 5px;
    cursor: pointer;
    height: auto;
    line-height: 1.4;
  }
  .srw-item:hover,
  .srw-item.active {
    background: var(--ac);
    color: #fff;
  }
  .srw-cp {
    font-weight: 700;
    font-family: monospace;
    font-size: 11px;
    min-width: 70px;
    flex-shrink: 0;
    color: var(--ac);
  }
  .srw-item:hover .srw-cp,
  .srw-item.active .srw-cp {
    color: rgba(255, 255, 255, 0.85);
  }
  .srw-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .srw-loading {
    padding: 8px;
    text-align: center;
    font-size: 11px;
    color: var(--fg3);
  }
  .srw-resize {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
    background: linear-gradient(135deg, transparent 50%, var(--ac) 50%);
    border-radius: 0 0 8px 0;
  }
</style>
