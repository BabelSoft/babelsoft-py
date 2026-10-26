<script lang="ts">
  // Tools ▸ Mandarin / Cantonese / Zhuang / Han Radical / Yi Radical Lookup.
  //
  // The original ships five dialogs (`CDialogMandarin`, `CDialogCantonese`,
  // `CDialogZhuang`, `CDialogHanRadical`, `CDialogYiRadical`) that only differ
  // in which table they ask: "which characters have this reading / radical?".
  // One window with a mode selector answers all of them and matches the way
  // the rest of this port groups the original's near-identical dialogs.
  import Icon from "../icons/Icon.svelte";
  import { t } from "../i18n.svelte";
  import { API_BASE } from "../api";

  export type LookupKind =
    | "pinyin"
    | "jyutping"
    | "zhuang"
    | "han_radical"
    | "yi_radical";

  interface Props {
    show: boolean;
    /** Pre-selects the mode when opened from a specific Tools ▸ … item. */
    kind: LookupKind;
    onClose: () => void;
    onGoto: (cp: number) => void;
  }
  let { show, kind, onClose, onGoto }: Props = $props();

  const KINDS: { id: LookupKind; label: string }[] = [
    { id: "pinyin", label: "lookup.m_pinyin" },
    { id: "jyutping", label: "lookup.m_jyutping" },
    { id: "zhuang", label: "lookup.m_zhuang" },
    { id: "han_radical", label: "lookup.m_han" },
    { id: "yi_radical", label: "lookup.m_yi" },
  ];

  let mode = $state<LookupKind>("pinyin");
  let q = $state("");
  let tone = $state(0);
  let strokes = $state(-1);
  let results = $state<{ cp: number; char: string; name: string }[]>([]);
  let count = $state(0);
  let loading = $state(false);
  let searched = $state(false);

  const isRadical = $derived(mode === "han_radical" || mode === "yi_radical");

  // Opening from a different Tools item switches the mode; the query is kept
  // so the user can compare the same syllable across languages.
  $effect(() => {
    if (show) mode = kind;
  });

  // ── window chrome ──
  let x = $state(160);
  let y = $state(90);
  let w = 620;
  let h = 560;
  let dragging = $state(false);
  let sx = $state(0),
    sy = $state(0),
    wx = $state(0),
    wy = $state(0);
  function dragStart(e: MouseEvent) {
    dragging = true;
    sx = e.clientX;
    sy = e.clientY;
    wx = x;
    wy = y;
    document.addEventListener("mousemove", dragMove);
    document.addEventListener("mouseup", dragEnd);
  }
  function dragMove(e: MouseEvent) {
    x = wx + (e.clientX - sx);
    y = wy + (e.clientY - sy);
  }
  function dragEnd() {
    dragging = false;
    document.removeEventListener("mousemove", dragMove);
    document.removeEventListener("mouseup", dragEnd);
  }

  let _timer: ReturnType<typeof setTimeout> | undefined;
  function schedule() {
    clearTimeout(_timer);
    _timer = setTimeout(search, 220);
  }

  async function search() {
    const query = q.trim();
    if (!query) {
      results = [];
      count = 0;
      searched = false;
      return;
    }
    loading = true;
    try {
      const params = new URLSearchParams({
        kind: mode,
        q: query,
        tone: String(tone),
        strokes: String(strokes),
      });
      const r = await fetch(`${API_BASE}/lookup?${params}`);
      if (r.ok) {
        const d = await r.json();
        results = d.results ?? [];
        count = d.count ?? results.length;
      } else {
        results = [];
        count = 0;
      }
    } catch {
      results = [];
      count = 0;
    }
    loading = false;
    searched = true;
  }

  function pick(k: LookupKind) {
    if (mode === k) return;
    mode = k;
    results = [];
    count = 0;
    searched = false;
    if (q.trim()) schedule();
  }

  function hex(cp: number): string {
    return cp.toString(16).toUpperCase().padStart(4, "0");
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key === "Enter") search();
  }
</script>

<svelte:window onkeydown={onKey} />

