<script lang="ts">
  import Icon from "../icons/Icon.svelte";
  import { t } from "../i18n.svelte";
  import type { BlockInfo } from "../types";
  import { settings } from "../settings.svelte";
  import { getFonts } from "../api";
  import AdvSearch from "./AdvSearch.svelte";
  import SearchResultsWindow from "./SearchResultsWindow.svelte";
  import GlyphText from "./GlyphText.svelte";

  interface Props {
    buf: string;
    mode: string;
    glyph: boolean;
    colour: boolean;
    /** Font stack shared with the character grid (from CompositeFontDialog). */
    stackFamily?: string;
    /** Edit-buffer font size in px — independent of the grid size. */
    /** Edit-buffer font size in px, or `null` for the original CSS sizing. */
    bufSize?: number | null;
    onBufSizeChange?: (n: number) => void;
    onConfigureStack?: () => void;
    gv: string;
    sv: string;
    /** Options ▸ Go To Code Points ▸ Hexadecimal / Decimal. */
    gotoHex?: boolean;
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
    searchResults: { codepoint: number; name: string }[];
    searchIdx: number;
    searchQuery: string;
    searchProgress: number;
    showResults: boolean;
    searchLoading: boolean;
    onSearchResultClick: (cp: number) => void;
    onCloseResults: () => void;
    onLoadMoreResults: () => void;
    onGoto: () => void;
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
    stackFamily = "",
    bufSize = null,
    onBufSizeChange = () => {},
    onConfigureStack = () => {},
    gv,
    sv,
    gotoHex = true,
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
    searchResults,
    searchIdx,
    searchQuery,
    searchProgress,
    showResults,
    searchLoading,
    onSearchResultClick,
    onCloseResults,
    onLoadMoreResults,
    onGoto,
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

  // ── Edit-buffer rendering (Edit ▸ Glyph/Text Mode and Colour Glyphs) ──
  // In the original, `CUniscribeEdit::SetSimpleMode()` switches between
  // `DrawSimple` (each character drawn with the font mapped to its block) and
  // `DrawComplex` (one shaping engine over the whole text), and
  // `SetColourMode()` decides whether `OutputGlyph` uses the font's built-in
  // colour glyph (`bColour && IsColourFont() && IsColourGlyph()`).  Neither
  // touches `m_nFontSize`, so the size here is pinned once and the toggles only
  // change the family and the colour-glyph preference.
  const BUF_PX = 12;
  const bufStyle = $derived(
    [
      `font-size: ${bufSize ?? BUF_PX}px`,
      "line-height: 1.5",
      // Glyph mode draws with the mapped stack; text mode with a plain text font.
      `font-family: ${
        glyph
          ? stackFamily || settings.singleFamily || "serif"
          : "ui-monospace, monospace"
      }`,
      // Colour Glyphs: prefer the font's colour glyphs (the web equivalent of
      // IsColourFont/IsColourGlyph); off forces the monochrome forms.
      `font-variant-emoji: ${colour ? "emoji" : "text"}`,
    ].join("; "),
  );

  // Font families for the single-font selector.  Loaded lazily — only when
  // single-font mode is actually used, so the default (composite) path never
  // pays for the request.
  let families = $state<string[]>([]);

  // ── Glyph Mode caret mirroring ────────────────────────────────────
  // The canvas draws each glyph in its own forced-width cell, so the browser's
  // caret (which follows the *shaped* text) would sit in the wrong place.  We
  // hide the native one and draw ours, which means tracking the textarea's
  // selection, scroll offset and text colour.
  let ebEl = $state<HTMLTextAreaElement | null>(null);
  let caretPos = $state(0);
  let selStart = $state(0);
  let selEnd = $state(0);
  let scrollTop = $state(0);
  let ebColour = $state("#000000");
  let ebBg = $state("#ffffff");

  function syncSel() {
    const el = ebEl;
    if (!el) return;
    caretPos = el.selectionStart ?? 0;
    selStart = el.selectionStart ?? 0;
    selEnd = el.selectionEnd ?? selStart;
    scrollTop = el.scrollTop;
    // In glyph mode the textarea's own colours are transparent, so both the
    // text and the background have to come from the first ancestor that
    // actually has them.
    ebColour = firstColour(el, "color") ?? "#000000";
    ebBg = firstColour(el, "backgroundColor") ?? "#ffffff";
  }

  /** Nearest non-transparent `color` / `backgroundColor` at or above `el`. */
  function firstColour(el: HTMLElement, prop: "color" | "backgroundColor") {
    for (let n: HTMLElement | null = el; n; n = n.parentElement) {
      const v = getComputedStyle(n)[prop];
      if (v && v !== "rgba(0, 0, 0, 0)" && v !== "transparent") return v;
    }
    return null;
  }

  $effect(() => {
    if (glyph) queueMicrotask(syncSel);
  });
  $effect(() => {
    if (settings.fontMode !== "single" || families.length) return;
    getFonts()
      .then((list) => {
        families = list;
      })
      .catch(() => {});
  });

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
          <span class="block-sel-label"
            >{sblock || t("bottom.select_block")}</span
          >
          <span class="block-sel-arrow" class:open
            ><Icon name="chevron-down" size={12} /></span
          >
        </button>
        <!-- dropdown -->
        {#if open}
          <div class="block-sel-dd" bind:this={ddEl}>
            {#each blocks as b}
              <button
                class="block-sel-opt"
                class:active={b.name === sblock}
                onclick={() => pick(b.name)}
                title={b.name}
              >
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
        placeholder={gotoHex ? t("general.hex") : t("general.decimal")}
        oninput={(e) => onGvChange((e.target as HTMLInputElement).value)}
        onkeydown={(e) => {
          if (e.key === "Enter") onGoto();
        }}
      />
      <button onclick={onGoto}>{t("bottom.go")}</button>
    </fieldset>
  </div>
  <SearchResultsWindow
    results={searchResults}
    idx={searchIdx}
    query={searchQuery}
    progress={searchProgress}
    show={showResults}
    loading={searchLoading}
    onResultClick={onSearchResultClick}
    onClose={onCloseResults}
    onLoadMore={onLoadMoreResults}
  />
  {#if editVisible}
    <fieldset class="eb">
      <legend>{t("bottom.edit_buffer")}</legend>
      <div class="eb-wrap">
        {#if glyph}
          <!-- Glyph Mode: the unshaped cells drawn over the (invisible) textarea. -->
          <GlyphText
            text={buf}
            px={bufSize ?? BUF_PX}
            family={stackFamily || settings.singleFamily || "serif"}
            caret={caretPos}
            {selStart}
            {selEnd}
            {scrollTop}
            colour={ebColour}
            colourGlyphs={colour}
            bg={ebBg}
          />
        {/if}
        <textarea
          bind:this={ebEl}
          value={buf}
          class:ghost={glyph}
          oninput={(e) => onBufChange((e.target as HTMLTextAreaElement).value)}
          rows={3}
          spellcheck={false}
          style={bufStyle}
          placeholder="Click cells to add. Arrow keys navigate. Enter to add selected."
          oncontextmenu={(e) => onContextMenu(e)}
          onwheel={(e: WheelEvent & { currentTarget: HTMLTextAreaElement }) => {
            // Ctrl+wheel over the buffer changes the buffer font size (and must not
            // scroll the page / the textarea's own text).  The first notch starts
            // from the buffer's current rendered size, so zooming never jumps.
            if (!e.ctrlKey) return;
            e.preventDefault();
            const cur =
              bufSize ??
              parseFloat(getComputedStyle(e.currentTarget).fontSize) ??
              14;
            onBufSizeChange(cur - Math.sign(e.deltaY));
          }}
          onscroll={(e) =>
            (scrollTop = (e.currentTarget as HTMLTextAreaElement).scrollTop)}
          onselect={() => syncSel()}
          onkeyup={() => syncSel()}
          onkeydown={() => queueMicrotask(syncSel)}
          onmouseup={() => syncSel()}
          onclick={() => syncSel()}></textarea>
      </div>
      <div class="ebc">
        <div class="ebr">
          <label class="rd">
            <input
              type="radio"
              name="rdr"
              checked={glyph}
              onchange={() => onGlyphToggle(true)}
            />
            {t("bottom.glyph")}
          </label>
          <label class="rd">
            <input
              type="radio"
              name="rdr"
              checked={!glyph}
              onchange={() => onGlyphToggle(false)}
            />
            {t("bottom.text")}
          </label>
          <label class="ck">
            <input
              type="checkbox"
              checked={colour}
              onchange={(e) =>
                onColourToggle((e.target as HTMLInputElement).checked)}
            />
            {t("bottom.colour")}
          </label>
        </div>
        <div class="ebr">
          {#each [{ l: t("edit.char"), v: "char" }, { l: t("edit.ncr_hex"), v: "ncr_hex" }, { l: t("edit.ncr_dec"), v: "ncr_dec" }, { l: t("edit.html"), v: "html" }, { l: t("edit.ucn"), v: "ucn" }] as m}
            <label class="rd">
              <input
                type="radio"
                name="em"
                value={m.v}
                checked={mode === m.v}
                onchange={() => onModeChange(m.v)}
              />
              {m.l}
            </label>
          {/each}
        </div>
        <div class="ebr ebtns">
          {#if settings.fontMode === "single"}
            <select
              class="sb sel"
              bind:value={settings.singleFamily}
              title={t("fonts.single")}
            >
              {#if !families.includes(settings.singleFamily)}
                <option value={settings.singleFamily}
                  >{settings.singleFamily}</option
                >
              {/if}
              {#each families as f (f)}
                <option value={f}>{f}</option>
              {/each}
            </select>
          {/if}
          <button class="sb" onclick={onConfigureStack}
            >{t("font.configure")}…</button
          >
          <button class="sb" onclick={onHideToggle}>{t("bottom.hide")}</button>
          <button class="sb" onclick={onSave}>{t("bottom.save")}</button>
          <button class="sb" onclick={onClear}>{t("bottom.clear")}</button>
          <button class="sb" onclick={onCopy}>{t("bottom.copy")}</button>
          <button class="sb" onclick={onCut}>{t("bottom.cut")}</button>
        </div>
      </div>
    </fieldset>
  {/if}
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
  /* Single-font mode: the family picker sits where a button normally would,
     so it inherits the same height and rounding. */
  .sb.sel {
    max-width: 190px;
    padding: 0 6px;
    font-weight: 500;
  }
  .sb.sel:hover {
    background: var(--bg3);
    color: var(--fg);
    border-color: var(--bd);
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
  .eb-wrap {
    position: relative;
    flex: 1;
    min-width: 0;
    display: flex;
  }
  /* Glyph mode: the canvas sits on top of the textarea and owns the whole
     rendering (including the caret and the selection). */
  .eb-wrap textarea {
    position: relative;
    z-index: 1;
  }
  /* Glyph mode: the canvas is the visible text, the textarea only edits it. */
  .eb textarea.ghost {
    color: transparent;
    caret-color: transparent;
    background: transparent;
  }
  /* …including its selection, which follows the shaped layout, not our cells. */
  .eb textarea.ghost::selection {
    background: transparent;
    color: transparent;
  }
  .eb textarea {
    width: 100%;
    flex: 1;
    resize: none;
    font-family: monospace;
    font-size: 12px;
    /* Ctrl+wheel changes the font size, which must NOT change the buffer's
       height — otherwise zooming makes the panel grow/shrink. `height` (not
       `min-height`) pins it, and the text scrolls inside instead. */
    height: 52px;
    line-height: 1.5;
    overflow-y: auto;
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
