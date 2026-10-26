<script lang="ts">
  // Help ▸ Help / About — one window with both, like the original's
  // `CDialogAbout` (which shows the product version, the supported Unicode
  // version and the project links).
  //
  // The shortcut table is generated from `localizedMenus()`, so it can never
  // drift: it lists exactly the accelerators the menu bar advertises.
  import Icon from "../icons/Icon.svelte";
  import { untrack } from "svelte";
  import { localizedMenus, t } from "../i18n.svelte";
  import { settings } from "../settings.svelte";
  import { API_BASE } from "../api";

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();

  /** `"1.0.0"` — the app's own version (pyproject / package.json). */
  const APP_VERSION = "1.0.0";

  let about = $state<{
    backend: string;
    python: string;
    unicode: string;
    unicode_versions: number;
    ivd: string;
    emoji: string;
  } | null>(null);

  /** Collect `{menu, items:[{label, key}]}` for every advertised shortcut. */
  const shortcuts = $derived.by(() => {
    const out: { menu: string; items: { label: string; key: string }[] }[] = [];
    for (const m of localizedMenus(settings)) {
      const items: { label: string; key: string }[] = [];
      const walk = (list: { l: string; k?: string; sub?: any[] }[]) => {
        for (const it of list) {
          if (it.sub) walk(it.sub);
          else if (it.k) items.push({ label: it.l, key: it.k });
        }
      };
      walk(m.items as any);
      if (items.length) out.push({ menu: m.label, items });
    }
    return out;
  });

  // ── window chrome ──
  let x = $state(220);
  let y = $state(120);
  let w = $state(0);
  let h = $state(0);
  const MAX_W = 720;
  const MAX_H = 620;

  function clampToViewport() {
    if (typeof window === "undefined") return;
    untrack(() => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const m = 8;
      w = Math.max(340, Math.min(MAX_W, vw - m * 2));
      h = Math.max(240, Math.min(MAX_H, vh - m * 2));
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
      if (about) return;
      try {
        const r = await fetch(API_BASE + "/about");
        if (r.ok) about = await r.json();
      } catch {
        // The dialog is still useful without the version block.
      }
    });
    const onResize = () => clampToViewport();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  });
</script>

{#if show}
  <div class="modal-mask" role="presentation">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="hpd"
      style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
      onmousedown={(e) => e.stopPropagation()}
      role="dialog"
      aria-label={t("help.about")}
      tabindex="-1"
    >
      <div
        class="hpd-head"
        onmousedown={dragStart}
        role="toolbar"
        tabindex="-1"
      >
        <span class="hpd-title">{t("menu.help")}</span>
        <span class="hpd-spacer"></span>
        <button class="hpd-x" onclick={onClose} title={t("dlg.close")}
          ><Icon name="close" size={14} /></button
        >
      </div>

      <div class="hpd-body">
        <section class="hpd-about">
          <div class="hpd-prod">BabelMap {APP_VERSION}</div>
          <div class="hpd-note">
            A Python + Svelte port of BabelStone's BabelMap. The character data,
            fonts and every menu command run in this app; the Python backend
            owns the Unicode database and the rasteriser.
          </div>
          <table class="hpd-vers">
            <tbody>
              <tr>
                <th>Unicode</th>
                <td>{about?.unicode || "…"}</td>
              </tr>
              <tr>
                <th>Unicode versions bundled</th>
                <td>{about?.unicode_versions || "…"}</td>
              </tr>
              <tr>
                <th>Backend</th>
                <td>FastAPI {about?.backend || "…"}</td>
              </tr>
              <tr>
                <th>Python</th>
                <td>{about?.python || "…"}</td>
              </tr>
              <tr>
                <th>IVD</th>
                <td>{about?.ivd || "—"}</td>
              </tr>
              <tr>
                <th>Emoji</th>
                <td>{about?.emoji || "—"}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="hpd-keys">
          <div class="hpd-h">{t("help.help")}</div>
          <div class="hpd-cols">
            {#each shortcuts as g (g.menu)}
              <div class="hpd-group">
                <div class="hpd-gname">{g.menu}</div>
                {#each g.items as s (g.menu + s.label)}
                  <div class="hpd-krow">
                    <span class="hpd-klabel">{s.label}</span>
                    <span class="hpd-key">{s.key}</span>
                  </div>
                {/each}
              </div>
            {/each}
          </div>
        </section>
      </div>

      <div class="hpd-foot">
        <span class="hpd-hint"
          >Ctrl+hover a cell magnifies it; Ctrl+wheel zooms the grid; Ctrl+wheel
          over the edit buffer zooms the buffer.</span
        >
        <span class="hpd-spacer"></span>
        <button class="hpd-ok" onclick={onClose}>{t("dlg.close")}</button>
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
  .hpd {
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
  .hpd-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .hpd-title {
    font-size: 12px;
    font-weight: 600;
  }
  .hpd-spacer {
    flex: 1;
  }
  .hpd-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .hpd-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .hpd-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .hpd-prod {
    font-size: 15px;
    font-weight: 700;
  }
  .hpd-note {
    margin-top: 4px;
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--fg2);
    max-width: 60ch;
  }
  .hpd-vers {
    margin-top: 10px;
    border-collapse: collapse;
    font-size: 11.5px;
  }
  .hpd-vers th {
    text-align: left;
    font-weight: 500;
    color: var(--fg3);
    padding: 2px 14px 2px 0;
    white-space: nowrap;
  }
  .hpd-vers td {
    font-family: ui-monospace, monospace;
    padding: 2px 0;
  }
  .hpd-h {
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
    padding-top: 10px;
    border-top: 1px solid var(--bd);
  }
  .hpd-cols {
    columns: 2;
    column-gap: 24px;
  }
  .hpd-group {
    break-inside: avoid;
    margin-bottom: 10px;
  }
  .hpd-gname {
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--fg3);
    margin-bottom: 3px;
  }
  .hpd-krow {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    font-size: 11.5px;
    padding: 1px 0;
  }
  .hpd-klabel {
    color: var(--fg);
  }
  .hpd-key {
    font-family: ui-monospace, monospace;
    font-size: 10.5px;
    color: var(--fg2);
    white-space: nowrap;
  }
  .hpd-foot {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .hpd-hint {
    font-size: 10.5px;
    color: var(--fg3);
  }
  .hpd-ok {
    font: inherit;
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--ac);
    color: #fff;
    cursor: pointer;
  }
</style>
