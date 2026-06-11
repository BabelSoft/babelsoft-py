<script lang="ts">
  import { t } from "../i18n.svelte";
  import type { BlockInfo } from "../types";
  import AdvSearch from "./AdvSearch.svelte";

  interface Props {
    buf: string;
    mode: string;
    glyph: boolean;
    colour: boolean;
    fsize: number;
    gv: string;
    sv: string;
    blocks: BlockInfo[];
    sblock: string;
    editVisible: boolean;
    onBufChange: (v: string) => void;
    onSblockChange: (v: string) => void;
    onGvChange: (v: string) => void;
    onSvChange: (v: string) => void;
    onBlockSelect: (name: string) => void;
    onSearch: () => void;
    onSearchPrev: () => void;
    onSearchNext: () => void;
    onGoto: () => void;
    onFontSizeChange: (size: number) => void;
    onModeChange: (m: string) => void;
    onGlyphToggle: (v: boolean) => void;
    onColourToggle: (v: boolean) => void;
    onCopy: () => void;
    onCut: () => void;
    onClear: () => void;
    onSave: () => void;
    onHideToggle: () => void;
    onContextMenu: (e: MouseEvent) => void;
  }

  let {
    buf,
    mode,
    glyph,
    colour,
    fsize,
    gv,
    sv,
    blocks,
    sblock,
    editVisible,
    onBufChange,
    onSblockChange,
    onGvChange,
    onSvChange,
    onBlockSelect,
    onSearch,
    onSearchPrev,
    onSearchNext,
    onGoto,
    onFontSizeChange,
    onModeChange,
    onGlyphToggle,
    onColourToggle,
    onCopy,
    onCut,
    onClear,
    onSave,
    onHideToggle,
    onContextMenu,
  }: Props = $props();

  let open = $state(false);
  let ddEl = $state<HTMLElement>();

  function toggleOpen() {
    open = !open;
  }
  function pick(name: string) {
    onSblockChange(name);
    onBlockSelect(name);
    open = false;
  }
  function onBlur() {
    // timeout lets the option click register before close
    setTimeout(() => {
      open = false;
    }, 150);
  }
</script>

