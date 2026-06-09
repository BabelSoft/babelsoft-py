<script lang="ts">
  import type { GridPage, BlockInfo } from "./lib/types";
  import { t, lang } from "./lib/i18n.svelte";
  import SaveDialog from "./lib/components/SaveDialog.svelte";
  import ContextMenu from "./lib/components/ContextMenu.svelte";
  import InfoBar from "./lib/components/InfoBar.svelte";
  import GridHeader from "./lib/components/GridHeader.svelte";
  import PlaneTabs from "./lib/components/PlaneTabs.svelte";
  import StatusBar from "./lib/components/StatusBar.svelte";
  import NavPanel from "./lib/components/NavPanel.svelte";
  import CharacterGrid from "./lib/components/CharacterGrid.svelte";
  import MenuBar from "./lib/components/MenuBar.svelte";
  import BottomPanel from "./lib/components/BottomPanel.svelte";

  let dark = $state(false);
  let grid = $state<GridPage | null>(null);
  let err = $state("");
  let loading = $state(false);
  let plane = $state(0);
  let scroll = $state(0);
  let fsize = $state(16);
  let buf = $state("");
  let mode = $state<"char" | "ncr_hex" | "ncr_dec" | "html" | "ucn">("char");
  let glyph = $state(true);
  let colour = $state(false);
  let gv = $state("");
  let sv = $state("");
  let blocks = $state<BlockInfo[]>([]);
  let sblock = $state("");
  let sr = $state(-1);
  let sc = $state(-1);
  let showLang = $state(false);
  let _navBusy = false;
  let statusMsg = $state("");

  // ── Dialog / context menu state ────────────────────────────────────
  let showSaveDlg = $state(false);
  let ctxShow = $state(false);
  let ctxX = $state(0);
  let ctxY = $state(0);
  let ctxSel = $state(false);
  let _ebTextarea = $state<HTMLTextAreaElement | null>(null);

  function showStatus(msg: string) {
    // StatusBar manages its own auto-dismiss timer via $effect
    statusMsg = msg;
  }

  const PLANES = [
    { id: 0, l: "BMP" },
    { id: 1, l: "SMP" },
    { id: 2, l: "SIP" },
    { id: 3, l: "TIP" },
    { id: 14, l: "SSP" },
    { id: 15, l: "PUA-A" },
    { id: 16, l: "PUA-B" },
  ];
  const planAbbr: Record<number, string> = {};
  PLANES.forEach((p) => (planAbbr[p.id] = p.l));
  const API = "http://127.0.0.1:17890/api";
  async function get<T>(p: string): Promise<T> {
    const r = await fetch(API + p);
    if (!r.ok) throw Error(String(r.status));
    return r.json();
  }

  async function load(np?: number, ns?: number, q?: boolean) {
    if (np != null) plane = np;
    if (ns != null) scroll = ns;
    if (!q) {
      loading = true;
      err = "";
    }
    try {
      grid = await get<GridPage>(`/grid/${plane}?scroll=${scroll}`);
    } catch (e: any) {
      err = e.message;
    } finally {
      if (!q) loading = false;
    }
  }
  async function loadBlocks() {
    if (blocks.length === 0)
      try {
        const data = await get<BlockInfo[]>("/blocks");
        blocks = data.sort((a, b) => a.name.localeCompare(b.name));
      } catch {}
  }
  async function goPlane(p: number) {
    sr = -1;
    sc = -1;
    sblock = "";
    scroll = 0;
    blocks = [];
    await load(p, 0);
    loadBlocks();
  }
  async function nav(dir: number) {
    if (_navBusy) return;
    let ns = Math.max(0, Math.min(grid?.max_scroll ?? 4095, scroll + dir));
    if (ns === scroll) return;
    _navBusy = true;
    await load(undefined, ns, true);
    _navBusy = false;
  }
  async function nblock(dir: number) {
    if (!grid || !blocks.length) {
      await nav(dir * 32);
      return;
    }
    const ps = plane * 0x10000,
      cp = ps + scroll * 16,
      cb = blocks.find((b) => b.start <= cp && b.end >= cp);
    if (cb) {
      const t = blocks[blocks.indexOf(cb) + dir];
      if (t) {
        await load(undefined, Math.floor((t.start - ps) / 16));
        return;
      }
    }
    await nav(dir * 32);
  }
  async function doGo() {
    if (!gv.trim()) return;
    let cp = parseInt(gv.replace(/^(0x|U\+|\$|#)/i, ""), gv.startsWith("#") ? 10 : 16);
    if (isNaN(cp) || cp < 0 || cp > 0x10ffff) return;
    gv = "";
    const np = Math.floor(cp / 0x10000);
    const g = await get<GridPage>(`/grid/${np}/goto/${cp}`);
    if (g.not_found) {
      alert(`U+${cp.toString(16).toUpperCase()} ${t("general.not_assigned")}`);
      return;
    }
    grid = g;
    plane = np;
    scroll = g.scroll_position;
    sr = 0;
    sc = (cp - np * 0x10000) % 16;
  }
  async function doSearch() {
    if (!sv.trim()) return;
    try {
      const r = await get<any[]>(`/search/name?q=${encodeURIComponent(sv.trim())}`);
      if (r.length > 0) {
        const cp = r[0].codepoint;
        sv = "";
        const np = Math.floor(cp / 0x10000);
        const g = await get<GridPage>(`/grid/${np}/goto/${cp}`);
        if (g.not_found) {
          alert(`U+${cp.toString(16).toUpperCase()} ${t("general.not_assigned")}`);
          return;
        }
        grid = g;
        plane = np;
        scroll = g.scroll_position;
        sr = 0;
        sc = (cp - np * 0x10000) % 16;
      } else err = t("general.not_found");
    } catch (e: any) {
      err = e.message;
    }
  }
  async function doBlock() {
    if (!sblock) return;
    const b = blocks.find((x) => x.name === sblock);
    if (!b) return;
    const np = b.plane;
    sr = -1;
    sc = -1;
    grid = await get<GridPage>(`/grid/${np}/goto/${b.start}`);
    plane = np;
    scroll = grid.scroll_position;
  }

  function selectCell(r: number, c: number) {
    sr = r;
    sc = c;
  }
  function addToBuf(r: number, c: number) {
    if (grid) {
      const cell = grid.cells[r]?.[c];
      if (cell && cell.codepoint > 0) buf += String.fromCodePoint(cell.codepoint);
    }
  }
  function conv(): string {
    if (!buf) return "";
    const a = [...buf];
    if (mode === "ncr_hex") return a.map((c) => `&#x${c.codePointAt(0)!.toString(16).toUpperCase()};`).join("");
    if (mode === "ncr_dec") return a.map((c) => `&#${c.codePointAt(0)!};`).join("");
    if (mode === "html") return a.map((c) => (c.codePointAt(0)! > 127 ? `&#x${c.codePointAt(0)!.toString(16).toUpperCase()};` : c)).join("");
    if (mode === "ucn")
      return a
        .map((c) => (c.codePointAt(0)! <= 0xffff ? `\\u${c.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}` : `\\U${c.codePointAt(0)!.toString(16).toUpperCase().padStart(8, "0")}`))
        .join("");
    return buf;
  }

  /** Switch edit buffer mode: revert to char, then convert to new format */
  function changeMode(m: typeof mode) {
    if (mode === m) return;
    if (buf) buf = revertToChar(buf, mode);
    mode = m;
    if (buf) buf = conv();
  }

  /** Parse buffer back to raw characters from the given mode */
  function revertToChar(text: string, from: typeof mode): string {
    if (from === "char") return text;
    if (from === "ncr_hex") {
      return text.replace(/&#x([0-9A-Fa-f]+);/g, (_, h) => {
        const cp = parseInt(h, 16);
        return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
      });
    }
    if (from === "ncr_dec") {
      return text.replace(/&#(\d+);/g, (_, d) => {
        const cp = parseInt(d, 10);
        return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
      });
    }
    if (from === "html") {
      return text
        .replace(/&#x([0-9A-Fa-f]+);/g, (_, h) => {
          const cp = parseInt(h, 16);
          return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
        })
        .replace(/&#(\d+);/g, (_, d) => {
          const cp = parseInt(d, 10);
          return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
        });
      // Named entities handled by browser — keep as-is for now
    }
    if (from === "ucn") {
      return text.replace(/\\[uU]([0-9A-Fa-f]{4,8})/g, (_, h) => {
        const cp = parseInt(h, 16);
        return cp > 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : "\ufffd";
      });
    }
    return text;
  }

  // ── Edit Buffer operations ──────────────────────────────────────────

  /** Copy plain text (current mode conversion) to clipboard */
  async function copyPlain() {
    if (!buf) return;
    try {
      await navigator.clipboard.writeText(conv());
      showStatus(t("status.copied"));
    } catch {
      showStatus(t("status.copy_failed"));
    }
  }

  /** Copy as RTF (with font metadata) to clipboard */
  async function copyRtf() {
    if (!buf) return;
    try {
      const text = conv();
      const rtf = buildRtf(text);
      const blob = new Blob([rtf], { type: "text/rtf" });
      const plainBlob = new Blob([text], { type: "text/plain" });
      const item = new ClipboardItem({ "text/rtf": blob, "text/plain": plainBlob });
      await navigator.clipboard.write([item]);
      showStatus(t("status.copied"));
    } catch {
      try {
        await navigator.clipboard.writeText(conv());
        showStatus(t("status.copied"));
      } catch {
        showStatus(t("status.copy_failed"));
      }
    }
  }

  /** Cut plain text: copy then clear */
  async function cutPlain() {
    await copyPlain();
    buf = "";
  }

  /** Cut RTF: copy RTF then clear */
  async function cutRtf() {
    await copyRtf();
    buf = "";
  }

  /** Paste from clipboard into edit buffer */
  async function doPaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        buf += text;
        showStatus(t("status.copied"));
      }
    } catch {
      showStatus(t("status.copy_failed"));
    }
  }

  /** Clear the edit buffer */
  function doClear() {
    buf = "";
  }

  // ── Save / Context menu triggers ───────────────────────────────────

  function openSaveDlg() {
    if (!buf) return;
    showSaveDlg = true;
  }

  function openCtxMenu(e: MouseEvent, ta: HTMLTextAreaElement) {
    e.preventDefault();
    _ebTextarea = ta;
    ctxSel = ta.selectionStart !== ta.selectionEnd;
    ctxX = Math.max(0, Math.min(e.clientX, window.innerWidth - 240));
    ctxY = e.clientY;
    ctxShow = true;
  }

  /** Build a minimal RTF string wrapping the given text with current font settings */
  function buildRtf(text: string): string {
    const escaped = text.replace(/\\/g, "\\\\").replace(/\{/g, "\\{").replace(/\}/g, "\\}").replace(/\n/g, "\\par\n").replace(/\r/g, "");
    let body = "";
    for (const ch of escaped) {
      const cp = ch.codePointAt(0) ?? 63;
      if (cp > 127) {
        body += `\\u${cp}?`;
      } else {
        body += ch;
      }
    }
    const fontSize = Math.round(fsize * 2);
    return [
      "{\\rtf1\\ansi\\ansicpg1252\\deff0\\nouicompat",
      "{\\fonttbl{\\f0\\fswiss\\fcharset0 Arial;}{\\f1\\fnil\\fcharset134 SimSun;}{\\f2\\fnil\\fcharset128 MS Mincho;}{\\f3\\fnil\\fcharset129 Malgun Gothic;}}",
      "{\\colortbl ;\\red0\\green0\\blue0;}",
      "\\viewkind4\\uc1\\pard\\f0\\fs" + fontSize + " ",
      body,
      "\\par}",
    ].join("\n");
  }

  function selCp() {
    if (sr < 0 || !grid) return null;
    return grid.cells[sr]?.[sc]?.codepoint ?? null;
  }
  function selName() {
    if (sr < 0 || !grid) return "";
    return grid.cells[sr]?.[sc]?.char_name || "";
  }
  let selInfo = $derived.by(() => {
    const cp = selCp();
    if (cp != null && cp >= 0) {
      const cell = grid!.cells[sr]?.[sc];
      const reserved = cell?.reserved;
      const nm = reserved ? "<reserved>" : selName() || `U+${cp.toString(16).toUpperCase()}`;
      return {
        hex: cp
          .toString(16)
          .toUpperCase()
          .padStart(cp > 0xffff ? 5 : 4, "0"),
        char: String.fromCodePoint(cp),
        dec: String(cp),
        name: nm,
      };
    }
    return null;
  });

  function onKey(e: KeyboardEvent) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
    if (e.key === "ArrowUp") {
      if (sr > 0) sr--;
      else if (scroll > 0) {
        sr = 0;
        nav(-1);
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (sr < 7) sr++;
      else if (scroll < (grid?.max_scroll ?? 4095)) {
        sr = 7;
        nav(1);
      }
      e.preventDefault();
    } else if (e.key === "ArrowLeft") {
      if (sc > 0) sc--;
      else if (sr > 0) {
        sr--;
        sc = 15;
      } else if (scroll > 0) {
        sr = 0;
        sc = 15;
        nav(-1);
      }
      e.preventDefault();
    } else if (e.key === "ArrowRight") {
      if (sc < 15) sc++;
      else if (sr < 7) {
        sr++;
        sc = 0;
      } else if (scroll < (grid?.max_scroll ?? 4095)) {
        sr = 7;
        sc = 0;
        nav(1);
      }
      e.preventDefault();
    } else if (e.key === "Enter" && sr >= 0) {
      selectCell(sr, sc);
      addToBuf(sr, sc);
      e.preventDefault();
    } else if (e.key === "PageUp") {
      nav(-8);
      e.preventDefault();
    } else if (e.key === "PageDown") {
      nav(8);
      e.preventDefault();
    } else if (e.key === "Escape") {
      // MenuBar handles its own Escape closing
    } else if (e.key === "F4") {
      e.preventDefault();
      if (e.ctrlKey && e.shiftKey) cutRtf();
      else if (e.ctrlKey) copyRtf();
      else if (e.shiftKey) cutPlain();
      else copyPlain();
    }
  }

  function onMenuAction(label: string) {
    if (label === t("view.toggle_theme")) dark = !dark;
    else if (label === t("edit.clear")) doClear();
    else if (label === t("edit.copy_plain")) copyPlain();
    else if (label === t("edit.copy_rtf")) copyRtf();
    else if (label === t("edit.cut_plain")) cutPlain();
    else if (label === t("edit.cut_rtf")) cutRtf();
    else if (label === t("edit.paste")) doPaste();
    else if (label === t("edit.save")) openSaveDlg();
    else if (label === t("edit.glyph_mode")) glyph = true;
    else if (label === t("edit.text_mode")) glyph = false;
    else if (label === t("edit.colour_glyphs")) colour = !colour;
    else if (label === t("edit.char")) changeMode("char");
    else if (label === t("edit.ncr_hex")) changeMode("ncr_hex");
    else if (label === t("edit.ncr_dec")) changeMode("ncr_dec");
    else if (label === t("edit.html")) changeMode("html");
    else if (label === t("edit.ucn")) changeMode("ucn");
  }

  // Start Python backend via Tauri (no-op in browser dev mode)
  async function startBackend() {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("start_backend");
    } catch {}
  }

  load();
  loadBlocks();
  startBackend();
