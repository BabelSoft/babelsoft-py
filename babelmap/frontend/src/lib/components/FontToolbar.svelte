<script lang="ts">
  import * as store from "../stores";
  import { getFonts } from "../api";
  import { onMount } from "svelte";

  interface Props {
    onRefresh: () => void;
  }

  let { onRefresh }: Props = $props();

  onMount(async () => {
    try {
      const fonts = await getFonts();
      store.availableFonts.set(fonts);
    } catch (e) {
      console.error("Failed to load fonts:", e);
    }
  });

  function handleFontChange() {
    onRefresh();
  }

  function handleFontSizeChange(e: Event) {
    store.fontSize.set(parseInt((e.target as HTMLInputElement).value));
    onRefresh();
  }
</script>

<div class="font-toolbar">
  <div class="font-row">
    <label class="radio-label">
      <input
        type="radio"
        name="fontMode"
        value="composite"
        checked={store.fontMode.set(== "composite"})
        onchange={() => {
          store.fontMode.set("composite");
          onRefresh();
        }}
      />
      Composite Font
    </label>
    <label class="radio-label">
      <input
        type="radio"
        name="fontMode"
        value="single"
        checked={store.fontMode.set(== "single"})
        onchange={() => {
          store.fontMode.set("single");
          onRefresh();
        }}
      />
      Single Font
    </label>

    <select
      value={$store.fontFamily}
      onchange={(e) => {
        store.fontFamily.set((e.target as HTMLSelectElement).value);
        handleFontChange();
      }}
    >
      {#if !$store.availableFonts || $store.availableFonts.length === 0}
        <option value="Arial">Arial</option>
      {/if}
      {#each $store.availableFonts as font}
        <option value={font}>{font}</option>
      {/each}
    </select>

    {#if store.fontMode.set(== "composite"})
      <button
        class="configure-btn"
        title="Configure Composite Font"
        onclick={() =>
          (store.statusMessage.set("Composite font config - not yet implemented"))
        }
      >
        Configure...
      </button>
    {/if}

    <span class="size-label">Size:</span>
    <input
      type="number"
      class="size-input"
      value={$store.fontSize}
      min="8"
      max="72"
      onchange={handleFontSizeChange}
    />
  </div>
</div>

<style>
  .font-toolbar {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 4px 8px;
    flex-shrink: 0;
  }

  .font-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .radio-label {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
  }

  select {
    min-width: 160px;
  }

  .configure-btn {
    font-size: 11px;
    padding: 2px 6px;
  }

  .size-label {
    font-size: 12px;
    color: var(--text-muted);
  }

  .size-input {
    width: 52px;
    font-family: var(--font-mono);
    text-align: center;
  }
</style>