<div class="bot">
  <div class="br1">
    <fieldset class="block-sel-fs">
      <legend>{t("bottom.select_block")}</legend>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="block-sel-wrap"
        onkeydown={(e) => {
          if (e.key === "Escape") open = false;
        }}
      >
        <!-- trigger -->
        <button class="block-sel-trig" onclick={toggleOpen} onblur={onBlur}>
          <span class="block-sel-label">{sblock || t("bottom.select_block")}</span>
          <span class="block-sel-arrow" class:open>▾</span>
        </button>
        <!-- dropdown -->
        {#if open}
          <div class="block-sel-dd" bind:this={ddEl}>
            {#each blocks as b}
              <button class="block-sel-opt" class:active={b.name === sblock} onclick={() => pick(b.name)} title={b.name}>
                {b.name}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </fieldset>
    <AdvSearch {sv} {onSvChange} {onSearch} {onSearchPrev} {onSearchNext} />
    <fieldset class="fg">
      <legend>{t("bottom.goto_cp")}</legend>
      <input
        type="text"
        value={gv}
        placeholder={t("general.hex")}
        oninput={(e) => onGvChange((e.target as HTMLInputElement).value)}
        onkeydown={(e) => {
          if (e.key === "Enter") onGoto();
        }}
      />
      <button onclick={onGoto}>{t("bottom.go")}</button>
    </fieldset>
  </div>
  <div class="br2">
    <label class="rd"><input type="radio" name="fm" checked /> {t("font.composite_font")}</label>
    <button class="sb">{t("font.configure")}</button>
    <label class="rd"><input type="radio" name="fm" /> {t("font.single_font")}</label>
    <select class="fsel"><option>Arial</option></select>
    <input type="number" class="fsz" value={fsize} min="8" max="72" onchange={(e) => onFontSizeChange(parseInt((e.target as HTMLInputElement).value) || 16)} />
    <button class="sb" style="margin-left:auto">{t("font.show")}</button>
  </div>
  <fieldset class="eb">
    <legend>{t("bottom.edit_buffer")}</legend>
    <textarea
      value={buf}
      oninput={(e) => onBufChange((e.target as HTMLTextAreaElement).value)}
      rows={3}
      spellcheck={false}
      placeholder="Click cells to add. Arrow keys navigate. Enter to add selected."
      oncontextmenu={(e) => onContextMenu(e)}
    ></textarea>
    <div class="ebc">
      <div class="ebr">
        <label class="rd">
          <input type="radio" name="rdr" checked={glyph} onchange={() => onGlyphToggle(true)} />
          {t("bottom.glyph")}
        </label>
        <label class="rd">
          <input type="radio" name="rdr" checked={!glyph} onchange={() => onGlyphToggle(false)} />
          {t("bottom.text")}
        </label>
        <label class="ck">
          <input type="checkbox" checked={colour} onchange={(e) => onColourToggle((e.target as HTMLInputElement).checked)} />
          {t("bottom.colour")}
        </label>
      </div>
      <div class="ebr">
        {#each [{ l: t("edit.char"), v: "char" }, { l: t("edit.ncr_hex"), v: "ncr_hex" }, { l: t("edit.ncr_dec"), v: "ncr_dec" }, { l: t("edit.html"), v: "html" }, { l: t("edit.ucn"), v: "ucn" }] as m}
          <label class="rd">
            <input type="radio" name="em" value={m.v} checked={mode === m.v} onchange={() => onModeChange(m.v)} />
            {m.l}
          </label>
        {/each}
      </div>
      <div class="ebr ebtns">
        <button class="sb" onclick={onHideToggle}>{t("bottom.hide")}</button>
        <button class="sb" onclick={onSave}>{t("bottom.save")}</button>
        <button class="sb" onclick={onClear}>{t("bottom.clear")}</button>
        <button class="sb" onclick={onCopy}>{t("bottom.copy")}</button>
        <button class="sb" onclick={onCut}>{t("bottom.cut")}</button>
      </div>
    </div>
  </fieldset>
</div>

<style>
  .bot {
    flex-shrink: 0;
    background: var(--bg2);
    border-top: 2px solid var(--bd);
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.04);
  }
  .br1 {
    display: flex;
    gap: 8px;
  }
  .br1 fieldset:first-child {
    max-width: 200px;
    min-width: 155px;
  }

  /* ── Custom dropdown ── */
  .block-sel-wrap {
    position: relative;
    width: 100%;
  }
  .block-sel-trig {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 7px 10px 7px 12px;
    font-size: 12px;
    font-weight: 500;
    font-family: inherit;
    background: var(--bg2);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    cursor: pointer;
    transition:
      border-color 0.15s,
      background 0.15s,
      box-shadow 0.15s;
    line-height: 1.4;
    text-align: left;
  }
  .block-sel-trig:hover {
    border-color: var(--ac);
    background: var(--bg);
  }
  .block-sel-trig:focus {
    outline: none;
    border-color: var(--ac);
    box-shadow: 0 0 0 3px rgba(92, 124, 250, 0.18);
  }
  .block-sel-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .block-sel-arrow {
    flex-shrink: 0;
    font-size: 13px;
    color: var(--fg3);
    transition:
      transform 0.2s,
      color 0.15s;
    line-height: 1;
  }
  .block-sel-arrow.open {
    transform: rotate(180deg);
    color: var(--ac);
  }

  /* dropdown menu */
  .block-sel-dd {
    position: absolute;
    bottom: calc(100% + 4px);
    left: 0;
    min-width: 100%;
    width: max-content;
    max-width: 320px;
    max-height: 60vh;
    overflow-y: auto;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 10px;
    box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.12);
    z-index: 100;
    padding: 4px;
  }
  .block-sel-dd .block-sel-opt {
    display: block;
    width: 100%;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 400;
    font-family: inherit;
    text-align: left;
    background: transparent;
    color: var(--fg);
    border: none;
    border-radius: 6px;
    cursor: pointer;
    height: auto;
    white-space: nowrap;
  }
  .block-sel-dd .block-sel-opt:hover {
    background: var(--ac);
    color: #fff;
  }
  .block-sel-dd .block-sel-opt.active {
    background: var(--bg3);
    font-weight: 600;
    color: var(--ac);
  }
  .block-sel-dd .block-sel-opt.active:hover {
    background: var(--ac);
    color: #fff;
  }
  .fg {
    flex: 0 0 auto;
    min-width: 130px;
  }
  .fg input {
    width: 70px;
    font-family: monospace;
  }
  .br1 button,
  .sb {
    height: 26px;
    padding: 0 10px;
    font-size: 11px;
    font-weight: 600;
    background: var(--bg3);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .br1 button:hover,
  .sb:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .br2 {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .rd {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg);
    cursor: pointer;
    font-weight: 500;
  }
  .rd input {
    accent-color: var(--ac);
  }
  .ck {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg);
    cursor: pointer;
  }
  .ck input {
    accent-color: var(--ac);
  }
  .fsel {
    width: 140px;
  }
  .fsz {
    width: 50px;
    text-align: center;
    font-family: monospace;
    background: var(--bg) !important;
  }
  .eb textarea {
    width: 100%;
    flex: 1;
    resize: none;
    font-family: monospace;
    font-size: 12px;
    min-height: 52px;
    line-height: 1.5;
  }
  .ebc {
    margin-top: 3px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .ebr {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .ebtns {
    padding-top: 4px;
    border-top: 1px solid var(--bd);
  }
</style>
