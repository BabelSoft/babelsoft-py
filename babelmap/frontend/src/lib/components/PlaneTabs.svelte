<script lang="ts">
  import { get } from "svelte/store";
  import * as store from "../stores";

  interface Props {
    onPlaneChange: () => void;
  }

  let { onPlaneChange }: Props = $props();

  const planeTabs = [
    { plane: 0, label: "BMP", name: "Basic Multilingual Plane" },
    { plane: 1, label: "SMP", name: "Supplementary Multilingual Plane" },
    { plane: 2, label: "SIP", name: "Supplementary Ideographic Plane" },
    { plane: 3, label: "TIP", name: "Tertiary Ideographic Plane" },
    { plane: 14, label: "SSP", name: "Supplementary Special-purpose Plane" },
    { plane: 15, label: "PUA-A", name: "Private Use Area A" },
    { plane: 16, label: "PUA-B", name: "Private Use Area B" },
  ];

  function switchPlane(plane: number) {
    store.currentPlane.set(plane);
    store.scrollPosition.set(0);
    store.selectedCell.set(null);
    onPlaneChange();
  }

  let tooltip = $state<{ text: string; x: number; y: number } | null>(null);
</script>

<div class="plane-tabs">
  {#each planeTabs as tab}
    <button
      class="plane-tab"
      class:active={get(store.currentPlane) === tab.plane}
      onclick={() => switchPlane(tab.plane)}
      onmouseenter={(e) => {
        const rect = (e.target as HTMLElement).getBoundingClientRect();
        tooltip = { text: tab.name, x: rect.left + rect.width / 2, y: rect.bottom + 4 };
      }}
      onmouseleave={() => (tooltip = null)}
      title={tab.name}
    >
      {tab.label}
    </button>
  {/each}
</div>

{#if tooltip}
  <div class="tooltip" style="left:{tooltip.x}px;top:{tooltip.y}px;transform:translateX(-50%)">
    {tooltip.text}
  </div>
{/if}

<style>
  .plane-tabs {
    display: flex;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 0 4px;
    gap: 1px;
    flex-shrink: 0;
  }
  .plane-tab {
    border: none;
    background: transparent;
    color: var(--text-secondary);
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    cursor: pointer;
  }
  .plane-tab:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }
  .plane-tab.active {
    color: var(--text-primary);
    border-bottom-color: var(--accent);
    background: var(--bg-tertiary);
  }
</style>
