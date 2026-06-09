<script lang="ts">
  import { t } from "../i18n.svelte";
  import type { GridPage } from "../types";

  interface Props {
    loading: boolean;
    err: string;
    grid: GridPage | null;
  }

  let { loading, err, grid }: Props = $props();
</script>

<div class="gh">
  <span class="gt">
    {#if loading}{t("general.loading")}{:else if err}{err}{:else if grid}{grid.block_name}{:else}{t("general.ready")}{/if}
  </span>
  {#if grid}
    <span class="gr">U+{grid.block_start.toString(16).toUpperCase().padStart(4, "0")}–U+{grid.block_end.toString(16).toUpperCase().padStart(4, "0")}</span>
    <span class="gc">({grid.block_assigned}/{grid.block_count})</span>
  {/if}
</div>
<div class="ch">
  <span></span>
  {#each Array(16) as _, c}<span>_{c.toString(16).toUpperCase()}</span>{/each}
</div>

<style>
  .gh {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 6px;
    flex-shrink: 0;
  }
  .gt {
    font-size: 14px;
    font-weight: 700;
    color: var(--fg);
  }
  .gr {
    font-family: monospace;
    font-size: 11px;
    color: var(--ac);
  }
  .gc {
    font-size: 11px;
    color: var(--fg3);
  }
  .ch {
    display: grid;
    grid-template-columns: 64px repeat(16, 1fr);
    flex-shrink: 0;
    border-bottom: 1px solid var(--bd);
  }
  .ch span {
    text-align: center;
    font-size: 13px;
    font-family: monospace;
    color: var(--fg3);
    padding: 2px 0;
  }
</style>