{#if show}
  <div
    class="lk"
    class:dragging
    style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
    role="dialog"
    aria-label={t("lookup.title")}
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="lk-head" onmousedown={dragStart}>
      <span class="lk-title">{t("lookup.title")}</span>
      <span class="lk-count"
        >{searched ? `${count} ${t("lookup.count")}` : ""}</span
      >
      <button class="lk-x" onclick={onClose} title={t("dlg.close")}
        ><Icon name="close" size={14} /></button
      >
    </div>

    <div class="lk-modes">
      {#each KINDS as k (k.id)}
        <button class:on={mode === k.id} onclick={() => pick(k.id)}
          >{t(k.label)}</button
        >
      {/each}
    </div>

    <div class="lk-bar">
      <input
        class="lk-q"
        placeholder={isRadical
          ? t("lookup.radical_hint")
          : t("lookup.reading_hint")}
        bind:value={q}
        oninput={schedule}
      />
      {#if !isRadical}
        <label class="lk-l"
          >{t("lookup.tone")}
          <select bind:value={tone} onchange={schedule}>
            <option value={0}>{t("lookup.any")}</option>
            {#each [1, 2, 3, 4, 5] as n (n)}
              <option value={n}>{n}</option>
            {/each}
          </select>
        </label>
      {:else if mode === "han_radical"}
        <label class="lk-l"
          >{t("lookup.strokes")}
          <select bind:value={strokes} onchange={schedule}>
            <option value={-1}>{t("lookup.any")}</option>
            {#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13] as n (n)}
              <option value={n}>{n}</option>
            {/each}
          </select>
        </label>
      {/if}
      <button class="lk-go" onclick={search}>{t("lookup.search")}</button>
    </div>

    <div class="lk-body">
      {#if loading}
        <div class="lk-msg">…</div>
      {:else if results.length === 0}
        <div class="lk-msg">
          {searched ? t("lookup.none") : t("lookup.idle")}
        </div>
      {:else}
        <div class="lk-list">
          {#each results as r (r.cp)}
            <button class="lk-row" onclick={() => onGoto(r.cp)}>
              <span class="lk-char">{r.char}</span>
              <span class="lk-u">U+{hex(r.cp)}</span>
              <span class="lk-name">{r.name}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .lk {
    position: fixed;
    z-index: 300;
    display: flex;
    flex-direction: column;
    background: var(--bg2, #fff);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 10px;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.28);
    overflow: hidden;
  }
  .lk.dragging {
    user-select: none;
  }
  .lk-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .lk-title {
    font-size: 12px;
    font-weight: 600;
  }
  .lk-count {
    flex: 1;
    font-size: 11px;
    color: var(--fg3);
  }
  .lk-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .lk-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .lk-modes {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px 10px 0;
  }
  .lk-modes button {
    font: inherit;
    font-size: 11px;
    padding: 4px 9px;
    border-radius: 999px;
    border: 1px solid var(--bd);
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
  }
  .lk-modes button.on {
    background: var(--ac);
    border-color: var(--ac);
    color: #fff;
  }
  .lk-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--bd);
  }
  .lk-q {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-size: 12px;
    padding: 5px 8px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--bg, #fff);
    color: var(--fg);
  }
  .lk-l {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg2);
    white-space: nowrap;
  }
  .lk-l select {
    font: inherit;
    font-size: 11px;
    padding: 3px 4px;
    border-radius: 5px;
    border: 1px solid var(--bd);
    background: var(--bg, #fff);
    color: var(--fg);
  }
  .lk-go {
    font: inherit;
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 6px;
    border: 1px solid var(--ac);
    background: var(--ac);
    color: #fff;
    cursor: pointer;
  }
  .lk-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 6px;
  }
  .lk-msg {
    padding: 24px 12px;
    text-align: center;
    font-size: 11.5px;
    color: var(--fg3);
  }
  .lk-list {
    display: flex;
    flex-direction: column;
  }
  .lk-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font: inherit;
    font-size: 11.5px;
    text-align: left;
    padding: 3px 6px;
    border: 0;
    border-radius: 5px;
    background: transparent;
    color: var(--fg);
    cursor: pointer;
  }
  .lk-row:hover {
    background: var(--bg3, #f3f4f6);
  }
  .lk-char {
    width: 1.6em;
    text-align: center;
  }
  .lk-u {
    font-family: ui-monospace, monospace;
    font-size: 10.5px;
    color: var(--fg3);
    white-space: nowrap;
  }
  .lk-name {
    color: var(--fg2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
