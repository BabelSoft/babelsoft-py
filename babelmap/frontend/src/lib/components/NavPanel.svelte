<script lang="ts">
  import { t } from "../i18n.svelte";

  interface Props {
    maxScroll: number;
    scroll: number;
    onScrollInput: (val: number) => void;
    onPlaneStart: () => void;
    onPlaneEnd: () => void;
    onPrevBlock: () => void;
    onNextBlock: () => void;
    onPageUp: () => void;
    onPageDown: () => void;
    onRowStart: () => void;
    onRowEnd: () => void;
    onRandom: () => void;
  }

  let { maxScroll, scroll, onScrollInput, onPlaneStart, onPlaneEnd, onPrevBlock, onNextBlock, onPageUp, onPageDown, onRowStart, onRowEnd, onRandom }: Props = $props();
</script>

<aside class="rn">
  <div class="vs">
    <input
      type="range"
      {...{ orient: "vertical" }}
      min="0"
      max={maxScroll}
      value={scroll}
      oninput={(e) => {
        onScrollInput(parseInt((e.target as HTMLInputElement).value) || 0);
      }}
    />
  </div>
  <div class="nb">
    <button onclick={onPlaneStart} title={t("nav.plane_start")}>⏮️</button>
    <button onclick={onPlaneEnd} title={t("nav.plane_end")}>⏭️</button>
    <button onclick={onPrevBlock} title={t("nav.prev_block")}>⏪</button>
    <button onclick={onNextBlock} title={t("nav.next_block")}>⏩</button>
    <button onclick={onPageUp} title={t("nav.page_up")}>⬆️</button>
    <button onclick={onPageDown} title={t("nav.page_down")}>⬇️</button>
    <button onclick={onRowStart} title={t("nav.row_start")}>⤒</button>
    <button onclick={onRowEnd} title={t("nav.row_end")}>⤓</button>
    <button title={t("nav.ivs")} disabled>〰️</button>
    <button onclick={onRandom} title={t("nav.random")}>🎲</button>
  </div>
</aside>

<style>
  .rn {
    display: flex;
    flex-direction: row;
    gap: 0;
    background: var(--bg2);
    border-left: 1px solid var(--bd);
    flex-shrink: 0;
  }
  .vs {
    width: 28px;
    display: flex;
    align-items: stretch;
    justify-content: center;
    padding: 4px 0;
  }
  .vs input {
    writing-mode: vertical-lr;
    width: auto;
    accent-color: var(--ac);
  }
  .nb {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 2px;
    width: 36px;
  }
  .nb button {
    width: 100%;
    height: 28px;
    font-size: 14px;
    background: var(--bg3);
    color: var(--fg2);
    border: 1px solid var(--bd);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .nb button:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .nb button:disabled {
    opacity: 0.3;
    cursor: default;
  }
  .nb button:disabled:hover {
    background: var(--bg3);
    color: var(--fg2);
    border-color: var(--bd);
  }
</style>
