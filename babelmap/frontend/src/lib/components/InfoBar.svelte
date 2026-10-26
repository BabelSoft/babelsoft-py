<script lang="ts">
  import { t } from "../i18n.svelte";

  interface Props {
    selInfo: {
      hex: string;
      char: string;
      /** Options ▸ Alternative Representation of the code point. */
      alt: string;
      /** Full description: name + source refs + readings (Options ▸ Status Bar). */
      name: string;
    } | null;
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
  <input
    class="ir2"
    readonly
    value={selInfo?.alt || ""}
    title={t("options.alt_repr")}
    onclick={() => {
      if (selInfo?.alt) navigator.clipboard.writeText(selInfo.alt);
    }}
  />
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
    width: 150px;
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
