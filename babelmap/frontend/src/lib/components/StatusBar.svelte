<script lang="ts">
  import { t } from "../i18n.svelte";
  import { coverageStore, scanPct } from "../coverage.svelte";
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

  let {
    statusMsg,
    selInfo,
    grid,
    planeLabel,
    fsize,
    firstRowBase,
    onStatusClear,
  }: Props = $props();

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
  <!-- Font-analysis progress.  The scan is kicked off at app start so it
       overlaps with the user's first interactions, and its progress belongs
       here (unobtrusive) rather than inside the dialog that consumes it. -->
  {#if coverageStore.loading}
    <span class="st-scan" title={coverageStore.scanFile || ""}>
      <span class="st-scan-label">{t("composite.analysing")}</span>
      <span class="st-bar">
        <span class="st-bar-fill" style="width:{scanPct()}%"></span>
      </span>
      <span class="st-scan-num">
        {#if coverageStore.scanTotal > 0}
          {coverageStore.scanDone}/{coverageStore.scanTotal}
        {:else}
          …
        {/if}
      </span>
    </span>
  {/if}
  <span
    >{planeLabel} · Arial {fsize}px · {firstRowBase != null
      ? `U+${firstRowBase.toString(16).toUpperCase().padStart(4, "0")}`
      : ""}</span
  >
</footer>

<style>
  .st {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
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
  .st-scan {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    color: var(--fg3);
    overflow: hidden;
  }
  .st-scan-label {
    white-space: nowrap;
  }
  .st-bar {
    display: inline-block;
    width: 120px;
    height: 4px;
    border-radius: 2px;
    background: var(--bg3);
    overflow: hidden;
    flex-shrink: 0;
  }
  .st-bar-fill {
    display: block;
    height: 100%;
    background: var(--ac);
    transition: width 0.2s;
  }
  .st-scan-num {
    font-family: ui-monospace, Consolas, monospace;
    white-space: nowrap;
  }
</style>