</script>

<svelte:window onkeydown={onKey} />

<div class="app" class:dark>
  <MenuBar {dark} {showLang} {onMenuAction} onDarkToggle={() => (dark = !dark)} onToggleLang={() => (showLang = !showLang)} onCloseLang={() => (showLang = false)} />

  <PlaneTabs {plane} planes={PLANES} onChange={goPlane} />

  <div class="main">
    <div class="gw">
      <GridHeader {loading} {err} {grid} />
      <CharacterGrid {grid} {plane} {sr} {sc} onSelect={selectCell} onAddToBuffer={addToBuf} onWheel={(deltaY: number) => nav(deltaY > 0 ? 1 : -1)} />
    </div>

    <NavPanel
      maxScroll={grid?.max_scroll ?? 4095}
      {scroll}
      onScrollInput={(v) => {
        scroll = v;
        load(undefined, v, true);
      }}
      onPlaneStart={() => goPlane(0)}
      onPlaneEnd={() => goPlane(16)}
      onPrevBlock={() => nblock(-1)}
      onNextBlock={() => nblock(1)}
      onPageUp={() => nav(-8)}
      onPageDown={() => nav(8)}
      onRowStart={() => {
        sr = 0;
      }}
      onRowEnd={() => {
        sr = 7;
      }}
      onRandom={() => {
        const cp = Math.floor(Math.random() * 0x110000);
        gv = cp.toString(16).toUpperCase();
        doGo();
      }}
    />
  </div>

  <InfoBar {selInfo} />

  <BottomPanel
    {buf}
    {mode}
    {glyph}
    {colour}
    {fsize}
    {gv}
    {sv}
    {blocks}
    {sblock}
    editVisible={true}
    onBufChange={(v: string) => (buf = v)}
    onSblockChange={(v: string) => (sblock = v)}
    onGvChange={(v: string) => (gv = v)}
    onSvChange={(v: string) => (sv = v)}
    onBlockSelect={doBlock}
    onSearch={doSearch}
    onGoto={doGo}
    onFontSizeChange={(v: number) => {
      fsize = v;
      load();
    }}
    onModeChange={(m: string) => changeMode(m as any)}
    onGlyphToggle={(v: boolean) => (glyph = v)}
    onColourToggle={(v: boolean) => (colour = v)}
    onCopy={copyPlain}
    onCut={cutPlain}
    onClear={doClear}
    onSave={openSaveDlg}
    onHideToggle={() => {}}
    onContextMenu={(e: MouseEvent) => openCtxMenu(e, e.currentTarget as HTMLTextAreaElement)}
  />

  <StatusBar
    {statusMsg}
    {selInfo}
    {grid}
    planeLabel={PLANES.find((p) => p.id === plane)?.l || ""}
    {fsize}
    firstRowBase={grid ? plane * 0x10000 + (grid.row_bases[0] ?? 0) : null}
    onStatusClear={() => (statusMsg = "")}
  />

  <SaveDialog
    show={showSaveDlg}
    {buf}
    {conv}
    {fsize}
    onClose={() => (showSaveDlg = false)}
    onSaved={() => {
      showSaveDlg = false;
      showStatus(t("status.copied"));
    }}
  />

  <ContextMenu
    show={ctxShow}
    x={ctxX}
    y={ctxY}
    hasSel={ctxSel}
    {buf}
    textarea={_ebTextarea}
    onClose={() => {
      ctxShow = false;
      _ebTextarea = null;
    }}
    onBufChange={(v: string) => (buf = v)}
  />
