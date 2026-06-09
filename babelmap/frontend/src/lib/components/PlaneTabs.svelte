<script lang="ts">
  interface Props {
    plane: number;
    planes: { id: number; l: string }[];
    onChange: (id: number) => void;
  }

  let { plane, planes, onChange }: Props = $props();
</script>

<div class="tabs">
  {#each planes as p}
    <button class:on={plane === p.id} onclick={() => onChange(p.id)}>
      {p.l}
    </button>
  {/each}
</div>

<style>
  .tabs {
    display: flex;
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
