<script lang="ts">
  import { untrack } from "svelte";
  import type { GridPage, BlockInfo } from "./lib/types";
  import { API_BASE } from "./lib/api";
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
  import UnicodeDialog from "./lib/components/UnicodeDialog.svelte";
  import CharacterPropertiesDialog from "./lib/components/CharacterPropertiesDialog.svelte";
  import EmojiLookupDialog from "./lib/components/EmojiLookupDialog.svelte";
  import OpenTypeTestDialog from "./lib/components/OpenTypeTestDialog.svelte";
  import FontOverviewDialog from "./lib/components/FontOverviewDialog.svelte";
  import CompositeFontDialog from "./lib/components/CompositeFontDialog.svelte";
  import {
    fontStack,
    stackFamily,
    loadUserFonts,
    applyStack,
    clearStack,
    inject,
  } from "./lib/fontStack.svelte";
  import { startCoverageScan, startScanTicker } from "./lib/coverage.svelte";
  import { altRepresentation, charRef, revertToChars } from "./lib/altRepr";
  import FontQualityDialog from "./lib/components/FontQualityDialog.svelte";
  import ExportGlyphsDialog from "./lib/components/ExportGlyphsDialog.svelte";
  import ColourCodingDialog from "./lib/components/ColourCodingDialog.svelte";
  import BookmarksDialog from "./lib/components/BookmarksDialog.svelte";
  import HelpDialog from "./lib/components/HelpDialog.svelte";
  import LookupDialog, {
    type LookupKind,
  } from "./lib/components/LookupDialog.svelte";
  import UcdDialog from "./lib/components/UcdDialog.svelte";
  import {
    addBookmark,
    clearBookmarks,
    removeBookmark,
    bookmarks as bookmarkList,
    hex as bmHex,
  } from "./lib/bookmarks.svelte";
  import {
    settings,
    applySettings,
    saveSettings,
    resetSettings,
    GRID_SIZES,
    GRID_POINT_SIZES,
    gridPxFor,
    ALT_REPRS,
    CJKV_READINGS,
    TANGUT_READINGS,
    COLOUR_CODINGS,
    type EditMode,
  } from "./lib/settings.svelte";
  import {
    ALT_LABELS as ALT_KEYS,
    CJKV_LABELS as CJKV_KEYS,
    TANGUT_LABELS as TANGUT_KEYS,
    COLOUR_LABELS as COLOUR_KEYS,
    POPUP_LABELS as POPUP_KEYS,
  } from "./lib/i18n.svelte";

  let dark = $state(false);
  let grid = $state<GridPage | null>(null);
  let err = $state("");
  let loading = $state(false);
  let plane = $state(0);
  let scroll = $state(0);
  let buf = $state("");
  // Edit-buffer state, initialised from the persisted settings and mirrored
  // back by the effect below — the original keeps the same four in its
  // registry (Rendering Mode, Colour Rendering, Map Mode, Show Edit Buffer).
  let mode = $state<EditMode>(settings.editMode);
  let glyph = $state(settings.glyphMode);
  let colour = $state(settings.colourGlyphs);
  let editVisible = $state(settings.editBufferVisible);
  let gv = $state("");
  let sv = $state("");
  let blocks = $state<BlockInfo[]>([]);
  /**
   * The block list in the order Options ▸ Unicode Blocks asks for:
   * alphabetical (the original's default, `eRegistrySortBlocks`) or code point
   * order.  The API already returns code point order, so the sort is cheap.
   */
  const blocksShown = $derived.by(() =>
    settings.blocksSorted
      ? [...blocks].sort((a, b) =>
          a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
        )
      : blocks,
  );
  let sblock = $state("");
  let sr = $state(-1);
  let sc = $state(-1);
  let showLang = $state(false);
  let _navBusy = false;
  let statusMsg = $state("");
  let _sresults = $state<{ codepoint: number; name: string }[]>([]);
  let _sidx = $state(-1);
  let _showResults = $state(false);
  let _lastQuery = $state("");
  let _normalizedQuery = $state("");
  let _searchProgress = $state(0);
  let _searchLoading = $state(false);
  let _searchComplete = $state(false);
  let _filterNoBlock = $derived(!settings.showReservedRanges);
  // ── Dialog / context menu state ────────────────────────────────────
  let showSaveDlg = $state(false);
  let showUnicode = $state(false);
  let showCharProps = $state(false);
  let showEmojiLookup = $state(false);
  let showOpenTypeTest = $state(false);
  let showFontOverview = $state(false);
  let showCompositeFont = $state(false);
  let showFontQuality = $state(false);
  let showExportGlyphs = $state(false);
  let showColourConfig = $state(false);
  let showBookmarks = $state(false);
  let showHelp = $state(false);
  let showLookup = $state(false);
  let lookupKind = $state<LookupKind>("pinyin");
  let showUcd = $state(false);
  // Tools ▸ Supplementary Information now lives in Character Properties as its
  // own page (the original's CJKV / Tangut / hieroglyph dialogs were all "more
  // about this character").
  let charPropsView = $state<
    "props" | "extended" | "ideographic" | "history" | "supplementary"
  >("props");
  let charPropsCp = $state(-1);
  let ctxShow = $state(false);
  let ctxX = $state(0);
  let ctxY = $state(0);
  let ctxSel = $state(false);
  let _ebTextarea = $state<HTMLTextAreaElement | null>(null);

  // ── Font stack (character grid + edit buffer share it) ───────────────
  // The CompositeFontDialog owns the entries/CSS; this derived value is the
  // `font-family` list both surfaces render with. It is empty until the stack
  // is applied, so the default styling is untouched out of the box.
  const stack = $derived(fontStack.applied ? stackFamily(fontStack.items) : "");

  // The grid font size lives in the font stack (Ctrl+wheel over the grid).
  // `null` = never chosen → the Medium row of the View size column, which is
  // the original's default (`GridPointSize[2][1]` = 16pt).  `fsize` is the
  // number the status bar, the RTF export and Copy Glyph read.
  const fsize = $derived(fontStack.gridSize ?? gridPxFor(2, settings.viewSize));

  // Code points the Export Font Glyphs dialog starts from: the selected cell,
  // or nothing (the dialog then keeps its own default range).
  const exportCps = $derived.by(() => {
    const cp = selCp();
    return cp != null && cp >= 0 ? [cp] : [];
  });

  // Ctrl+wheel zoom.  One wheel notch = one pixel; `deltaY > 0` (scroll down)
  // shrinks.  Clamped so the size never leaves a sane, usable range.
  const MIN_SIZE = 8;
  const MAX_SIZE = 96;
  /** Where a zoom starts from when nothing has been set yet. */
  function currentGridSize(): number {
    if (fontStack.gridSize != null) return fontStack.gridSize;
    const cell = document.querySelector(".gc2");
    const px = cell ? parseFloat(getComputedStyle(cell).fontSize) : NaN;
    return Number.isFinite(px) ? px : 16;
  }
  function zoomGrid(deltaY: number) {
    const next = Math.round(currentGridSize()) - Math.sign(deltaY);
    const size = Math.max(MIN_SIZE, Math.min(MAX_SIZE, next));
    fontStack.gridSize = size;
    settings.gridSize = size;
  }

  // ── Settings ⇄ stores ───────────────────────────────────────────────
  // `settings` is the single source of truth: every change is mirrored into
  // the rendering stores here and persisted (debounced, so dragging a slider
  // does not hammer localStorage).
  let _saveTimer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    // Touch every persisted field so the effect re-runs on any change.
    void JSON.stringify(settings);
    applySettings();
    clearTimeout(_saveTimer);
    _saveTimer = setTimeout(saveSettings, 250);
  });

  // The Edit-menu state is *driven* locally (the menu, the bottom panel and the
  // keyboard all mutate these four), so push it into the persisted settings
  // rather than the other way round — one writer, no feedback loop.
  $effect(() => {
    settings.glyphMode = glyph;
    settings.colourGlyphs = colour;
    settings.editMode = mode;
    settings.editBufferVisible = editVisible;
  });

  /**
   * Nav panel ▸ IVS — `OnButtonUnicodeVariationSequences` → `CDialogUVS`.
   *
   * The original opens a dedicated window, but every sequence it lists is
   * already part of Character Properties, so the button goes there instead
   * (the rows are clickable and insert the sequence into the buffer).
   */
  function openUvs(): void {
    const cp = selCp();
    if (cp == null || cp < 0) {
      showStatus(t("general.select_char"));
      return;
    }
    charPropsCp = cp;
    charPropsView = "props";
    showCharProps = true;
  }

  /** Tools ▸ … Lookup — all five modes share one window. */
  function openLookup(kind: LookupKind) {
    lookupKind = kind;
    showLookup = true;
  }

  /** Tools ▸ Supplementary Information — CJKV / Tangut / hieroglyph. */
  function openSupplementaryInfo(): void {
    const cp = selCp();
    if (cp == null || cp < 0) {
      showStatus(t("general.select_char"));
      return;
    }
    charPropsCp = cp;
    charPropsView = "supplementary";
    showCharProps = true;
  }

  /**
   * Tools ▸ Generate Full UCD XML Data — `OnToolsXMLData` writes
   * `ucd.nounihan.flat.<product>.xml` for the whole repertoire.  Here the
   * browser downloads what the backend streams for the BMP plus the
   * supplementary planes' CJK/Hangul runs.
   */
  async function generateUcdXml(): Promise<void> {
    showStatus("Generating UCD XML…");
    try {
      const r = await fetch(
        `${API}/ucd/xml?start=0&end=1114111&all_cjk=false&all_hangul=false`,
      );
      if (!r.ok) throw new Error(String(r.status));
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "ucd.nounihan.flat.babelmap.xml";
      a.click();
      URL.revokeObjectURL(a.href);
      showStatus("UCD XML saved");
    } catch {
      showStatus("UCD XML generation failed");
    }
  }

  /** File ▸ Close to System Tray / Exit — both are window-shell operations. */
  async function windowAction(kind: "tray" | "exit"): Promise<void> {
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const win = getCurrentWindow();
      if (kind === "tray") await win.hide();
      else await win.close();
      return;
    } catch {
      // Browser dev mode: nothing to hide or close.
    }
    showStatus(
      kind === "tray"
        ? "Close to tray needs the desktop shell"
        : "Exit needs the desktop shell",
    );
  }

  /** Fonts ▸ Single Font / Composite Font. */
  function setFontMode(mode: "single" | "composite") {
    settings.fontMode = mode;
    fontStack.mode = mode;
    if (mode === "single") {
      // Single mode bypasses the stack entirely: apply it so the grid and the
      // buffer immediately use the chosen family, and drop the injected CSS.
      fontStack.applied = true;
      inject("");
      showStatus(`Single font: ${settings.singleFamily}`);
    } else {
      // Back to composite: apply the stack only if it actually has content,
      // otherwise the grid would inherit a bare "serif" and lose its default.
      if (
        fontStack.blocks.length ||
        fontStack.items.some((i) => i.enabled && (i.family || i.userId))
      ) {
        applyStack();
      } else {
        clearStack();
      }
      showStatus("Composite font");
    }
  }

  /** Fonts ▸ Grid Font Size ▸ (one of the five presets). */
  function setGridSizeIndex(i: number) {
    if (i < 0 || i >= GRID_SIZES.length) return;
    const size = gridPxFor(i, settings.viewSize);
    settings.gridSize = size;
    fontStack.gridSize = size;
  }

  /**
   * View ▸ Medium Size / Large Size.
   *
   * These pick the *column* of the original's `GridPointSize[][2]` table, so
   * the same Fonts ▸ Grid Font Size row renders at a different point size (the
   * Medium column is 2pt smaller than the Large one).  A custom Ctrl+wheel
   * zoom is carried over by re-applying the same relative step.
   */
  function setViewSize(v: "medium" | "large") {
    if (settings.viewSize === v) return;
    const row = GRID_POINT_SIZES.findIndex(
      (r) => r[settings.viewSize === "large" ? 0 : 1] === settings.gridSize,
    );
    settings.viewSize = v;
    if (row >= 0) {
      const size = gridPxFor(row, v);
      settings.gridSize = size;
      fontStack.gridSize = size;
    }
    showStatus(v === "large" ? "Large size" : "Medium size");
  }

  /** View ▸ Keep on Top — `eRegistryStayontop`; the desktop shell owns it. */
  async function setKeepOnTop(on: boolean) {
    settings.keepOnTop = on;
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      await getCurrentWindow().setAlwaysOnTop(on);
    } catch {
      // Browser dev mode: there is no window to pin, so only remember it.
    }
    showStatus(on ? "Keep on top: on" : "Keep on top: off");
  }

  // ── Edit ▸ Copy Glyph / Copy Glyph Outline ──────────────────────────
  //
  // `CDialogMap::CopyGlyph(bOutline)` draws the current character into a
  // 10×-cell bitmap and puts it on the Clipboard, stroked instead of filled
  // when `bOutline` is set.  The browser's canvas is the equivalent renderer
  // and it uses the very same font stack as the grid, so what is copied is
  // what is on screen.
  async function copyGlyph(outline: boolean): Promise<void> {
    const cp = selCp();
    if (cp == null || cp < 0) {
      showStatus(t("general.select_char"));
      return;
    }
    const ch = String.fromCodePoint(cp);
    const px = Math.max(12, Math.round(fsize)) * 10; // m_nGlyphSize * 10
    const family = stack || settings.singleFamily || "serif";
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.font = `${px}px ${family}`;
    const m = ctx.measureText(ch);
    const pad = Math.ceil(px * 0.15);
    const w = Math.max(1, Math.ceil(m.width) + pad * 2);
    const h = Math.max(1, Math.ceil(px * 1.35) + pad * 2);
    canvas.width = w;
    canvas.height = h;
    ctx.font = `${px}px ${family}`;
    ctx.textBaseline = "alphabetic";
    const baseline = h - pad - Math.ceil(px * 0.28);
    if (outline) {
      ctx.lineWidth = Math.max(1, Math.round(px / 32));
      ctx.strokeStyle = "#000000";
      ctx.strokeText(ch, pad, baseline);
    } else {
      ctx.fillStyle = "#000000";
      ctx.fillText(ch, pad, baseline);
    }
    const blob = await new Promise<Blob | null>((res) =>
      canvas.toBlob(res, "image/png"),
    );
    if (!blob) return;
    try {
      const ClipboardItemCtor = (globalThis as any).ClipboardItem;
      if (!ClipboardItemCtor || !navigator.clipboard?.write) throw new Error();
      await navigator.clipboard.write([
        new ClipboardItemCtor({ "image/png": blob }),
      ]);
      showStatus(
        outline
          ? `Copied glyph outline U+${bmHex(cp)}`
          : `Copied glyph U+${bmHex(cp)}`,
      );
    } catch {
      showStatus("This browser cannot copy images to the clipboard");
    }
  }

  function showStatus(msg: string) {
    // StatusBar manages its own auto-dismiss timer via $effect
    statusMsg = msg;
  }

  // ── Plane tabs ──────────────────────────────────────────────────────
  // Labels are sourced ENTIRELY from the backend's authoritative plane-name
  // data (babelsoft.unicode.core → Unicode.get_plane_abbreviation), fetched
  // from /api/unicode/planes.  Nothing is hardcoded: the tab bar shows a
  // loading placeholder (in PlaneTabs) until the data arrives.
  let planeMeta = $state<
    { plane: number; name: string; abbreviation: string; reserved: boolean }[]
  >([]);
  let PLANES = $derived.by(() => {
    if (planeMeta.length === 0) return [];
    // View ▸ Hide Reserved Planes (`eRegistryShowReservedPlanes`): off by
    // default, which is what leaves the seven assigned planes on the bar.
    if (!settings.showReservedPlanes) {
      return planeMeta
        .filter((m) => !m.reserved && m.abbreviation)
        .map((m) => ({ id: m.plane, l: m.abbreviation }));
    }
    return Array.from({ length: 17 }, (_, i) => {
      const m = planeMeta.find((x) => x.plane === i);
      return { id: i, l: m && m.abbreviation ? m.abbreviation : `Plane ${i}` };
    });
  });
  const planAbbr: Record<number, string> = {};
  $effect(() => {
    PLANES.forEach((p) => (planAbbr[p.id] = p.l));
  });
  const API = "http://127.0.0.1:18080/api";
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
      grid = await get<GridPage>(
        `/grid/${plane}?scroll=${scroll}&filter_no_block=${_filterNoBlock}${gridAttrs()}`,
      );
    } catch (e: any) {
      err = e.message;
    } finally {
      if (!q) loading = false;
    }
  }

  /**
   * Colour coding and rotated vertical scripts both need the cell's Unicode
   * properties, which the grid endpoint only computes when asked.
   */
  function gridAttrs(): string {
    return settings.colourCoding !== "none" || settings.rotateVertical
      ? "&attrs=1"
      : "";
  }

  // Reload the page when a setting that changes the cells themselves changes.
  $effect(() => {
    void settings.colourCoding;
    void settings.rotateVertical;
    untrack(() => load(undefined, undefined, true));
  });
  async function loadBlocks() {
    if (blocks.length === 0)
      try {
        const data = await get<BlockInfo[]>("/blocks");
        blocks = data.sort((a, b) => a.name.localeCompare(b.name));
      } catch {}
  }
  async function loadPlanes() {
    try {
      const data = await get<{
        planes: {
          plane: number;
          name: string;
          abbreviation: string;
          reserved: boolean;
        }[];
      }>("/unicode/planes");
      planeMeta = data.planes ?? [];
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
    // Options ▸ Go To Code Points decides the base; an explicit `$`/`#`/`0x`
    // prefix still wins, exactly like the original's `$%04X` / `#%d` field.
    const raw = gv.trim();
    const decimal = /^#/.test(raw)
      ? true
      : /^(\$|0x|U\+)/i.test(raw)
        ? false
        : !settings.gotoHex;
    const cp = parseInt(raw.replace(/^(0x|U\+|\$|#)/i, ""), decimal ? 10 : 16);
    if (isNaN(cp) || cp < 0 || cp > 0x10ffff) return;
    gv = "";
    await gotoCP(cp);
  }
  async function doSearch() {
    if (!sv.trim()) return;
    const q = sv.trim();

    // Same query as last time → just advance to next result
    if (q === _lastQuery && _sresults.length > 0) {
      _sidx = (_sidx + 1) % _sresults.length;
      _showResults = true;
      await gotoCP(_sresults[_sidx].codepoint);
      return;
    }

    // New query → fresh search (streaming)
    _lastQuery = q;
    _showResults = false;
    _sresults = [];
    _sidx = -1;
    _normalizedQuery = "";
    _searchProgress = 0;
    _searchLoading = true;
    _searchComplete = false;

    try {
      const url = `${API}/search/name/stream?q=${encodeURIComponent(q)}&limit=200&start_cp=0&filter_no_block=${_filterNoBlock}`;
      const response = await fetch(url);
      if (!response.ok) throw Error(String(response.status));
      const reader = response.body?.getReader();
      if (!reader) throw Error("Stream not supported");

      const decoder = new TextDecoder();
      let buffer = "";
      let firstResult = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);

          if (payload === "[DONE]") {
            _searchLoading = false;
            if (_sresults.length === 0) showStatus(t("general.not_found"));
            return;
          }

          if (payload.startsWith("QUERY ")) {
            _normalizedQuery = JSON.parse(payload.slice(6));
            continue;
          }

          if (payload.startsWith("PROGRESS ")) {
            _searchProgress = parseFloat(payload.slice(9));
            if (_searchProgress >= 100) _searchComplete = true;
            continue;
          }

          try {
            const item = JSON.parse(payload) as {
              codepoint: number;
              name: string;
            };
            _sresults = [..._sresults, item];
            if (firstResult) {
              firstResult = false;
              _sidx = 0;
              _showResults = true;
              await gotoCP(item.codepoint);
            }
          } catch {
            /* skip malformed */
          }
        }
      }

      // Flush remaining buffer
      if (buffer.startsWith("data: ")) {
        const payload = buffer.slice(6);
        if (payload !== "[DONE]" && !payload.startsWith("QUERY ")) {
          try {
            const item = JSON.parse(payload) as {
              codepoint: number;
              name: string;
            };
            _sresults = [..._sresults, item];
            if (firstResult) {
              _sidx = 0;
              _showResults = true;
              await gotoCP(item.codepoint);
            }
          } catch {
            /* skip */
          }
        }
      }

      if (_sresults.length === 0) showStatus(t("general.not_found"));
    } catch (e: any) {
      _searchLoading = false;
      showStatus(e.message);
    }
  }

  async function loadMoreResults() {
    if (_searchLoading || _searchComplete || _sresults.length === 0) return;
    const lastCp = _sresults[_sresults.length - 1].codepoint;
    _searchLoading = true;
    try {
      const url = `${API}/search/name/stream?q=${encodeURIComponent(_lastQuery)}&limit=200&start_cp=${lastCp}&filter_no_block=${_filterNoBlock}`;
      const response = await fetch(url);
      if (!response.ok) throw Error(String(response.status));
      const reader = response.body?.getReader();
      if (!reader) throw Error("Stream not supported");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);

          if (payload === "[DONE]") {
            _searchLoading = false;
            return;
          }

          if (payload.startsWith("PROGRESS ")) {
            _searchProgress = parseFloat(payload.slice(9));
            if (_searchProgress >= 100) _searchComplete = true;
            continue;
          }

          // Skip QUERY on subsequent loads
          if (payload.startsWith("QUERY ")) continue;

          try {
            const item = JSON.parse(payload) as {
              codepoint: number;
              name: string;
            };
            // Avoid duplicates from wrap-around
            if (
              _sresults.length > 0 &&
              item.codepoint <= _sresults[_sresults.length - 1].codepoint
            )
              continue;
            _sresults = [..._sresults, item];
          } catch {
            /* skip */
          }
        }
      }
    } catch (e: any) {
      _searchLoading = false;
      showStatus(e.message);
    }
  }

  async function doSearchPrev() {
    if (_sresults.length === 0) {
      doSearch();
      return;
    }
    _sidx = _sidx <= 0 ? _sresults.length - 1 : _sidx - 1;
    await gotoCP(_sresults[_sidx].codepoint);
  }
  async function doSearchNext() {
    if (_sresults.length === 0) {
      doSearch();
      return;
    }
    _sidx = (_sidx + 1) % _sresults.length;
    await gotoCP(_sresults[_sidx].codepoint);
  }
  function onSearchResultClick(cp: number) {
    // Find the index of the clicked result
    const idx = _sresults.findIndex((r) => r.codepoint === cp);
    if (idx >= 0) _sidx = idx;
    gotoCP(cp);
  }
  function onDismissResults() {
    _showResults = false;
  }
  async function gotoCP(cp: number) {
    const np = Math.floor(cp / 0x10000);
    const g = await get<GridPage>(
      `/grid/${np}/goto/${cp}?filter_no_block=${_filterNoBlock}${gridAttrs()}`,
    );
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

  // ── Go to Han Ideograph ──────────────────────────────────────────
  async function doGotoHan() {
    const ref = prompt(
      t("find.goto_han") +
        " — " +
        (lang.v === "zh" ? "输入源引用" : "Enter Source Reference"),
    );
    if (!ref?.trim()) return;
    try {
      const r = await get<any[]>(
        `/search/han_source?q=${encodeURIComponent(ref.trim())}&limit=50`,
      );
      if (r.length > 0) {
        sv = "";
        _sresults = r.map((x: any) => ({
          codepoint: x.codepoint,
          name: x.name,
        }));
        _sidx = 0;
        _showResults = true;
        await gotoCP(_sresults[0].codepoint);
      } else alert(t("general.not_found"));
    } catch (e: any) {
      err = e.message;
    }
  }

  // ── Locate Character ─────────────────────────────────────────────
  async function doLocateChar() {
    if (!buf) return;
    const cp = [...buf][0]?.codePointAt(0);
    if (cp == null || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) return;
    sv = "";
    await gotoCP(cp);
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
      if (cell && cell.codepoint > 0)
        buf += String.fromCodePoint(cell.codepoint);
    }
  }
  function conv(): string {
    if (!buf) return "";
    if (mode === "char") return buf;
    // One shared formatter with Options ▸ Alternative Representation; the
    // "Convert Basic Latin" flag decides whether printable ASCII is escaped
    // or left alone, exactly like `ConvertToCharRef`'s bConvertBasicLatin.
    return [...buf]
      .map((c) => charRef(c.codePointAt(0)!, mode, settings.convertBasicLatin))
      .join("");
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
    return revertToChars(text, from);
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
      const item = new ClipboardItem({
        "text/rtf": blob,
        "text/plain": plainBlob,
      });
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

  /** Append text to the edit buffer (the UVS dialog's rows do this). */
  function appendText(text: string) {
    buf += text;
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
    const escaped = text
      .replace(/\\/g, "\\\\")
      .replace(/\{/g, "\\{")
      .replace(/\}/g, "\\}")
      .replace(/\n/g, "\\par\n")
      .replace(/\r/g, "");
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

  /** True when the plane has no assigned characters (`Unicode::IsPlaneReserved`). */
  function planeIsReserved(p: number): boolean {
    const m = planeMeta.find((x) => x.plane === p);
    return !!m?.reserved;
  }
  // ── Options ▸ CJKV / Tangut readings (description annotations) ──────
  // The backend formats them with the same global switches the original uses
  // (`Lookup::UseUpperCaseReadings` / `UseToneNumbers`), so the flags are part
  // of the cache key.
  interface Readings {
    cjkv: string;
    tangut: string;
    cjk_refs: string;
    tangut_refs: string;
    cjk: boolean;
    tangut_char: boolean;
  }
  let _readings = $state<Record<string, Readings>>({});
  function readingsKey(cp: number): string {
    return [
      cp,
      settings.cjkvReading,
      settings.tangutReading,
      settings.cjkvUpperCase ? 1 : 0,
      settings.cjkvToneNumbers ? 1 : 0,
      settings.tangutToneNumbers ? 1 : 0,
    ].join(":");
  }
  $effect(() => {
    const cp = selCp();
    if (cp == null || cp < 0) return;
    const key = readingsKey(cp);
    if (_readings[key]) return;
    const q = new URLSearchParams({
      cjkv: settings.cjkvReading,
      tangut: settings.tangutReading,
      upper: String(settings.cjkvUpperCase),
      tones: String(settings.cjkvToneNumbers),
      tangut_tones: String(settings.tangutToneNumbers),
    });
    fetch(`${API_BASE}/readings/${cp}?${q.toString()}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) _readings[key] = d as Readings;
      })
      .catch(() => {});
  });

  /** True for names the original only shows when "algorithmic names" is on. */
  function isAlgorithmicName(n: string): boolean {
    return /^(CJK (UNIFIED|COMPATIBILITY) IDEOGRAPH|TANGUT IDEOGRAPH|TANGUT COMPONENT|NUSHU CHARACTER|KHITAN SMALL SCRIPT CHARACTER|EGYPTIAN HIEROGLYPH)/.test(
      n,
    );
  }

  let selInfo = $derived.by(() => {
    const cp = selCp();
    if (cp != null && cp >= 0) {
      const cell = grid!.cells[sr]?.[sc];
      const reserved = cell?.reserved;
      const short = reserved
        ? "<reserved>"
        : selName() || `U+${cp.toString(16).toUpperCase()}`;
      const rd = _readings[readingsKey(cp)];
      // The original's SetDescription(): name → " : <source refs>" →
      // " [reading]", with each piece owned by one Options toggle.
      const parts: string[] = [];
      if (
        !reserved &&
        (settings.showAlgorithmicNames || !isAlgorithmicName(short))
      ) {
        parts.push(short);
      }
      if (rd?.cjk && settings.showCjkRefs && rd.cjk_refs) {
        parts.push(`: ${rd.cjk_refs}`);
      }
      if (rd?.cjkv) parts.push(`[${rd.cjkv}]`);
      if (rd?.tangut_char && settings.showTangutRefs && rd.tangut_refs) {
        parts.push(`: ${rd.tangut_refs}`);
      }
      if (rd?.tangut) parts.push(`[${rd.tangut}]`);
      return {
        hex: cp
          .toString(16)
          .toUpperCase()
          .padStart(cp > 0xffff ? 5 : 4, "0"),
        char: String.fromCodePoint(cp),
        // Options ▸ Alternative Representation — this field is the original's
        // `m_pAltCode` (the third edit box of the map dialog).
        alt: altRepresentation(
          cp,
          settings.altRepr,
          settings.convertBasicLatin,
        ),
        name: parts.join(" "),
        short,
      };
    }
    return null;
  });

  async function onKey(e: KeyboardEvent) {
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target instanceof HTMLSelectElement
    )
      return;
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
    } else if (e.key === "F9") {
      e.preventDefault();
      openCharProps();
    } else if (e.key === "F7" && e.shiftKey) {
      e.preventDefault();
      showCompositeFont = true;
    } else if (e.key === "F6") {
      // Edit ▸ Copy Glyph / Copy Glyph Outline.
      e.preventDefault();
      await copyGlyph(e.shiftKey);
    } else if (e.key === "F12") {
      // Tools ▸ Mandarin (F12) / Cantonese (Shift+F12).
      e.preventDefault();
      openLookup(e.shiftKey ? "jyutping" : "pinyin");
    } else if (e.key === "F11") {
      // Tools ▸ Han Radical (F11) / Yi Radical (Shift+F11).
      e.preventDefault();
      openLookup(e.shiftKey ? "yi_radical" : "han_radical");
    } else if (e.key === "1" && (e.altKey || e.ctrlKey)) {
      // Ctrl+1 / Ctrl+2 are consumed by the browser (tab switching), so the
      // working accelerator is Alt+1 / Alt+2.
      e.preventDefault();
      setFontMode("single");
    } else if (e.key === "2" && (e.altKey || e.ctrlKey)) {
      e.preventDefault();
      setFontMode("composite");
    } else if (e.key === "Insert") {
      e.preventDefault();
      doAddBookmark();
    } else if (e.key === "Delete" && e.ctrlKey) {
      e.preventDefault();
      doRemoveBookmark();
    } else if (e.key === "F8" && e.shiftKey) {
      e.preventDefault();
      showEmojiLookup = true;
    } else if (e.key === "F1") {
      e.preventDefault();
      showHelp = true;
    }
  }

  function openCharProps() {
    const cp = selCp();
    if (cp == null || cp < 0) {
      showStatus(t("general.not_assigned"));
      return;
    }
    charPropsCp = cp;
    showCharProps = true;
  }

  async function onMenuAction(label: string) {
    if (label === t("file.close_tray")) await windowAction("tray");
    else if (label === t("file.exit")) await windowAction("exit");
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
    else if (label === t("edit.copy_glyph")) await copyGlyph(false);
    else if (label === t("edit.copy_glyph_outline")) await copyGlyph(true);
    else if (label === t("edit.char")) changeMode("char");
    else if (label === t("edit.ncr_hex")) changeMode("ncr_hex");
    else if (label === t("edit.ncr_dec")) changeMode("ncr_dec");
    else if (label === t("edit.html")) changeMode("html");
    else if (label === t("edit.ucn")) changeMode("ucn");
    // Find menu
    else if (label === t("find.search_prev")) doSearchPrev();
    else if (label === t("find.search_next")) doSearchNext();
    else if (label === t("find.goto_han")) doGotoHan();
    else if (label === t("find.goto_cp")) doGo();
    else if (label === t("find.locate_char")) doLocateChar();
    // Tools menu
    else if (label === t("tools.unicode")) showUnicode = true;
    else if (label === t("tools.properties")) openCharProps();
    else if (label === t("tools.emoji_lookup")) showEmojiLookup = true;
    else if (label === t("tools.opentype_test")) showOpenTypeTest = true;
    else if (label === t("tools.mandarin")) openLookup("pinyin");
    else if (label === t("tools.cantonese")) openLookup("jyutping");
    else if (label === t("tools.zhuang")) openLookup("zhuang");
    else if (label === t("tools.han_radical")) openLookup("han_radical");
    else if (label === t("tools.yi_radical")) openLookup("yi_radical");
    else if (label === t("tools.supplementary")) openSupplementaryInfo();
    else if (label === t("tools.ucd")) showUcd = true;
    else if (label === t("tools.ucd_xml")) await generateUcdXml();
    // Fonts menu
    else if (label === t("fonts.single")) setFontMode("single");
    else if (label === t("fonts.composite")) setFontMode("composite");
    else if (label === t("fonts.list_all_styles")) {
      settings.allStyles = !settings.allStyles;
      showStatus(
        settings.allStyles
          ? "Listing all styles of every font"
          : "Listing only primary styles",
      );
    } else if (label === t("fonts.legacy_enum")) {
      settings.legacyEnum = !settings.legacyEnum;
      showStatus(
        settings.legacyEnum
          ? "Legacy (GDI) font names"
          : "Typographic font names",
      );
    } else if (label === t("fonts.symbol_mappings")) {
      settings.symbolMapping = !settings.symbolMapping;
      showStatus(
        settings.symbolMapping
          ? "Symbol font mappings ON (U+F020–F0FF shown as ASCII)"
          : "Symbol font mappings OFF",
      );
    } else if (label === t("fonts.very_small")) setGridSizeIndex(0);
    else if (label === t("fonts.small")) setGridSizeIndex(1);
    else if (label === t("fonts.medium")) setGridSizeIndex(2);
    else if (label === t("fonts.large")) setGridSizeIndex(3);
    else if (label === t("fonts.very_large")) setGridSizeIndex(4);
    else if (label === t("fonts.default")) settings.fontQuality = 0;
    else if (label === t("fonts.draft")) settings.fontQuality = 1;
    else if (label === t("fonts.proof")) settings.fontQuality = 2;
    else if (label === t("fonts.non_aa")) settings.fontQuality = 3;
    else if (label === t("fonts.aa")) settings.fontQuality = 4;
    else if (label === t("fonts.cleartype")) settings.fontQuality = 5;
    else if (label === t("fonts.cleartype_nat")) settings.fontQuality = 6;
    else if (label === t("fonts.quality_dialog")) showFontQuality = true;
    else if (label === t("fonts.overview")) showFontOverview = true;
    else if (label === t("fonts.export_glyphs")) showExportGlyphs = true;
    else if (label === t("fonts.composite_mapping")) showCompositeFont = true;
    else if (label === t("font.configure")) showCompositeFont = true;
    // View menu
    else if (label === t("view.show_edit_buffer")) {
      editVisible = !editVisible;
      showStatus(editVisible ? "Edit buffer shown" : "Edit buffer hidden");
    } else if (label === t("view.filter_no_block")) {
      settings.showReservedRanges = !settings.showReservedRanges;
      showStatus(
        _filterNoBlock
          ? "Filter ON: unassigned blocks hidden"
          : "Filter OFF: showing full planes",
      );
      load();
    } else if (label === t("view.medium_size")) setViewSize("medium");
    else if (label === t("view.large_size")) setViewSize("large");
    else if (label === t("view.hide_reserved_planes")) {
      settings.showReservedPlanes = !settings.showReservedPlanes;
      // Hiding them again while one is on screen falls back to the BMP, like
      // `OnViewReservedPlanes` does.
      if (!settings.showReservedPlanes && planeIsReserved(plane)) goPlane(0);
      showStatus(
        settings.showReservedPlanes
          ? "Showing the reserved planes"
          : "Hiding the reserved planes",
      );
    } else if (label === t("view.keep_on_top"))
      await setKeepOnTop(!settings.keepOnTop);
    // Bookmarks menu
    else if (label === t("bookmarks.manage")) showBookmarks = true;
    else if (label === t("bookmarks.add")) doAddBookmark();
    else if (label === t("bookmarks.remove")) doRemoveBookmark();
    else if (label === t("bookmarks.clear")) {
      clearBookmarks();
      showStatus("Bookmarks cleared");
    } else if (/^U\+[0-9A-F]{4,6}\b/.test(label)) {
      // A dynamic bookmark entry — jump to that code point.
      const cp = parseInt(label.slice(2).split(" ")[0], 16);
      if (!Number.isNaN(cp)) await gotoCP(cp);
    }
    // Help menu — both items open the same window (F1 is Online Help).
    else if (label === t("help.help") || label === t("help.about"))
      showHelp = true;
    // Options menu
    else onOptionsAction(label);
  }

  /** Bookmarks ▸ Add Bookmark (Insert) — adds the selected character. */
  function doAddBookmark(): void {
    const cp = selCp();
    if (cp == null || cp < 0) {
      showStatus(t("general.select_char"));
      return;
    }
    const name = selInfo?.short || `U+${bmHex(cp)}`;
    const idx = addBookmark(cp, name);
    showStatus(
      idx >= 0
        ? `Bookmarked U+${bmHex(cp)}`
        : bookmarkList().some((b) => b.cp === cp)
          ? `U+${bmHex(cp)} is already bookmarked`
          : `Bookmarks are full (32)`,
    );
  }

  /** Bookmarks ▸ Remove Bookmark (Ctrl+Delete). */
  function doRemoveBookmark(): void {
    const cp = selCp();
    if (cp == null || cp < 0) return;
    showStatus(
      removeBookmark(cp)
        ? `Bookmark removed: U+${bmHex(cp)}`
        : `U+${bmHex(cp)} is not bookmarked`,
    );
  }

  /**
   * One Options item.
   *
   * The original has one handler per group that differs only in *which value*
   * the clicked id maps to (`nID - IDM_OPTIONS_<group>_START`), so the same
   * shape is used here: a `[values, labelKeys]` pair plus a setter.
   */
  function onOptionsAction(label: string): void {
    /** Radio group: pick the value whose label matches, if any. */
    const choose = <T,>(
      values: readonly T[],
      keys: readonly string[],
      set: (v: T) => void,
    ): boolean => {
      const i = keys.findIndex((k) => t(k) === label);
      if (i < 0) return false;
      set(values[i]);
      return true;
    };

    if (label === t("options.blocks_alpha")) settings.blocksSorted = true;
    else if (label === t("options.blocks_codepoint"))
      settings.blocksSorted = false;
    else if (label === t("options.search_aliases"))
      settings.searchAliases = !settings.searchAliases;
    else if (label === t("options.goto_hex")) settings.gotoHex = true;
    else if (label === t("options.goto_dec")) settings.gotoHex = false;
    else if (
      choose(ALT_REPRS, ALT_KEYS, (v) => (settings.altRepr = v)) ||
      choose(CJKV_READINGS, CJKV_KEYS, (v) => (settings.cjkvReading = v)) ||
      choose(
        TANGUT_READINGS,
        TANGUT_KEYS,
        (v) => (settings.tangutReading = v),
      ) ||
      choose([36, 72, 108, 144], POPUP_KEYS, (v) => (settings.popupMag = v)) ||
      choose(COLOUR_CODINGS, COLOUR_KEYS, (v) => (settings.colourCoding = v))
    ) {
      // handled by the group above
    } else if (label === t("options.cjkv_upper_case"))
      settings.cjkvUpperCase = !settings.cjkvUpperCase;
    else if (label === t("options.cjkv_tone_numbers"))
      settings.cjkvToneNumbers = !settings.cjkvToneNumbers;
    else if (label === t("options.tangut_tones"))
      settings.tangutToneNumbers = !settings.tangutToneNumbers;
    else if (label === t("options.grid_single_click"))
      settings.selectClick = "single";
    else if (label === t("options.grid_double_click"))
      settings.selectClick = "double";
    else if (label === t("options.grid_copy_on_select"))
      settings.copyOnSelect = !settings.copyOnSelect;
    else if (label === t("options.cutcopy_plain")) settings.cutCopy = "plain";
    else if (label === t("options.cutcopy_rtf")) settings.cutCopy = "rtf";
    else if (label === t("options.status_algorithmic"))
      settings.showAlgorithmicNames = !settings.showAlgorithmicNames;
    else if (label === t("options.status_cjk"))
      settings.showCjkRefs = !settings.showCjkRefs;
    else if (label === t("options.status_tangut"))
      settings.showTangutRefs = !settings.showTangutRefs;
    else if (label === t("options.other_convert_latin"))
      settings.convertBasicLatin = !settings.convertBasicLatin;
    else if (label === t("options.other_rotate_vertical"))
      settings.rotateVertical = !settings.rotateVertical;
    else if (label === t("options.other_close_tray"))
      settings.closeToTray = !settings.closeToTray;
    else if (label === t("options.font_config")) showCompositeFont = true;
    else if (label === t("options.customize_colours")) showColourConfig = true;
    else if (label === t("options.reset")) doResetSettings();
  }

  /** Options ▸ Reset — the original's confirmation + `m_pRegistry->Reset()`. */
  function doResetSettings(): void {
    if (!confirm("Reset all options to default settings?")) return;
    resetSettings();
    // The Fonts group is mirrored into the render stores; re-apply + rebuild.
    setFontMode(settings.fontMode);
    showStatus("All options reset to defaults");
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
  loadPlanes();
  loadUserFonts();
  startBackend();

  // Kick the (CPU-heavy) font analysis off right after the shell is up, so it
  // overlaps with the user's first interactions instead of blocking the dialog
  // they open it from.  Progress is shown in the status bar at the bottom, and
  // in the dialog itself while it waits for the first result.
  $effect(() => {
    startScanTicker();
    startCoverageScan();
  });
</script>

<svelte:window onkeydown={onKey} />

<div class="app" class:dark>
  <MenuBar
    {dark}
    {showLang}
    {onMenuAction}
    onDarkToggle={() => (dark = !dark)}
    onToggleLang={() => (showLang = !showLang)}
    onCloseLang={() => (showLang = false)}
  />

  <PlaneTabs {plane} planes={PLANES} onChange={goPlane} />

  <div class="main">
    <div class="gw">
      <GridHeader {loading} {err} {grid} />
      <CharacterGrid
        {grid}
        {plane}
        {sr}
        {sc}
        stackFamily={stack}
        fontSize={fontStack.gridSize}
        onSelect={selectCell}
        onAddToBuffer={addToBuf}
        onDblClick={openCharProps}
        onWheel={(deltaY: number) => nav(deltaY > 0 ? 1 : -1)}
        onZoom={(deltaY: number) => zoomGrid(deltaY)}
      />
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
      onIvs={() => openUvs()}
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
    stackFamily={stack}
    bufSize={fontStack.bufferSize}
    onBufSizeChange={(n: number) => {
      fontStack.bufferSize = Math.max(
        MIN_SIZE,
        Math.min(MAX_SIZE, Math.round(n)),
      );
    }}
    onConfigureStack={() => (showCompositeFont = true)}
    {gv}
    {sv}
    gotoHex={settings.gotoHex}
    blocks={blocksShown}
    {sblock}
    {editVisible}
    onBufChange={(v: string) => (buf = v)}
    onSblockChange={(v: string) => (sblock = v)}
    onGvChange={(v: string) => (gv = v)}
    onSvChange={(v: string) => (sv = v)}
    onBlockSelect={doBlock}
    onSearch={doSearch}
    onSearchPrev={doSearchPrev}
    onSearchNext={doSearchNext}
    searchResults={_sresults}
    searchIdx={_sidx}
    searchQuery={_normalizedQuery}
    searchProgress={_searchProgress}
    showResults={_showResults}
    {onSearchResultClick}
    onCloseResults={onDismissResults}
    searchLoading={_searchLoading}
    onLoadMoreResults={loadMoreResults}
    onGoto={doGo}
    onModeChange={(m: string) => changeMode(m as any)}
    onGlyphToggle={(v: boolean) => (glyph = v)}
    onColourToggle={(v: boolean) => (colour = v)}
    onCopy={settings.cutCopy === "rtf" ? copyRtf : copyPlain}
    onCut={settings.cutCopy === "rtf" ? cutRtf : cutPlain}
    onClear={doClear}
    onSave={openSaveDlg}
    onHideToggle={() => {
      editVisible = false;
      showStatus("Edit buffer hidden — View ▸ Show Edit Buffer");
    }}
    onContextMenu={(e: MouseEvent) =>
      openCtxMenu(e, e.currentTarget as HTMLTextAreaElement)}
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

  <UnicodeDialog
    show={showUnicode}
    onClose={() => (showUnicode = false)}
    onGotoCP={(cp: number) => {
      showUnicode = false;
      gotoCP(cp);
    }}
  />

  <CharacterPropertiesDialog
    show={showCharProps}
    cp={charPropsCp}
    initialView={charPropsView}
    onInsert={(text: string) => {
      appendText(text);
      showStatus(
        `Inserted ${[...text].map((c) => `U+${c.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}`).join(" ")}`,
      );
    }}
    onClose={() => (showCharProps = false)}
  />

  <EmojiLookupDialog
    show={showEmojiLookup}
    onClose={() => (showEmojiLookup = false)}
    onGotoCP={(cp: number) => {
      showEmojiLookup = false;
      gotoCP(cp);
    }}
  />

  <OpenTypeTestDialog
    show={showOpenTypeTest}
    onClose={() => (showOpenTypeTest = false)}
  />

  <FontOverviewDialog
    show={showFontOverview}
    onClose={() => (showFontOverview = false)}
  />

  <CompositeFontDialog
    show={showCompositeFont}
    onClose={() => (showCompositeFont = false)}
  />

  <FontQualityDialog
    show={showFontQuality}
    onClose={() => (showFontQuality = false)}
  />

  <ExportGlyphsDialog
    show={showExportGlyphs}
    onClose={() => (showExportGlyphs = false)}
    initialCps={exportCps}
  />

  <ColourCodingDialog
    show={showColourConfig}
    onClose={() => (showColourConfig = false)}
  />

  <BookmarksDialog
    show={showBookmarks}
    onClose={() => (showBookmarks = false)}
    onGoto={(cp: number) => {
      showBookmarks = false;
      gotoCP(cp);
    }}
  />

  <HelpDialog show={showHelp} onClose={() => (showHelp = false)} />

  <LookupDialog
    show={showLookup}
    kind={lookupKind}
    onClose={() => (showLookup = false)}
    onGoto={(cp: number) => {
      showLookup = false;
      gotoCP(cp);
    }}
  />

  <UcdDialog show={showUcd} onClose={() => (showUcd = false)} />

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
