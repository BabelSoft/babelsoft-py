<script lang="ts">
  // Fonts ▸ Quality — a live seven-way comparison of the same sample text.
  //
  // Why a dialog and not just a menu: the seven LOGFONT.lfQuality modes are
  // only meaningful when you can see them side by side.  Each row is a PNG
  // rasterised by the backend (backend/glyph_render.py, FreeType), so the
  // difference between monochrome, grayscale AA and ClearType subpixel
  // rendering is real — not a CSS approximation.
  //
  // Honest scope: the character grid itself is rendered by WebView2 and CSS
  // cannot select a rasteriser, so the quality you pick here governs this
  // preview and Export Font Glyphs.  The dialog says so instead of pretending.
  import Icon from "../icons/Icon.svelte";
  import { untrack } from "svelte";
  import { API_BASE } from "../api";
  import { t } from "../i18n.svelte";
  import { settings } from "../settings.svelte";
  import { fontStack, loadUserFonts } from "../fontStack.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();

  /** The seven modes, in menu order — index == LOGFONT.lfQuality value. */
  const MODES = [
    { i: 0, key: "fonts.default", note: "LF_QUALITY_DEFAULT" },
    { i: 1, key: "fonts.draft", note: "LF_QUALITY_DRAFT" },
    { i: 2, key: "fonts.proof", note: "LF_QUALITY_PROOF" },
    { i: 3, key: "fonts.non_aa", note: "LF_QUALITY_NONANTIALIASED" },
    { i: 4, key: "fonts.aa", note: "LF_QUALITY_ANTIALIASED" },
    { i: 5, key: "fonts.cleartype", note: "LF_QUALITY_CLEARTYPE" },
    { i: 6, key: "fonts.cleartype_nat", note: "LF_QUALITY_CLEARTYPE_NATURAL" },
  ];

  let text = $state("Hamburgefonstiv 0123 — AaBbGg");
  let family = $state(settings.singleFamily || "Arial");
  let size = $state(28);
  let fg = $state("#101010");
  let bg = $state("#ffffff");
  let families = $state<string[]>([]);
  let loading = $state(false);

  // ── window chrome ──
  let x = $state(140);
  let y = $state(80);
  let w = $state(0);
  let h = $state(0);
  const MAX_W = 980;
  const MAX_H = 720;

  function clampToViewport() {
    if (typeof window === "undefined") return;
    untrack(() => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const m = 8;
      w = Math.max(360, Math.min(MAX_W, vw - m * 2));
      h = Math.max(260, Math.min(MAX_H, vh - m * 2));
      x = Math.min(Math.max(x, m), Math.max(m, vw - w - m));
      y = Math.min(Math.max(y, m), Math.max(m, vh - h - m));
    });
  }

  let dragging = $state(false);
  let dsx = $state(0),
    dsy = $state(0),
    wsx = $state(0),
    wsy = $state(0);
  function dragStart(e: MouseEvent) {
    dragging = true;
    dsx = e.clientX;
    dsy = e.clientY;
    wsx = x;
    wsy = y;
    document.addEventListener("mousemove", dragMove);
    document.addEventListener("mouseup", dragEnd);
  }
  function dragMove(e: MouseEvent) {
    x = wsx + (e.clientX - dsx);
    y = wsy + (e.clientY - dsy);
  }
  function dragEnd() {
    dragging = false;
    document.removeEventListener("mousemove", dragMove);
    document.removeEventListener("mouseup", dragEnd);
  }

  $effect(() => {
    if (!show) return;
    clampToViewport();
    untrack(async () => {
      if (!families.length) {
        loading = true;
        try {
          const r = await fetch(API_BASE + "/fonts");
          const d = await r.json();
          families = (d.families ?? d.fonts ?? d ?? []) as string[];
        } catch {
          families = [];
        }
        loading = false;
      }
      if (!fontStack.userFonts.length) loadUserFonts();
    });
    const onResize = () => clampToViewport();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  });

  /** Backend URL for one row of the comparison. */
  function src(quality: number): string {
    const p = new URLSearchParams({
      text,
      font: family,
      size: String(size),
      quality: String(quality),
      fg,
      bg,
      scale: "2",
    });
    return `${API_BASE}/glyphs/sample?${p.toString()}`;
  }
</script>

