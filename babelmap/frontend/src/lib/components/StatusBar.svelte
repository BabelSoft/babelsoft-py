<script lang="ts">
  import { t } from "../i18n.svelte";
  import type { GridPage } from "../types";

  interface Props {
    statusMsg: string;
    selInfo: { hex: string; name: string } | null;
    grid: GridPage | null;
    planeLabel: string;
    fsize: number;
    firstRowBase: number | null;
    onStatusClear: () => void;
  }

  let { statusMsg, selInfo, grid, planeLabel, fsize, firstRowBase, onStatusClear }: Props = $props();

  let _timer: ReturnType<typeof setTimeout> | null = null;
  let displayMsg = $state("");

  $effect(() => {
    const msg = statusMsg;
    if (msg) {
      displayMsg = msg;
      if (_timer) clearTimeout(_timer);
      _timer = setTimeout(() => {
        displayMsg = "";
        onStatusClear();
      }, 2500);
    } else {
      displayMsg = "";
    }
  });
</script>

<footer class="st">
  <span>
    {#if displayMsg}
      <span class="status-msg">{displayMsg}</span>
    {:else if selInfo}
      U+{selInfo.hex} – {selInfo.name}
    {:else if grid}
      {grid.block_name}
    {:else}
      {t("general.ready")}
    {/if}
  </span>
  <span>{planeLabel} · Arial {fsize}px · {firstRowBase != null ? `U+${firstRowBase.toString(16).toUpperCase().padStart(4, "0")}` : ""}</span>
</footer>

<style>
  .st {
    display: flex;
    justify-content: space-between;
    padding: 3px 14px;
    background: var(--bg2);
    border-top: 1px solid var(--bd);
    font-size: 11px;
    color: var(--fg3);
    flex-shrink: 0;
  }
  .status-msg {
    color: var(--ac);
    font-weight: 600;
  }
</style>
