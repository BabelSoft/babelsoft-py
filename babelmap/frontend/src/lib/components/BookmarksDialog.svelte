<script lang="ts">
  // Bookmarks ▸ Manage Bookmarks… — the port of `CDialogBookmarks`.
  //
  // The original is a two-column list (Code Point / Character Name) with Add,
  // Remove and Remove All buttons, a "Bookmarks (n of 32)" heading, sortable
  // columns, and every edit written straight back to the registry in list
  // order.  This dialog does the same against `settings.bookmarks`.
  import Icon from "../icons/Icon.svelte";
  import { untrack } from "svelte";
  import { t } from "../i18n.svelte";
  import { API_BASE } from "../api";
  import {
    MAX_BOOKMARKS,
    addBookmark,
    bookmarks,
    clearBookmarks,
    hex,
    parseCodepointList,
    removeBookmark,
    setBookmarks,
  } from "../bookmarks.svelte";

  interface Props {
    show: boolean;
    onClose: () => void;
    onGoto: (cp: number) => void;
  }
  let { show, onClose, onGoto }: Props = $props();

  let selected = $state<Set<number>>(new Set());
  let sortBy = $state<"cp" | "name">("cp");
  let sortAsc = $state(true);
  let adding = $state(false);
  let addText = $state("");
  let addError = $state("");
  let busy = $state(false);

  const list = $derived.by(() => {
    const rows = [...bookmarks()];
    rows.sort((a, b) =>
      sortBy === "cp"
        ? a.cp - b.cp
        : a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
    );
    if (!sortAsc) rows.reverse();
    return rows;
  });

  /** Header click — the original toggles the direction on a second click. */
  function sortOn(col: "cp" | "name") {
    if (sortBy === col) sortAsc = !sortAsc;
    else {
      sortBy = col;
      sortAsc = true;
    }
  }

  function toggle(cp: number) {
    const next = new Set(selected);
    if (next.has(cp)) next.delete(cp);
    else next.add(cp);
    selected = next;
  }

  function removeSelected() {
    if (!selected.size) return;
    if (!confirm(t("bookmarks.delete_selected"))) return;
    for (const cp of selected) removeBookmark(cp);
    selected = new Set();
  }

  function removeAll() {
    if (!bookmarks().length) return;
    if (!confirm(t("bookmarks.delete_all"))) return;
    clearBookmarks();
    selected = new Set();
  }

  /** Resolve the name of each typed code point, then append the valid ones. */
  async function doAdd() {
    const cps = parseCodepointList(addText);
    if (!cps.length) {
      addError = "—";
      return;
    }
    busy = true;
    addError = "";
    let added = 0;
    for (const cp of cps) {
      let name = `U+${hex(cp)}`;
      try {
        const r = await fetch(`${API_BASE}/codepoint/${cp}`);
        if (r.ok) {
          const d = await r.json();
          if (d?.name) name = d.name;
        }
      } catch {
        // Name lookup failed — the code point is still bookmarkable.
      }
      if (addBookmark(cp, name) >= 0) added++;
      if (bookmarks().length >= MAX_BOOKMARKS) break;
    }
    busy = false;
    addText = "";
    adding = false;
    if (added === 0) addError = t("bookmarks.added").replace("{n}", "0");
  }

  /** Write the current on-screen order back (the original's ReorderBookmarks). */
  function applyOrder() {
    setBookmarks(list);
  }

  // ── window chrome ──
  let x = $state(200);
  let y = $state(110);
  let w = $state(0);
  let h = $state(0);
  const MAX_W = 620;
  const MAX_H = 560;

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
    untrack(() => {
      selected = new Set();
      adding = false;
      addText = "";
      addError = "";
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
      class="bmd"
      style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
      onmousedown={(e) => e.stopPropagation()}
      role="dialog"
      aria-label={t("bookmarks.manage")}
      tabindex="-1"
    >
      <div
        class="bmd-head"
        onmousedown={dragStart}
        role="toolbar"
        tabindex="-1"
      >
        <span class="bmd-title">{t("bookmarks.title")}</span>
        <span class="bmd-sub"
          >{t("bookmarks.heading")
            .replace("{n}", String(bookmarks().length))
            .replace("{max}", String(MAX_BOOKMARKS))}</span
        >
        <span class="bmd-spacer"></span>
        <button class="bmd-x" onclick={onClose} title={t("bookmarks.close")}
          ><Icon name="close" size={14} /></button
        >
      </div>

      <div class="bmd-cols">
        <button class="bmd-col" onclick={() => sortOn("cp")}
          >{t("bookmarks.codepoint")}{sortBy === "cp"
            ? sortAsc
              ? " ▲"
              : " ▼"
            : ""}</button
        >
        <button class="bmd-col wide" onclick={() => sortOn("name")}
          >{t("bookmarks.name")}{sortBy === "name"
            ? sortAsc
              ? " ▲"
              : " ▼"
            : ""}</button
        >
      </div>

      <div class="bmd-rows">
        {#each list as b (b.cp)}
          <button
            class="bmd-row"
            class:on={selected.has(b.cp)}
            onclick={(e) => {
              if (e.shiftKey || e.ctrlKey) toggle(b.cp);
              else toggle(b.cp);
            }}
            ondblclick={() => onGoto(b.cp)}
            title={`U+${hex(b.cp)}`}
          >
            <span class="bmd-cp">{hex(b.cp)}</span>
            <span class="bmd-name">{b.name}</span>
          </button>
        {/each}
        {#if !list.length}
          <div class="bmd-empty">{t("bookmarks.empty")}</div>
        {/if}
      </div>

      {#if adding}
        <div class="bmd-add">
          <div class="bmd-hint">
            {t("bookmarks.add_hint").replace(
              "{n}",
              String(MAX_BOOKMARKS - bookmarks().length),
            )}
          </div>
          <div class="bmd-addrow">
            <input
              bind:value={addText}
              spellcheck="false"
              placeholder="4E00 4E01 1F600"
              onkeydown={(e) => {
                if (e.key === "Enter") doAdd();
                if (e.key === "Escape") adding = false;
              }}
            />
            <button class="bmd-ok" onclick={doAdd} disabled={busy}>
              {busy ? "…" : t("bookmarks.add")}
            </button>
            <button class="bmd-btn" onclick={() => (adding = false)}>×</button>
          </div>
          {#if addError}<div class="bmd-err">{addError}</div>{/if}
        </div>
      {/if}

      <div class="bmd-foot">
        <button
          class="bmd-btn"
          onclick={() => (adding = !adding)}
          disabled={bookmarks().length >= MAX_BOOKMARKS}
          >{t("bookmarks.add")}</button
        >
        <button
          class="bmd-btn"
          onclick={removeSelected}
          disabled={!selected.size}>{t("bookmarks.remove")}</button
        >
        <button
          class="bmd-btn"
          onclick={removeAll}
          disabled={!bookmarks().length}>{t("bookmarks.remove_all")}</button
        >
        <span class="bmd-spacer"></span>
        <button class="bmd-btn" onclick={applyOrder} title="Apply sort order"
          >⇅</button
        >
        <button class="bmd-ok" onclick={onClose}>{t("bookmarks.close")}</button>
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
  .bmd {
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
  .bmd-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .bmd-title {
    font-size: 12px;
    font-weight: 600;
  }
  .bmd-sub {
    font-size: 10.5px;
    color: var(--fg3);
  }
  .bmd-spacer {
    flex: 1;
  }
  .bmd-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .bmd-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .bmd-cols {
    display: flex;
    gap: 0;
    padding: 4px 10px 0;
  }
  .bmd-col {
    flex: 0 0 74px;
    text-align: left;
    font: inherit;
    font-size: 10.5px;
    font-weight: 600;
    color: var(--fg2);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--bd);
    padding: 4px 6px;
    cursor: pointer;
  }
  .bmd-col.wide {
    flex: 1;
  }
  .bmd-rows {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 4px 10px;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .bmd-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font: inherit;
    font-size: 12px;
    text-align: left;
    padding: 3px 6px;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }
  .bmd-row:hover {
    background: var(--bg3, #f3f4f6);
  }
  .bmd-row.on {
    border-color: var(--ac);
    background: var(--bg3, #f3f4f6);
  }
  .bmd-cp {
    flex: 0 0 66px;
    font-family: ui-monospace, monospace;
    font-size: 11.5px;
    color: var(--fg2);
  }
  .bmd-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .bmd-empty {
    padding: 24px;
    text-align: center;
    color: var(--fg3);
    font-size: 12px;
  }
  .bmd-add {
    padding: 8px 10px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .bmd-hint {
    font-size: 10.5px;
    color: var(--fg3);
    margin-bottom: 5px;
  }
  .bmd-addrow {
    display: flex;
    gap: 6px;
  }
  .bmd-addrow input {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-family: ui-monospace, monospace;
    font-size: 12px;
    padding: 4px 7px;
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
  }
  .bmd-err {
    font-size: 10.5px;
    color: #c0392b;
    margin-top: 4px;
  }
  .bmd-foot {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .bmd-btn,
  .bmd-ok {
    font: inherit;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--bg);
    color: var(--fg);
    cursor: pointer;
  }
  .bmd-btn:disabled {
    opacity: 0.45;
    cursor: default;
  }
  .bmd-ok {
    background: var(--ac);
    color: #fff;
  }
  .bmd-ok:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