{#if show}
  <div class="modal-mask" role="presentation">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fqd"
      style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
      onmousedown={(e) => e.stopPropagation()}
      role="dialog"
      aria-label={t("fonts.quality_dialog")}
      tabindex="-1"
    >
      <div
        class="fqd-head"
        onmousedown={dragStart}
        role="toolbar"
        tabindex="-1"
      >
        <span class="fqd-title">{t("fonts.quality_dialog")}</span>
        <span class="fqd-spacer"></span>
        <button class="fqd-x" onclick={onClose} title={t("dlg.close")}
          ><Icon name="close" size={14} /></button
        >
      </div>

      <div class="fqd-bar">
        <label>
          <span>{t("fonts.quality_sample")}</span>
          <input bind:value={text} spellcheck="false" />
        </label>
        <label>
          <span>{t("fonts.export_size")}</span>
          <input
            type="number"
            min="6"
            max="200"
            bind:value={size}
            style="width:64px"
          />
        </label>
        <label>
          <span>{t("fonts.export_fg")}</span>
          <input type="color" bind:value={fg} />
        </label>
        <label>
          <span>{t("fonts.export_bg")}</span>
          <input type="color" bind:value={bg} />
        </label>
      </div>

      <div class="fqd-note">{t("fonts.quality_note")}</div>

      <div class="fqd-rows">
        {#each MODES as m (m.i)}
          <button
            class="fqd-row"
            class:on={settings.fontQuality === m.i}
            onclick={() => (settings.fontQuality = m.i)}
            title={m.note}
          >
            <span class="fqd-lab">
              <span class="fqd-name">{t(m.key)}</span>
              <span class="fqd-mono">{m.note.replace("LF_QUALITY_", "")}</span>
            </span>
            <span class="fqd-img">
              <img
                src={src(m.i)}
                alt={t(m.key)}
                style="background:{bg}"
                draggable="false"
              />
            </span>
          </button>
        {/each}
      </div>

      <div class="fqd-foot">
        <label class="fqd-fam">
          <span>Font</span>
          <select bind:value={family}>
            {#if !families.includes(family)}
              <option value={family}>{family}</option>
            {/if}
            {#each families as f (f)}
              <option value={f}>{f}</option>
            {/each}
            {#each fontStack.userFonts as uf (uf.id)}
              <option value={"u:" + uf.id}>{uf.family} (uploaded)</option>
            {/each}
          </select>
        </label>
        {#if loading}<span class="fqd-dim">…</span>{/if}
        <span class="fqd-spacer"></span>
        <button class="fqd-ok" onclick={onClose}>{t("dlg.close")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-mask {
    position: fixed;
    inset: 0;
    z-index: 300;
    background: rgba(0, 0, 0, 0.28);
  }
  .fqd {
    position: absolute;
    box-sizing: border-box;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg2, #fff);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 10px;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }
  .fqd-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .fqd-title {
    font-size: 12px;
    font-weight: 600;
  }
  .fqd-spacer {
    flex: 1;
  }
  .fqd-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .fqd-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .fqd-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 8px 12px 4px;
  }
  .fqd-bar label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--fg2);
  }
  .fqd-bar label:first-child {
    flex: 1;
    min-width: 220px;
  }
  .fqd-bar input:not([type]) {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-size: 12px;
    padding: 4px 7px;
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
  }
  .fqd-bar input[type="number"] {
    font: inherit;
    font-size: 12px;
    padding: 4px 6px;
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
  }
  .fqd-bar input[type="color"] {
    width: 30px;
    height: 24px;
    padding: 0;
    border: 1px solid var(--bd);
    border-radius: 5px;
    background: transparent;
  }
  .fqd-note {
    padding: 2px 12px 8px;
    font-size: 11px;
    line-height: 1.45;
    color: var(--fg3);
  }
  .fqd-rows {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 0 12px 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .fqd-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 8px;
    border: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    color: inherit;
    cursor: pointer;
    text-align: left;
  }
  .fqd-row:hover {
    background: var(--bg3, #f3f4f6);
  }
  .fqd-row.on {
    border-color: var(--ac);
    background: var(--bg3, #f3f4f6);
  }
  .fqd-lab {
    width: 150px;
    flex: none;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .fqd-name {
    font-size: 12px;
    font-weight: 500;
  }
  .fqd-mono {
    font-family: ui-monospace, monospace;
    font-size: 9.5px;
    color: var(--fg3);
  }
  .fqd-img {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    display: flex;
    align-items: center;
  }
  /* The samples come back supersampled ×2, so scale them back down to the
     requested point size while keeping the pixel structure visible. */
  .fqd-img img {
    max-width: 100%;
    height: auto;
    image-rendering: auto;
  }
  .fqd-foot {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .fqd-fam {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--fg2);
  }
  .fqd-fam select {
    max-width: 220px;
    font: inherit;
    font-size: 12px;
    padding: 4px 6px;
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
  }
  .fqd-dim {
    color: var(--fg3);
    font-size: 11px;
  }
  .fqd-ok {
    font: inherit;
    font-size: 12px;
    padding: 5px 14px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--ac);
    color: #fff;
    cursor: pointer;
  }
</style>
