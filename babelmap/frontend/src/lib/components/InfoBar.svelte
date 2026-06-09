<script lang="ts">
  import { t } from "../i18n.svelte";

  interface Props {
    selInfo: { hex: string; char: string; dec: string; name: string } | null;
  }

  let { selInfo }: Props = $props();
</script>

<div class="ir">
  <input
    class="ir1"
    readonly
    value={selInfo ? `U+${selInfo.hex} ${selInfo.char} ${selInfo.name}` : ""}
    placeholder={t("general.select_char")}
    onclick={(e) => {
      const t = e.target as HTMLInputElement;
      if (t.value) {
        navigator.clipboard.writeText(t.value);
      }
    }}
  />
  <input class="ir2" readonly value={selInfo?.dec || ""} />
</div>

<style>
  .ir {
    display: flex;
    gap: 6px;
    padding: 4px 10px;
    background: var(--bg2);
    border-top: 1px solid var(--bd);
    flex-shrink: 0;
  }
  .ir1 {
    flex: 1;
    font-family: monospace;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 4px 8px;
    outline: none;
    cursor: text;
  }
  .ir2 {
    width: 80px;
    text-align: center;
    font-family: monospace;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 4px 8px;
    outline: none;
    cursor: text;
  }
</style>
