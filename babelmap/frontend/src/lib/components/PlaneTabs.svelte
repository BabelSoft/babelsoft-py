<script lang="ts">
  interface Props {
    plane: number;
    planes: { id: number; l: string }[];
    onChange: (id: number) => void;
  }

  let { plane, planes, onChange }: Props = $props();
</script>

<div class="tabs">
  {#if planes.length}
    {#each planes as p}
      <button class:on={plane === p.id} onclick={() => onChange(p.id)}>
        {p.l}
      </button>
    {/each}
  {:else}
    <span class="tabs-loading">…</span>
  {/if}
</div>

<style>
  .tabs {
    display: flex;
    flex-wrap: wrap;
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    padding: 0 8px;
    gap: 2px;
    flex-shrink: 0;
  }
  .tabs button {
    cursor: pointer;
    font-family: inherit;
    font-size: 11px;
    font-weight: 700;
    border: none;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
    background: transparent;
    color: var(--fg3);
    padding: 6px 16px;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }
  .tabs-loading {
    color: var(--fg3);
    font-size: 11px;
    padding: 6px 8px;
    letter-spacing: 2px;
    user-select: none;
  }
  .tabs button:hover {
    color: var(--fg);
    background: var(--bg3);
  }
  .tabs button.on {
    color: var(--ac);
    border-bottom-color: var(--ac);
  }
</style>
