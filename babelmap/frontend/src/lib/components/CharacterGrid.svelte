<script lang="ts">
  import type { GridPage } from "../types";
  interface Props {
    gridPage: GridPage | null;
    onRefresh: () => void;
  }
  let { gridPage, onRefresh }: Props = $props();
</script>

<div class="char-grid">
  {#if gridPage}
    {#each gridPage.cells as row}
      <div class="grid-row">
        {#each row as cell}
          <span class="cell">{cell.codepoint >= 0 ? String.fromCodePoint(cell.codepoint) : ""}</span>
        {/each}
      </div>
    {/each}
  {/if}
</div>
