<script lang="ts">
  // Tools ▸ Generate Core UCD Data — the port of `CDialogUCD`.
  //
  // The original is a version selector + block list + "all / blocks / range"
  // radio + two algorithmic-run checkboxes, over a 15-column table of
  // `Unicode::UCDFields`, with Generate / Copy / Save buttons.  This port only
  // has one UCD on disk, so the version selector shows that release read-only;
  // everything else maps one-to-one, and the rows come from `/api/ucd/generate`
  // (which abbreviates CJK/Hangul runs to `<…, First>` / `<…, Last>` exactly
  // like UnicodeData.txt unless the checkboxes are ticked).
  import Icon from "../icons/Icon.svelte";
  import { t } from "../i18n.svelte";
  import { API_BASE } from "../api";

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();

  let fields = $state<string[]>([]);
  let rows = $state<string[][]>([]);
  let total = $state(0);
  let shown = $state(0);
  let busy = $state(false);
  let version = $state("");
  let startHex = $state("0000");
  let endHex = $state("FFFF");
  let allCjk = $state(false);
  let allHangul = $state(false);
  let blocks = $state<{ name: string; start: number; end: number }[]>([]);
  let blockName = $state("");

  $effect(() => {
    if (!show) return;
    if (!fields.length) void init();
  });

  async function init() {
    try {
      const [f, b, v] = await Promise.all([
        fetch(`${API_BASE}/ucd/fields`).then((r) => r.json()),
        fetch(`${API_BASE}/blocks`).then((r) => r.json()),
        fetch(`${API_BASE}/about`).then((r) => r.json()),
      ]);
      fields = f.fields ?? [];
      blocks = (b.blocks ?? b ?? []).map(
        (x: { name: string; start: number; end: number }) => x,
      );
      version = v.unicode ?? "";
    } catch {
      // The dialog still works without the block list.
    }
  }

  function parseHex(text: string, fallback: number): number {
    const v = parseInt(text.replace(/[^0-9a-fA-F]/g, ""), 16);
    return Number.isFinite(v) ? v : fallback;
  }

  function pickBlock(name: string) {
    blockName = name;
    const b = blocks.find((x) => x.name === name);
    if (!b) return;
    startHex = b.start.toString(16).toUpperCase().padStart(4, "0");
    endHex = b.end.toString(16).toUpperCase().padStart(4, "0");
  }

  async function generate() {
    const start = parseHex(startHex, 0);
    const end = parseHex(endHex, 0xffff);
    busy = true;
    try {
      const params = new URLSearchParams({
        start: String(start),
        end: String(end),
        all_cjk: String(allCjk),
        all_hangul: String(allHangul),
        limit: "20000",
      });
      const r = await fetch(`${API_BASE}/ucd/generate?${params}`);
      if (r.ok) {
        const d = await r.json();
        rows = d.rows ?? [];
        total = d.total ?? rows.length;
        shown = d.shown ?? rows.length;
      } else {
        rows = [];
        total = shown = 0;
      }
    } catch {
      rows = [];
      total = shown = 0;
    }
    busy = false;
  }

  /** Tab-separated, i.e. what the original's Copy button puts on the clipboard. */
  function asText(): string {
    return rows.map((r) => r.join("\t")).join("\n");
  }

  async function copy() {
    if (!rows.length) return;
    try {
      await navigator.clipboard.writeText(asText());
      onStatus("Copied");
    } catch {
      onStatus("Clipboard unavailable");
    }
  }

  function save() {
    if (!rows.length) return;
    const blob = new Blob([asText()], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ucd.txt";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  let status = $state("");
  function onStatus(msg: string) {
    status = msg;
    setTimeout(() => (status = ""), 2500);
  }

  // ── window chrome ──
  let x = $state(90);
  let y = $state(60);
  let w = 900;
  let h = 620;
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

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }
</script>

<svelte:window onkeydown={onKey} />

{#if show}
  <div
    class="uc"
    class:dragging
    style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
    role="dialog"
    aria-label={t("tools.ucd")}
    tabindex="-1"
  >
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="uc-head" onmousedown={dragStart}>
      <span class="uc-title">{t("tools.ucd")}</span>
      <span class="uc-sub">{version ? `Unicode ${version}` : ""}</span>
      <span class="uc-grow"></span>
      <button class="uc-x" onclick={onClose} title={t("dlg.close")}
        ><Icon name="close" size={14} /></button
      >
    </div>

    <div class="uc-bar">
      <label class="uc-l">
        {t("ucd.block")}
        <select bind:value={blockName} onchange={() => pickBlock(blockName)}>
          <option value="">—</option>
          {#each blocks as b (b.name)}
            <option value={b.name}>{b.name}</option>
          {/each}
        </select>
      </label>
      <label class="uc-l">
        {t("ucd.start")}
        <input class="uc-hex" bind:value={startHex} />
      </label>
      <label class="uc-l">
        {t("ucd.end")}
        <input class="uc-hex" bind:value={endHex} />
      </label>
      <label class="uc-chk">
        <input type="checkbox" bind:checked={allCjk} />{t("ucd.all_cjk")}
      </label>
      <label class="uc-chk">
        <input type="checkbox" bind:checked={allHangul} />{t("ucd.all_hangul")}
      </label>
      <button class="uc-go" onclick={generate} disabled={busy}
        >{busy ? "…" : t("ucd.generate")}</button
      >
    </div>

    <div class="uc-body">
      {#if rows.length === 0}
        <div class="uc-msg">{busy ? "…" : t("ucd.idle")}</div>
      {:else}
        <table class="uc-table">
          <thead>
            <tr>
              {#each fields as f (f)}
                <th>{f}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each rows as row, i (i)}
              <tr>
                {#each row as cell, j (j)}
                  <td>{cell}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <div class="uc-foot">
      <span class="uc-count"
        >{shown === total ? `${total}` : `${shown} / ${total}`}
        {t("lookup.count")}</span
      >
      <span class="uc-status">{status}</span>
      <span class="uc-grow"></span>
      <button class="uc-btn" onclick={copy} disabled={!rows.length}
        >{t("ucd.copy")}</button
      >
      <button class="uc-btn" onclick={save} disabled={!rows.length}
        >{t("ucd.save")}</button
      >
      <button class="uc-btn primary" onclick={onClose}>{t("dlg.close")}</button>
    </div>
  </div>
{/if}

<style>
  .uc {
    position: fixed;
    z-index: 300;
    display: flex;
    flex-direction: column;
    max-width: calc(100vw - 16px);
    max-height: calc(100vh - 16px);
    background: var(--bg2, #fff);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 10px;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }
  .uc.dragging {
    user-select: none;
  }
  .uc-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .uc-title {
    font-size: 12px;
    font-weight: 600;
  }
  .uc-sub {
    font-size: 11px;
    color: var(--fg3);
  }
  .uc-grow {
    flex: 1;
  }
  .uc-x {
    border: 0;
    background: transparent;
    color: var(--fg2);
    cursor: pointer;
    padding: 3px;
    border-radius: 5px;
    display: flex;
  }
  .uc-x:hover {
    background: var(--ac);
    color: #fff;
  }
  .uc-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--bd);
  }
  .uc-l {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg2);
    white-space: nowrap;
  }
  .uc-l select {
    font: inherit;
    font-size: 11px;
    max-width: 240px;
    padding: 3px 4px;
    border-radius: 5px;
    border: 1px solid var(--bd);
    background: var(--bg, #fff);
    color: var(--fg);
  }
  .uc-hex {
    width: 64px;
    font-family: ui-monospace, monospace;
    font-size: 11px;
    padding: 3px 5px;
    border-radius: 5px;
    border: 1px solid var(--bd);
    background: var(--bg, #fff);
    color: var(--fg);
  }
  .uc-chk {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg2);
    white-space: nowrap;
  }
  .uc-go {
    font: inherit;
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 6px;
    border: 1px solid var(--ac);
    background: var(--ac);
    color: #fff;
    cursor: pointer;
  }
  .uc-go:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .uc-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }
  .uc-msg {
    padding: 30px 16px;
    text-align: center;
    font-size: 11.5px;
    color: var(--fg3);
  }
  .uc-table {
    border-collapse: collapse;
    font-size: 11px;
    width: 100%;
  }
  .uc-table th {
    position: sticky;
    top: 0;
    background: var(--bg3, #f3f4f6);
    border-bottom: 1px solid var(--bd);
    text-align: left;
    font-weight: 600;
    padding: 4px 8px;
    white-space: nowrap;
  }
  .uc-table td {
    font-family: ui-monospace, monospace;
    font-size: 10.5px;
    padding: 2px 8px;
    border-bottom: 1px solid var(--bd);
    white-space: nowrap;
  }
  .uc-table tbody tr:hover {
    background: var(--bg3, #f3f4f6);
  }
  .uc-foot {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-top: 1px solid var(--bd);
    background: var(--bg3, #f3f4f6);
  }
  .uc-count,
  .uc-status {
    font-size: 11px;
    color: var(--fg3);
  }
  .uc-btn {
    font: inherit;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid var(--bd);
    background: var(--bg2, #fff);
    color: var(--fg);
    cursor: pointer;
  }
  .uc-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .uc-btn.primary {
    background: var(--ac);
    border-color: var(--ac);
    color: #fff;
  }
</style>
