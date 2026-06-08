<script lang="ts">
  import { get } from "svelte/store";
  import * as store from "../stores";
  import { searchByName, jumpToBlock, convertEditBuffer, jumpToCodepoint } from "../api";
  import type { BlockInfo } from "../types";

  interface Props {
    onRefresh: () => void;
  }

  let { onRefresh }: Props = $props();

  let searchQuery = $state("");
  let searchResults = $state<string[]>([]);
  let selectedBlock = $state("");
  let gotoValue = $state("");
  let editBufferVisible = $state(true);

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    try {
      const results = await searchByName(searchQuery.trim());
      searchResults = results.map((c) => `U+${c.codepoint.toString(16).toUpperCase().padStart(4, "0")} - ${c.name}`);
    } catch (e: any) {
      store.statusMessage.set(`Search error: ${e.message}`);
    }
  }

  async function handleBlockSelect() {
    if (!selectedBlock) return;
    try {
      const page = await jumpToBlock(get(store.currentPlane), selectedBlock);
      store.gridPage.set(page);
      store.scrollPosition.set(page.scroll_position);
      onRefresh();
    } catch (e: any) {
      store.statusMessage.set(`Block jump: ${e.message}`);
    }
  }

  async function handleGoto() {
    if (!gotoValue.trim()) return;
    const v = gotoValue.trim();
    let cp = parseInt(v.replace(/^(0x|0X|U\+|u\+|\$)/, ""), 16);
    if (isNaN(cp)) cp = parseInt(v, 10);
    if (isNaN(cp)) return;
    try {
      const page = await jumpToCodepoint(get(store.currentPlane), cp);
      store.gridPage.set(page);
      store.scrollPosition.set(page.scroll_position);
      onRefresh();
      gotoValue = "";
    } catch (e: any) {
      store.statusMessage.set(`Go to: ${e.message}`);
    }
  }

  function handleEditBufferKeydown(e: KeyboardEvent) {
    if (e.ctrlKey && e.key === "a") {
      e.preventDefault();
      (e.target as HTMLTextAreaElement).select();
    }
  }

  async function handleModeChange(mode: string) {
    store.editBufferMode.set(mode as any);
    const buf = get(store.editBuffer);
    if (buf) {
      try {
        const { result } = await convertEditBuffer(buf, mode);
        store.editBuffer.set(result);
      } catch {
        // fallback: just change mode
      }
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(get(store.editBuffer));
      store.statusMessage.set("Copied to clipboard");
    } catch {
      store.statusMessage.set("Copy failed");
    }
  }

  function handleClear() {
    store.editBuffer.set("");
    store.statusMessage.set("Edit buffer cleared");
  }

  function handleCut() {
    handleCopy();
    store.editBuffer.set("");
    store.statusMessage.set("Cut to clipboard");
  }
</script>