</div>

<style>
  :global(body) {
    margin: 0;
    overflow: hidden;
    font-family: system-ui, sans-serif;
    font-size: 13px;
  }
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    outline: none;
    --bg: #f8f9fa;
    --bg2: #fff;
    --bg3: #e9ecef;
    --fg: #212529;
    --fg2: #495057;
    --fg3: #868e96;
    --bd: #dee2e6;
    --ac: #5c7cfa;
    --sh: 0 1px 3px rgba(0, 0, 0, 0.08);
    --celbg: #fff;
    --celh: #f1f3f5;
    --sc: #adb5bd;
    --nonchar: #111;
  }
  .app.dark {
    --bg: #1a1b2e;
    --bg2: #232440;
    --bg3: #2d2e4a;
    --fg: #e4e6f0;
    --fg2: #b0b3cc;
    --fg3: #6e7191;
    --bd: #363858;
    --ac: #818cf8;
    --sh: 0 1px 3px rgba(0, 0, 0, 0.3);
    --celbg: #1e1f36;
    --celh: #2a2b48;
    --sc: #4a4b6a;
    --nonchar: #ddd;
  }
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  :global(button) {
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    border: none;
    border-radius: 8px;
    transition: all 0.15s;
  }
  :global(input),
  :global(select),
  :global(textarea) {
    font-family: inherit;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 5px 8px;
    outline: none;
    transition: border-color 0.15s;
  }
  :global(input:focus),
  :global(select:focus),
  :global(textarea:focus) {
    border-color: var(--ac);
    box-shadow: 0 0 0 3px rgba(92, 124, 250, 0.12);
  }
  :global(fieldset) {
    border: 1px solid var(--bd);
    border-radius: 10px;
    padding: 4px 10px 6px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  :global(fieldset legend) {
    font-size: 10px;
    color: var(--fg3);
    padding: 0 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .main {
    flex: 1;
    display: flex;
    overflow: visible;
    min-height: 0;
    background: var(--bg);
  }
  .gw {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 6px 10px;
    gap: 0;
    min-height: 0;
  }
</style>
