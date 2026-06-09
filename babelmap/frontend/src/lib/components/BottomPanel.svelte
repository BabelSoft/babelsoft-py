<script lang="ts">
  import { t } from "../i18n.svelte";
  import type { BlockInfo } from "../types";

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
</script>

<div class="bot">
  <div class="br1">
    <fieldset>
      <legend>{t("bottom.select_block")}</legend>
      <select
        value={sblock}
        onchange={(e) => {
          const v = (e.target as HTMLSelectElement).value;
          onSblockChange(v);
          onBlockSelect(v);
        }}
      >
        <option value="">-- {t("bottom.select_block")} --</option>
        {#each blocks as b}
          <option value={b.name}>{b.name}</option>
        {/each}
      </select>
    </fieldset>
    <fieldset class="fs">
      <legend>{t("bottom.search_name")}</legend>
      <input
        type="text"
        value={sv}
        oninput={(e) => onSvChange((e.target as HTMLInputElement).value)}
        onkeydown={(e) => {
          if (e.key === "Enter") onSearch();
        }}
      />
      <button onclick={onSearch}>🔍</button>
    </fieldset>
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
    max-width: 190px;
  }
  .br1 fieldset:first-child select {
    width: 100%;
  }
  .fs {
    flex: 2;
  }
  .fs input {
    flex: 1;
    width: 0;
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