<div class="bottom-panel">
  <!-- Row 1: Select Block / Search / GoTo -->
  <div class="controls-row">
    <!-- Select Block -->
    <div class="control-group">
      <label for="select-block">Select Block:</label>
      <select id="select-block" bind:value={selectedBlock} onchange={handleBlockSelect}>
        <option value="">-- Select Block --</option>
        {#each get(store.blocks).filter((b) => b.plane === get(store.currentPlane)) as block}
          <option value={block.name}>
            {block.name} ({block.count} chars)
          </option>
        {/each}
      </select>
    </div>

    <!-- Search by Name -->
    <div class="control-group">
      <label for="search-name">Search by Name:</label>
      <div class="search-row">
        <input
          id="search-name"
          type="text"
          bind:value={searchQuery}
          onkeydown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
        />
        <button onclick={handleSearch}>Search</button>
      </div>
    </div>

    <!-- GoTo -->
    <div class="control-group">
      <label for="goto-input">Goto Codepoint:</label>
      <div class="goto-row">
        <input
          id="goto-input"
          type="text"
          bind:value={gotoValue}
          placeholder="hex or dec"
          onkeydown={(e) => {
            if (e.key === "Enter") handleGoto();
          }}
        />
        <button onclick={handleGoto}>Go</button>
      </div>
    </div>
  </div>

  <!-- Row 2: Edit Buffer -->
  <div class="edit-buffer-section">
    <div class="edit-header">
      <span class="edit-title">Edit Buffer</span>
      <div class="edit-controls">
        <!-- Mode radios -->
        <label class="radio-small">
          <input type="radio" name="bufferMode" value="char" checked={get(store.editBufferMode) === "char"} onchange={() => handleModeChange("char")} />
          Char
        </label>
        <label class="radio-small">
          <input type="radio" name="bufferMode" value="ncr_hex" checked={get(store.editBufferMode) === "ncr_hex"} onchange={() => handleModeChange("ncr_hex")} />
          NCR&nbsp;hex
        </label>
        <label class="radio-small">
          <input type="radio" name="bufferMode" value="ncr_dec" checked={get(store.editBufferMode) === "ncr_dec"} onchange={() => handleModeChange("ncr_dec")} />
          NCR&nbsp;dec
        </label>
        <label class="radio-small">
          <input type="radio" name="bufferMode" value="html" checked={get(store.editBufferMode) === "html"} onchange={() => handleModeChange("html")} />
          HTML
        </label>
        <label class="radio-small">
          <input type="radio" name="bufferMode" value="ucn" checked={get(store.editBufferMode) === "ucn"} onchange={() => handleModeChange("ucn")} />
          UCN
        </label>
        <span class="sep">|</span>
        <label class="radio-small">
          <input type="radio" name="renderMode" value="glyph" checked={get(store.renderMode) === "glyph"} onchange={() => store.renderMode.set("glyph")} />
          Glyph
        </label>
        <label class="radio-small">
          <input type="radio" name="renderMode" value="text" checked={get(store.renderMode) === "text"} onchange={() => store.renderMode.set("text")} />
          Text
        </label>
        <span class="sep">|</span>
        <button onclick={handleClear}>Clear</button>
        <button onclick={handleCopy}>Copy</button>
        <button onclick={handleCut}>Cut</button>
      </div>
    </div>
    <textarea
      class="edit-textarea"
      value={get(store.editBuffer)}
      oninput={(e) => store.editBuffer.set((e.target as HTMLTextAreaElement).value)}
      rows={4}
      onkeydown={handleEditBufferKeydown}
      spellcheck={false}
    ></textarea>
  </div>

  <!-- Search Results -->
  {#if searchResults.length > 0}
    <div class="search-results">
      <div class="results-header">
        Search results ({searchResults.length})
        <button onclick={() => (searchResults = [])}>�?/button> </button>
      </div>
      <div class="results-list">
        {#each searchResults as r}
          <div class="result-item">{r}</div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .bottom-panel {
    background: var(--bg-secondary);
    border-top: 2px solid var(--border-color);
    flex-shrink: 0;
    max-height: 300px;
    overflow-y: auto;
  }

  .controls-row {
    display: flex;
    gap: 12px;
    padding: 6px 10px;
    flex-wrap: wrap;
    border-bottom: 1px solid var(--border-color);
  }

  .control-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .control-group label {
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
  }
  .control-group select {
    min-width: 200px;
  }
  .control-group input[type="text"] {
    width: 140px;
    font-family: var(--font-mono);
  }

  .search-row,
  .goto-row {
    display: flex;
    gap: 4px;
  }

  .edit-buffer-section {
    padding: 4px 10px 6px;
  }

  .edit-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    flex-wrap: wrap;
  }
  .edit-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }
  .edit-controls {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .radio-small {
    display: flex;
    align-items: center;
    gap: 1px;
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .sep {
    color: var(--border-color);
    font-size: 14px;
  }

  .edit-textarea {
    width: 100%;
    background: var(--bg-primary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 6px 8px;
    font-family: var(--font-mono);
    font-size: 13px;
    resize: vertical;
    min-height: 60px;
  }
  .edit-textarea:focus {
    outline: none;
    border-color: var(--accent);
  }

  .search-results {
    border-top: 1px solid var(--border-color);
    max-height: 120px;
    overflow-y: auto;
  }
  .results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 10px;
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    position: sticky;
    top: 0;
  }
  .results-header button {
    font-size: 10px;
    padding: 0 4px;
  }
  .results-list {
    padding: 4px 0;
  }
  .result-item {
    padding: 3px 12px;
    font-size: 12px;
    font-family: var(--font-mono);
    cursor: pointer;
    color: var(--text-secondary);
  }
  .result-item:hover {
    background: var(--accent);
    color: var(--text-primary);
  }
</style>
