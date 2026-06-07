<script lang="ts">
  import { statusMessage, planes, currentPlane, fontFamily, fontSize, getSelectedCodepoint } from "../stores";

  let selectedCp = $derived(getSelectedCodepoint());
  let cpDisplay = $derived(
    selectedCp
      ? `U+${selectedCp.toString(16).toUpperCase().padStart(4, "0")}`
      : "",
  );
</script>

<footer class="status-bar">
  <div class="status-left">
    <span class="status-msg">{$statusMessage}</span>
  </div>
  <div class="status-right">
    {#if cpDisplay}
      <span class="status-cp">{cpDisplay}</span>
    {/if}
    <span class="status-plane">{$planes[$currentPlane]?.abbreviation || `Plane ${$currentPlane}`}</span>
    <span class="status-font">{$fontFamily} {$fontSize}px</span>
  </div>
</footer>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    padding: 2px 10px;
    height: 24px;
    flex-shrink: 0;
    font-size: 11px;
  }

  .status-left {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .status-msg {
    color: var(--text-secondary);
  }

  .status-right {
    display: flex;
    gap: 16px;
    align-items: center;
    flex-shrink: 0;
  }

  .status-cp {
    font-family: var(--font-mono);
    color: var(--accent);
    font-weight: 600;
  }

  .status-plane {
    color: var(--text-muted);
  }

  .status-font {
    color: var(--text-muted);
    font-size: 10px;
  }
</style>
