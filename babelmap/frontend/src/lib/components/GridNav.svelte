<script lang="ts">
  import { get } from "svelte/store";
  import * as store from "../stores";
  import { navigateDirection } from "../api";

  interface Props {
    onRefresh: () => void;
  }

  let { onRefresh }: Props = $props();

  async function navigate(dir: string) {
    try {
      const page = await navigateDirection(get(store.currentPlane), get(store.scrollPosition), dir, get(store.fontFamily), get(store.fontSize));
      store.gridPage.set(page);
      store.scrollPosition.set(page.scroll_position);
      store.selectedCell.set(null);
    } catch (e: any) {
      store.statusMessage.set(`Navigation error: ${e.message}`);
    }
  }

  function handleScroll(e: Event) {
    const target = e.target as HTMLInputElement;
    store.scrollPosition.set(parseInt(target.value));
    onRefresh();
  }

  const maxScroll = $derived(get(store.gridPage)?.max_scroll ?? 256);
</script>

<aside class="grid-nav">
  <div class="nav-buttons">
    <button onclick={() => navigate("plane_start")} title="Start of Plane">|&lt;</button>
    <button onclick={() => navigate("plane_end")} title="End of Plane">&gt;|</button>
  </div>
  <div class="nav-buttons">
    <button onclick={() => navigate("block_prev")} title="Previous Block">&lt;&lt;</button>
    <button onclick={() => navigate("block_next")} title="Next Block">&gt;&gt;</button>
  </div>
  <div class="nav-buttons">
    <button onclick={() => navigate("page_prev")} title="Page Up">^</button>
    <button onclick={() => navigate("page_next")} title="Page Down">v</button>
  </div>
  <div class="nav-buttons">
    <button onclick={() => navigate("radical_prev")} title="Previous Radical">&lt;</button>
    <button onclick={() => navigate("radical_next")} title="Next Radical">&gt;</button>
  </div>

  <div class="scroll-section">
    <input type="range" class="vertical-slider" min="0" max={maxScroll} value={get(store.scrollPosition)} oninput={handleScroll} style="writing-mode:vertical-lr" title="Scroll position" />
    <span class="scroll-pos">
      {get(store.scrollPosition).toString(16).toUpperCase().padStart(4, "0")}
    </span>
  </div>

  <!-- GoTo Codepoint -->
  <form
    class="goto-block"
    onsubmit={(e) => {
      e.preventDefault();
      const input = (e.target as HTMLFormElement).querySelector("input") as HTMLInputElement;
      const v = input.value.trim();
      if (!v) return;
      let cp = parseInt(v.replace(/^(0x|0X|U\+|u\+|\$)/, ""), 16);
      if (isNaN(cp)) cp = parseInt(v, 10);
      if (isNaN(cp)) return;
      // Navigate via parent
      store.scrollPosition.set(Math.floor((cp % 0x10000) / 16));
      onRefresh();
      input.value = "";
    }}
  >
    <input type="text" placeholder="U+4E2D" class="goto-input" />
    <button type="submit" class="goto-btn">Go</button>
  </form>
</aside>

<style>
  .grid-nav {
    width: 60px;
    min-width: 60px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 4px;
    gap: 6px;
    overflow-y: auto;
  }

  .nav-buttons {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
  }
  .nav-buttons button {
    padding: 4px;
    font-size: 12px;
    border-radius: 2px;
  }

  .scroll-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 8px 0;
  }

  .vertical-slider {
    writing-mode: bt-lr;
    direction: rtl;
    appearance: slider-vertical;
    height: 100%;
    width: 20px;
    flex: 1;
  }

  .scroll-pos {
    font-size: 9px;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .goto-block {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
    padding-bottom: 4px;
  }
  .goto-input {
    width: 100%;
    font-size: 10px;
    padding: 2px 4px;
    font-family: var(--font-mono);
  }
  .goto-btn {
    font-size: 10px;
    padding: 2px;
  }
</style>
