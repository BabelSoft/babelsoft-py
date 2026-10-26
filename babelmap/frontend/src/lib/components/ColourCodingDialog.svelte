<script lang="ts">
  // Options ▸ Customise Colours… — edit the Colour Coding palette.
  //
  // The original's `CDialogColours` lets you pick a foreground/background pair
  // for every value of the selected coding mode (General Category, Bidi Class,
  // Script, …).  This dialog edits the same thing through
  // `settings.colourOverrides`, keyed `mode:value`, so overrides survive a
  // reload and are independent per mode.
  import Icon from "../icons/Icon.svelte";
  import { untrack } from "svelte";
  import { t } from "../i18n.svelte";
  import {
    COLOUR_CODINGS,
    settings,
    type ColourCoding,
  } from "../settings.svelte";
  import { COLOUR_LABELS } from "../i18n.svelte";
  import { defaultColour, knownValues } from "../colourCoding";

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();

  /** The mode being edited; `none` has no palette so it is not offered. */
  let mode = $state<ColourCoding>(
    settings.colourCoding === "none" ? "gc" : settings.colourCoding,
  );
  let filter = $state("");

  const MODES = COLOUR_CODINGS.filter((m) => m !== "none") as Exclude<
    ColourCoding,
    "none"
  >[];

  /** Values to show: the curated ones plus anything already overridden. */
  const values = $derived.by(() => {
    const base = knownValues(mode);
    const extra = Object.keys(settings.colourOverrides ?? {})
      .filter((k) => k.startsWith(mode + ":"))
      .map((k) => k.slice(mode.length + 1))
      .filter((v) => !base.includes(v));
    const all = [...base, ...extra].sort((a, b) => a.localeCompare(b));
    const q = filter.trim().toLowerCase();
    return q ? all.filter((v) => v.toLowerCase().includes(q)) : all;
  });

  function override(mode: ColourCoding, value: string) {
    return settings.colourOverrides?.[`${mode}:${value}`];
  }

  /** Current background of a value (override or default). */
  function bgOf(mode: ColourCoding, value: string): string {
    return override(mode, value)?.bg || defaultColour(mode, value);
  }

  function setBg(value: string, bg: string) {
    const key = `${mode}:${value}`;
    settings.colourOverrides = {
      ...(settings.colourOverrides ?? {}),
      [key]: { bg, fg: override(mode, value)?.fg || "" } as any,
    };
  }

  function resetValue(value: string) {
    const next = { ...(settings.colourOverrides ?? {}) };
    delete next[`${mode}:${value}`];
    settings.colourOverrides = next;
  }

  function resetMode() {
    const next: typeof settings.colourOverrides = {};
    for (const [k, v] of Object.entries(settings.colourOverrides ?? {})) {
      if (!k.startsWith(mode + ":")) next[k] = v;
    }
    settings.colourOverrides = next;
  }

  function resetAll() {
    settings.colourOverrides = {};
  }

  // ── window chrome ──
  let x = $state(180);
  let y = $state(100);
  let w = $state(0);
  let h = $state(0);
  const MAX_W = 760;
  const MAX_H = 640;

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
    const onResize = () => clampToViewport();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  });
</script>

{#if show}
  <div class="modal-mask" role="presentation">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="ccd"
      style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
      onmousedown={(e) => e.stopPropagation()}
      role="dialog"
      aria-label={t("options.customize_colours")}
      tabindex="-1"
    >
      <div
        class="ccd-head"
        onmousedown={dragStart}
        role="toolbar"
        tabindex="-1"
      >
        <span class="ccd-title">{t("options.customize_colours")}</span>
        <span class="ccd-spacer"></span>
        <button class="ccd-x" onclick={onClose} title={t("dlg.close")}
          ><Icon name="close" size={14} /></button
        >
      </div>

      <div class="ccd-bar">
        <label>
          <span>{t("options.colour_coding")}</span>
          <select bind:value={mode}>
            {#each MODES as m, i (m)}
              <option value={m}>{t(COLOUR_LABELS[i + 1])}</option>
            {/each}
          </select>
        </label>
        <label>
          <span>Filter</span>
          <input bind:value={filter} spellcheck="false" placeholder="…" />
        </label>
        <span class="ccd-spacer"></span>
        <button class="ccd-btn" onclick={resetMode}>Reset mode</button>
        <button class="ccd-btn" onclick={resetAll}>Reset all</button>
      </div>

      <div class="ccd-list">
        {#each values as v (mode + ":" + v)}
          <div class="ccd-row">
            <input
              type="color"
              value={bgOf(mode, v)}
              oninput={(e) => setBg(v, (e.target as HTMLInputElement).value)}
              title={bgOf(mode, v)}
            />
            <span class="ccd-val">{v}</span>
            <span class="ccd-sample" style:background={bgOf(mode, v)}>Ag字</span
            >
            {#if override(mode, v)}
              <span class="ccd-badge">custom</span>
            {/if}
            <span class="ccd-spacer"></span>
            {#if override(mode, v)}
              <button class="ccd-mini" onclick={() => resetValue(v)}>×</button>
            {/if}
          </div>
        {/each}
        {#if !values.length}<div class="ccd-empty">—</div>{/if}
      </div>

      <div class="ccd-foot">
        <span class="ccd-hint"
          >Options ▸ Colour Coding selects which of these is painted on the
          grid.</span
        >
        <span class="ccd-spacer"></span>
        <button class="ccd-ok" onclick={onClose}>{t("dlg.close")}</button>
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
  .ccd {
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
  .ccd-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .ccd-title {
    font-size: 12px;
    font-weight: 600;
  }
  .ccd-spacer {
    flex: 1;
  }
  .ccd-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .ccd-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .ccd-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--bd);
  }
  .ccd-bar label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--fg2);
  }
  .ccd-bar select,
  .ccd-bar input {
    font: inherit;
    font-size: 12px;
    padding: 4px 7px;
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
  }
  .ccd-btn,
  .ccd-ok {
    font: inherit;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--bg);
    color: var(--fg);
    cursor: pointer;
  }
  .ccd-ok {
    background: var(--ac);
    color: #fff;
  }
  .ccd-list {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .ccd-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 2px 4px;
    border-radius: 6px;
    font-size: 12px;
  }
  .ccd-row:hover {
    background: var(--bg3, #f3f4f6);
  }
  .ccd-row input[type="color"] {
    width: 28px;
    height: 22px;
    padding: 0;
    border: 1px solid var(--bd);
    border-radius: 5px;
    background: transparent;
  }
  .ccd-val {
    width: 190px;
    flex: none;
    font-family: ui-monospace, monospace;
    font-size: 11.5px;
  }
  .ccd-sample {
    padding: 1px 8px;
    border-radius: 5px;
    border: 1px solid var(--bd);
    font-size: 12px;
  }
  .ccd-badge {
    font-size: 9.5px;
    color: var(--ac);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .ccd-mini {
    border: 0;
    background: transparent;
    color: var(--fg3);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
  }
  .ccd-mini:hover {
    color: var(--ac);
  }
  .ccd-empty {
    padding: 20px;
    text-align: center;
    color: var(--fg3);
  }
  .ccd-foot {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .ccd-hint {
    font-size: 10.5px;
    color: var(--fg3);
  }
</style>
