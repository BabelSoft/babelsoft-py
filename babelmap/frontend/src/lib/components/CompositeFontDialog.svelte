<script lang="ts">
  import Icon from "../icons/Icon.svelte";
  import { untrack } from "svelte";
  import { API_BASE } from "../api";
  import { t } from "../i18n.svelte";
  import {
    fontStack,
    loadUserFonts,
    parseRange,
    buildCss,
    stackFamily,
    applyStack,
    clearStack,
    newItemId,
    setBlockAssignment,
    clearBlockAssignment,
    blockRangeCss,
    type StackItem,
    type FontStyle,
  } from "../fontStack.svelte";
  import {
    coverageStore,
    loadCoverage,
    loadBlockChars,
    supportSet,
    runAuto,
    autoFor,
    blockRange,
    fmtInt,
    scanPct,
    scanElapsed,
    type BlockRow,
    type BlockFont,
  } from "../coverage.svelte";

  // Composite Font Mappings — build the font stack the character grid and the
  // edit buffer share.
  //
  // Three surfaces write the same model:
  //   1. **Blocks** — per-Unicode-block font coverage + the Auto assignment
  //      (the port of the original CDialogConfig block list and its Auto
  //      button; see backend/font_coverage.py);
  //   2. point-and-click rows (font + style + character range) → @font-face;
  //   3. a hand-written CSS editor, compile-checked by the backend.
  // The stack is applied front-to-back (a later entry is a later fallback), so
  // new rows are always APPENDED — you cannot insert in the middle, because that
  // would silently change which face wins for an overlapping range.

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();

  let tab = $state<"blocks" | "entries" | "css">("blocks");
  let families = $state<string[]>([]);
  let loadingFonts = $state(false);

  // ── window chrome ──
  let x = $state(120);
  let y = $state(60);
  let w = $state(
    Math.min(
      1120,
      (typeof window !== "undefined" ? window.innerWidth : 1120) - 40,
    ),
  );
  let h = $state(
    Math.min(
      780,
      (typeof window !== "undefined" ? window.innerHeight : 780) - 40,
    ),
  );

  /**
   * Keep the dialog inside the viewport.
   *
   * The defaults above assume a large window; on a narrow one (or after a
   * resize) the dialog would extend past the right/bottom edge and take the
   * close button with it.  Runs on open and on every resize.  This dialog has no
   * resize handle, so the size is always re-derived from the viewport.
   */
  function clampToViewport() {
    if (typeof window === "undefined") return;
    untrack(() => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const m = 8;
      w = Math.max(320, Math.min(1120, vw - m * 2));
      h = Math.max(240, Math.min(780, vh - m * 2));
      x = Math.min(Math.max(x, m), Math.max(m, vw - w - m));
      y = Math.min(Math.max(y, m), Math.max(m, vh - h - m));
    });
  }
  $effect(() => {
    if (!show) return;
    clampToViewport();
    const onResize = () => clampToViewport();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  });
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

  // ── data ──
  async function loadFamilies() {
    loadingFonts = true;
    try {
      const r = await fetch(API_BASE + "/fonts");
      const d = await r.json();
      families = Array.isArray(d) ? d : [];
    } catch {
      families = [];
    }
    await loadUserFonts();
    loadingFonts = false;
  }

  /**
   * The overview's face list, reused for the entry editor's style and axis
   * choices.  The overview dialog loads the same endpoint, and the backend
   * caches the scan, so this is a cheap warm call.
   */
  let overviewFaces = $state<
    {
      family: string;
      italic: boolean;
      variable: boolean;
      axes: { tag: string; min: number; default: number; max: number }[];
    }[]
  >([]);
  async function loadOverviewFaces() {
    if (overviewFaces.length) return;
    try {
      const r = await fetch(API_BASE + "/fonts/overview");
      const d = await r.json();
      overviewFaces = d.fonts ?? [];
    } catch {
      overviewFaces = [];
    }
  }
  $effect(() => {
    if (show) {
      loadFamilies();
      void loadOverviewFaces();
    }
  });
  // The coverage table is normally preloaded at app start (App.svelte →
  // startCoverageScan).  This only covers the case where that was skipped or
  // failed, so opening the tab always ends up with data.
  $effect(() => {
    if (
      show &&
      tab === "blocks" &&
      !coverageStore.loaded &&
      !coverageStore.loading
    ) {
      void loadCoverage();
    }
  });

  // ── Blocks tab ──
  let blockSearch = $state("");
  let blockFilter = $state<"all" | "incomplete" | "empty">("all");
  /** The block whose font list the right column shows. */
  let selectedBlock = $state<BlockRow | null>(null);
  /**
   * The font the preview renders with.  Defaults to the block's best font;
   * clicking a font in the right-hand list switches it, so the same full block
   * can be compared across fonts (unsupported characters grey out).
   */
  let previewFont = $state<BlockFont | null>(null);

  /** Push a block's range onto the stack as a manual entry. */
  function pushBlockEntry(b: BlockRow, family: string) {
    if (!family) return;
    fontStack.items = [
      ...fontStack.items,
      {
        id: newItemId(),
        family,
        source: "system",
        style: "normal",
        axis: defaultAxisFor(family),
        stretch: "100%",
        unicodeRange: `U+${b.start.toString(16).toUpperCase()}-${b.end.toString(16).toUpperCase()}`,
        note: b.name,
        enabled: true,
      },
    ];
    void refreshPreview();
  }

  const blockRows = $derived.by(() => {
    const q = blockSearch.trim().toLowerCase();
    return coverageStore.blocks.filter((b) => {
      if (blockFilter === "incomplete" && b.covered >= b.total) return false;
      if (blockFilter === "empty" && b.covered > 0) return false;
      if (!q) return true;
      return (
        b.name.toLowerCase().includes(q) ||
        blockRange(b).toLowerCase().includes(q) ||
        (b.best_font || "").toLowerCase().includes(q)
      );
    });
  });

  /** The block assignments, keyed by block name (they drive the row labels). */
  const assignedByBlock = $derived.by(() => {
    const m = new Map<string, (typeof fontStack.blocks)[number]>();
    for (const a of fontStack.blocks) m.set(a.block, a);
    return m;
  });

  /** The family a block will actually use: saved assignment → Auto → best. */
  function blockFamily(b: BlockRow): string {
    const saved = assignedByBlock.get(b.name);
    if (saved) return (saved.family || saved.userId || "").trim();
    const a = autoFor(b.name);
    return (a?.font || b.best_font || "").trim();
  }

  /**
   * ``blockFamily`` is called once per row below. It must therefore be cheap:
   * the 340-row table re-renders on every selection change, so resolving the
   * Auto assignment per row per render dominated the 100ms+ block switch.
   * Memoise on ``auto`` and ``fontStack.blocks`` — the only inputs besides the
   * row itself.
   */
  const familyByBlock = $derived.by(() => {
    void coverageStore.auto;
    void coverageStore.blocks;
    void fontStack.blocks;
    const m = new Map<string, string>();
    for (const b of coverageStore.blocks) m.set(b.name, blockFamily(b));
    return m;
  });
  function famOf(b: BlockRow): string {
    return familyByBlock.get(b.name) ?? "";
  }

  /** The Auto assignment per block, resolved once instead of per row per render. */
  const autoByBlock = $derived.by(() => {
    const m = new Map<string, { font: string; reason: string }>();
    for (const a of coverageStore.auto ?? []) m.set(a.block, a);
    return m;
  });

  /**
   * The assignment a block row saves.
   *
   * ``origin`` records provenance only ("A" vs "✎" in the row): an assignment
   * whose font matches the Auto winner is tagged ``auto``, anything else is the
   * user's own choice.
   */
  function assignmentFor(b: BlockRow, family: string) {
    const face = b.fonts.find((f) => f.family === family);
    const auto = autoByBlock.get(b.name);
    return {
      block: b.name,
      family,
      source: "system" as const,
      style: "normal" as FontStyle,
      weight: String(face?.weight || b.best_weight || 400),
      axis: undefined as string | undefined,
      start: b.start,
      end: b.end,
      origin:
        auto && auto.font === family ? ("auto" as const) : ("user" as const),
    };
  }

  /** Double-click a block row → set it to the shown font (the edit action). */
  function assignBlock(b: BlockRow) {
    const fam = famOf(b);
    if (!fam) return;
    setBlockAssignment(assignmentFor(b, fam));
    void refreshPreview();
  }

  /**
   * The font row's **Set font** action: assign this block to that specific
   * face.  Blocks whose characters a manually chosen font does not cover are
   * still allowed — that is the user's call — but the row keeps showing the
   * real coverage count so a bad choice is visible.
   */
  function setBlockFont(b: BlockRow, f: BlockFont) {
    setBlockAssignment({
      block: b.name,
      family: f.family,
      source: "system",
      style: "normal",
      axis: defaultAxisFor(f.family) || undefined,
      start: b.start,
      end: b.end,
    });
    previewFont = f;
    void refreshPreview();
  }

  /** Select a block and show every font covering it in the right column. */
  function selectBlock(b: BlockRow) {
    selectedBlock = b;
    // Reset the preview to the block's best font and pull its full character
    // list (a block can hold tens of thousands of characters).
    previewFont =
      b.fonts.find((f) => f.index === b.best_index) ?? b.fonts[0] ?? null;
    void loadBlockChars(b.name);
  }

  /** Switch the preview to a specific font (from the right-hand list). */
  function selectFont(f: BlockFont) {
    previewFont = f;
  }

  /** Add a stack entry for the block using a *specific* font from the list. */
  function addFontEntry(b: BlockRow, f: { family: string }) {
    pushBlockEntry(b, f.family);
  }

  // Keep the right column populated: once the table arrives, and whenever the
  // current selection is filtered out of view, fall back to the first row.
  $effect(() => {
    const rows = blockRows;
    if (!rows.length) return;
    if (!selectedBlock || !rows.some((r) => r.name === selectedBlock!.name)) {
      selectBlock(rows[0]);
    }
  });

  // Full character list of the selected block (loaded on demand, cached).
  const blockChars = $derived.by(() => {
    const name = selectedBlock?.name;
    return name ? (coverageStore.chars[name] ?? null) : null;
  });

  // Fetch whenever the selection changes and its characters are not cached yet.
  // (Doing it in `selectBlock` alone missed the effect-driven fallback and the
  // return to the Blocks tab, which left the preview stuck on "loading".)
  $effect(() => {
    const name = selectedBlock?.name;
    if (name && !coverageStore.chars[name]) void loadBlockChars(name);
  });

  // The font list can hold 380+ rows; rendering them all on every block switch
  // costs tens of ms. Render a window instead, expanded as the user scrolls.
  const FONT_PAGE = 60;
  let fontLimit = $state(FONT_PAGE);
  // Reset the window whenever the block or the preview font changes.
  $effect(() => {
    void selectedBlock?.name;
    fontLimit = FONT_PAGE;
  });
  const visibleFonts = $derived(
    selectedBlock ? selectedBlock.fonts.slice(0, fontLimit) : [],
  );
  const hiddenFontCount = $derived(
    selectedBlock ? Math.max(0, selectedBlock.fonts.length - fontLimit) : 0,
  );
  function showMoreFonts() {
    fontLimit += FONT_PAGE * 3;
  }

  // The preview grid is windowed the same way: a Han block holds 20 000+ cells.
  const CHAR_PAGE = 600;
  let charLimit = $state(CHAR_PAGE);
  $effect(() => {
    void blockChars?.name;
    void selectedBlock?.name;
    charLimit = CHAR_PAGE;
  });
  const hiddenCharCount = $derived(
    blockChars ? Math.max(0, blockChars.cps.length - charLimit) : 0,
  );
  function showMoreChars() {
    charLimit += CHAR_PAGE * 4;
  }

  /** The font family the preview grid renders with. */
  const previewFontFamily = $derived(
    (previewFont?.family || (selectedBlock ? famOf(selectedBlock) : "")).trim(),
  );

  /**
   * The preview font's coverage of the current block, decoded once.
   *
   * The grid asks "is this cell covered?" per rendered cell, so the old
   * per-cell `chars.find(...).supported_by.includes(...)` was quadratic — on
   * CJK that is 600 cells × a 20 992-entry scan on every re-render.  The server
   * now ships a bitset (see `BlockChars`), decoded here into a byte-per-char
   * array for O(1) lookups, and reused for the "n/total supported" readout
   * instead of relying on the block row's `covered`.
   */
  const previewSupport = $derived.by(() => {
    const data = blockChars;
    if (!data || !previewFont) return null;
    return supportSet(data, previewFont.index);
  });

  /** Characters of the current block with the preview font's coverage flags. */
  const visibleCells = $derived.by(() => {
    const sup = previewSupport;
    const data = blockChars;
    if (!data) return [];
    const n = Math.min(charLimit, data.cps.length);
    const out: { cp: number; char: string; ok: boolean }[] = [];
    for (let i = 0; i < n; i++) {
      out.push({
        cp: data.cps[i],
        char: String.fromCodePoint(data.cps[i]),
        // Unknown coverage (no font chosen yet) shows as supported.
        ok: sup ? sup.has[i] === 1 : true,
      });
    }
    return out;
  });

  async function autoAssignAll() {
    await runAuto();
  }

  // ── entry editor (the pending row that gets appended) ──
  let draft = $state<StackItem>(blankItem());
  function blankItem(): StackItem {
    return {
      id: newItemId(),
      family: "",
      source: "system",
      style: "normal",
      axis: "",
      stretch: "100%",
      unicodeRange: "",
      note: "",
      enabled: true,
    };
  }
  let rangeText = $state("");
  let rangeErr = $state("");
  let draftErr = $state("");

  function onRangeInput(v: string) {
    rangeText = v;
    const p = parseRange(v);
    rangeErr = p.error || "";
    draft.unicodeRange = p.range;
  }

  /**
   * Everything pickable in the entry editor: installed families **plus** the
   * user's uploaded fonts.  Uploaded ones are addressed by `id` (they have no
   * `local()` name), so the select value is ``u:<id>`` for those and the plain
   * family name for installed ones.
   */
  const allFontChoices = $derived.by(() => {
    const sys = [
      ...new Set(
        overviewFaces
          .map((f) => f.family)
          .filter((n) => n && !n.startsWith(".") && !n.startsWith("@")),
      ),
    ].sort((a, b) => a.localeCompare(b));
    const usr = fontStack.userFonts.map((u) => ({
      value: "u:" + u.id,
      label: (u.family || u.name) + "  · uploaded",
      source: "user" as const,
      userId: u.id,
    }));
    return { usr, sys };
  });

  function onPickFont(value: string) {
    if (!value) return;
    if (value.startsWith("u:")) {
      const id = value.slice(2);
      const uf = fontStack.userFonts.find((u) => u.id === id);
      if (uf) {
        draft.source = "user";
        draft.userId = uf.id;
        draft.family = uf.family || uf.name;
      }
    } else {
      draft.source = "system";
      draft.userId = undefined;
      draft.family = value;
    }
    draft.axis = defaultAxisFor(draft.family);
  }

  /**
   * The variable axes of a font, from the overview's scan.
   *
   * The styles/weight list used to be hard-coded, but a font's real
   * possibilities are whatever its `fvar` table declares — the overview already
   * reads that, so the entry editor reuses it (`/api/fonts/overview`).
   */
  const axesOf = $derived.by(() => {
    const m = new Map<
      string,
      { tag: string; min: number; default: number; max: number }[]
    >();
    for (const f of overviewFaces) {
      if (!f.variable || !f.axes?.length) continue;
      if (!m.has(f.family)) m.set(f.family, f.axes);
    }
    return m;
  });
  const draftAxes = $derived(axesOf.get(draft.family) ?? []);
  function defaultAxisFor(family: string): string {
    const ax = axesOf.get(family);
    if (!ax?.length) return "";
    return ax.map((a) => `${a.tag} ${a.default}`).join(", ");
  }

  /** Read one axis' value out of the `"wght 600, wdth 87.5"` string. */
  function axisValue(axis: string | undefined, tag: string, fallback: number) {
    const m = (axis || "").match(new RegExp(`\\b${tag}\\s+(-?[\\d.]+)`));
    return m ? Number(m[1]) : fallback;
  }
  /** Write one axis' value back, keeping the other axes intact. */
  function setAxis(tag: string, value: number) {
    const parts = (draft.axis || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((s) => !new RegExp(`^${tag}\\s`).test(s));
    parts.push(`${tag} ${value}`);
    draft.axis = parts.join(", ");
  }

  /** Style choices, derived from what the fonts actually declare (overview). */
  const styleChoices = $derived.by(() => {
    const avail = new Set<string>(["normal"]);
    const fams = new Set(
      [draft.family, previewFontFamily].filter(Boolean) as string[],
    );
    for (const f of overviewFaces) {
      if (!fams.has(f.family)) continue;
      if (f.italic) avail.add("italic");
    }
    // Italic is meaningful for every font (the browser can synthesise it) but
    // oblique only makes sense as an explicit ask, so keep it last.
    avail.add("oblique");
    return [...avail];
  });

  /** Append the draft to the END of the stack. */
  function appendItem() {
    draftErr = "";
    if (!draft.family) {
      draftErr = "Pick a font first.";
      return;
    }
    if (!draft.unicodeRange) {
      draftErr = rangeErr || "Enter at least one character or range.";
      return;
    }
    fontStack.items = [...fontStack.items, { ...draft, id: newItemId() }];
    draft = blankItem();
    rangeText = "";
    rangeErr = "";
    void refreshPreview();
  }

  function removeItem(id: string) {
    fontStack.items = fontStack.items.filter((i) => i.id !== id);
    void refreshPreview();
  }
  function moveItem(id: string, dir: -1 | 1) {
    const arr = [...fontStack.items];
    const i = arr.findIndex((e) => e.id === id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= arr.length) return;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    fontStack.items = arr;
    void refreshPreview();
  }
  function toggleItem(id: string) {
    fontStack.items = fontStack.items.map((i) =>
      i.id === id ? { ...i, enabled: !i.enabled } : i,
    );
    void refreshPreview();
  }

  // ── CSS generation ──
  let cssErrLines = $derived(
    new Set((fontStack.report?.errors ?? []).map((e) => e.line)),
  );
  let cssWarnLines = $derived(
    new Set((fontStack.report?.warnings ?? []).map((e) => e.line)),
  );

  /**
   * Recompile + re-inject the derived CSS.
   *
   * There is no Apply button: the CSS is a pure function of the block
   * assignments and the entry list, so it is regenerated whenever either
   * changes.  Every mutation funnels through here.
   */
  let _applyTimer: ReturnType<typeof setTimeout> | undefined;
  function refreshPreview() {
    clearTimeout(_applyTimer);
    _applyTimer = setTimeout(() => void applyStack(), 60);
  }
  // Auto-apply on any model change (blocks or entries).
  $effect(() => {
    void fontStack.blocks;
    void fontStack.items;
    if (fontStack.blocks.length || fontStack.items.length) refreshPreview();
  });

  /**
   * The CSS the app actually injects: block assignments first (derived from the
   * Blocks tab), then the appended entry ranges.  Read-only — the CSS tab is a
   * view of this, not an editor.
   */
  const generatedCss = $derived(buildCss(fontStack.items, fontStack.css));
  const previewFamily = $derived(stackFamily(fontStack.items));

  // ── entry preview (the range text, in the entry's own font) ──
  const previewStyle = $derived(
    fontStack.applied && previewFamily ? `font-family: ${previewFamily};` : "",
  );

  function styleText(f: FontStyle) {
    return f === "normal"
      ? t("composite.style_regular")
      : f === "italic"
        ? t("composite.style_italic")
        : t("composite.style_oblique");
  }
</script>

{#if show}
  <div class="modal-mask" role="presentation">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="cfd"
      style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
      onmousedown={(e) => e.stopPropagation()}
      role="dialog"
      aria-label="Composite Font Mappings"
      tabindex="-1"
    >
      <div
        class="cfd-head"
        onmousedown={dragStart}
        role="toolbar"
        tabindex="-1"
      >
        <span class="cfd-title">{t("composite.title")}</span>
        <span class="cfd-sub">{fontStack.items.length} entry(ies)</span>
        <span class="cfd-spacer"></span>
        <button class="cfd-x" onclick={onClose} title="Close"
          ><Icon name="close" size={14} /></button
        >
      </div>

      <div class="cfd-tabs">
        <button class:on={tab === "blocks"} onclick={() => (tab = "blocks")}
          >{t("composite.blocks")}</button
        >
        <button class:on={tab === "entries"} onclick={() => (tab = "entries")}
          >{t("composite.entries")}</button
        >
        <button class:on={tab === "css"} onclick={() => (tab = "css")}>
          {t("composite.css")}
          {#if fontStack.applied && fontStack.report && !fontStack.report.ok}<span
              class="cfd-badge err">!</span
            >{/if}
        </button>
        <span class="cfd-spacer"></span>
        <span class="cfd-applied">
          {fontStack.applied ? t("composite.applied") : t("composite.off")}
        </span>
      </div>

      <div class="cfd-body" class:nofullscroll={tab === "blocks"}>
        {#if tab === "blocks"}
          {#if coverageStore.loading && !coverageStore.blocks.length}
            <!-- First open before the startup scan has finished: a cold scan
                 takes tens of seconds, so show real progress here rather than
                 a bare line of text (the status bar is easy to miss). -->
            <div class="cfd-scan">
              <div class="cfd-scan-title">{t("composite.scanning")}</div>
              <div class="cfd-bar" class:indet={coverageStore.scanTotal === 0}>
                <div class="cfd-bar-fill" style="width:{scanPct()}%"></div>
              </div>
              <div class="cfd-scan-meta">
                {#if coverageStore.scanTotal > 0}
                  <span
                    >{coverageStore.scanDone} / {coverageStore.scanTotal}
                    · {scanPct().toFixed(0)}%</span
                  >
                {:else}
                  <span>{t("composite.enumerating")}</span>
                {/if}
                <span class="cfd-scan-time">{scanElapsed().toFixed(1)}s</span>
              </div>
              <div class="cfd-scan-file" title={coverageStore.scanFile}>
                {coverageStore.scanFile || "\u00a0"}
              </div>
            </div>
          {:else if coverageStore.error}
            <div class="cfd-empty cfd-err">{coverageStore.error}</div>
          {:else}
            <!-- summary + Auto controls -->
            <div class="cfd-cov-bar">
              {#if coverageStore.summary}
                <span class="cfd-cov-stat">
                  <b>{fmtInt(coverageStore.summary.covered_blocks)}</b> /
                  {fmtInt(coverageStore.summary.total_blocks)}
                  {t("composite.blocks_covered")}
                </span>
                <span class="cfd-cov-stat">
                  <b>{fmtInt(coverageStore.summary.covered_chars)}</b> /
                  {fmtInt(coverageStore.summary.total_chars)}
                  {t("composite.chars_covered")}
                  ({((coverageStore.summary.ratio ?? 0) * 100).toFixed(1)}%)
                </span>
                <span class="cfd-cov-stat cfd-dim">
                  {fmtInt(coverageStore.imported)}
                  {t("composite.fonts_scanned")}
                </span>
              {/if}
              <span class="cfd-spacer"></span>
              {#if coverageStore.autoSummary}
                <span class="cfd-cov-stat cfd-ok">
                  ✓ {t("composite.auto_done")}: {coverageStore.autoSummary
                    .assigned_blocks}
                  {t("composite.assigned")}, {coverageStore.autoSummary
                    .unassigned_blocks}
                  {t("composite.unassigned")}
                </span>
              {/if}
              <button
                class="cfd-btn primary"
                onclick={autoAssignAll}
                disabled={coverageStore.autoRunning}
              >
                {coverageStore.autoRunning
                  ? t("composite.running")
                  : t("composite.auto")}
              </button>
            </div>

            <!-- filters -->
            <div class="cfd-cov-filter">
              <div class="cfd-search">
                <input
                  type="text"
                  bind:value={blockSearch}
                  placeholder={t("composite.filter_blocks")}
                  spellcheck="false"
                />
              </div>
              {#each [["all", t("composite.f_all")], ["incomplete", t("composite.f_incomplete")], ["empty", t("composite.f_empty")]] as [v, label]}
                <button
                  class="cfd-chip"
                  class:on={blockFilter === v}
                  onclick={() => (blockFilter = v as any)}>{label}</button
                >
              {/each}
              <span class="cfd-dim"
                >{blockRows.length} / {coverageStore.blocks.length}</span
              >
            </div>

            <!-- two columns: blocks on the left, the fonts covering the
                 selected block (complete list) on the right -->
            <div class="cfd-bsplit">
              <div class="cfd-bcol cfd-bcol-blocks">
                <div class="cfd-btable">
                  <div class="cfd-bhead">
                    <span>{t("composite.col_block")}</span>
                    <span>{t("composite.col_chars")}</span>
                    <span>{t("composite.col_best")}</span>
                    <span>{t("composite.col_covered")}</span>
                  </div>
                  {#each blockRows as b (b.name)}
                    {@const auto = autoByBlock.get(b.name)}
                    {@const fam = famOf(b)}
                    {@const assigned = assignedByBlock.get(b.name)}
                    <!-- Click selects (fills the right column); DOUBLE-click
                         pins the block to the font shown here — that is the
                         "edit this block's font" gesture. -->
                    <button
                      class="cfd-brow"
                      class:on={selectedBlock?.name === b.name}
                      class:pua={b.pua}
                      class:assigned={!!assigned}
                      onclick={() => selectBlock(b)}
                      ondblclick={() => assignBlock(b)}
                      title="{b.name} · {blockRange(b)} · {t(
                        'composite.dblclick_hint',
                      )}"
                    >
                      <span class="cfd-bname">{b.name}</span>
                      <span class="cfd-bnum">{fmtInt(b.total)}</span>
                      <span
                        class="cfd-bfont"
                        style="font-family:'{fam || 'inherit'}'"
                      >
                        <span class="cfd-bfamtext">{fam || "—"}</span>
                        {#if assigned}
                          <span
                            class="cfd-chip pin"
                            title="{assigned.origin === 'auto'
                              ? t('composite.auto')
                              : t('composite.edited')} · {blockRangeCss(
                              assigned,
                            )}">{assigned.origin === "auto" ? "A" : "✎"}</span
                          >
                        {:else if auto}
                          <span class="cfd-chip auto" title={auto.reason}
                            >{t("composite.auto")}</span
                          >
                        {/if}
                      </span>
                      <span class="cfd-bcov">
                        {#if b.pua}
                          <span class="cfd-dim">—</span>
                        {:else}
                          <span class="cfd-bnum"
                            >{fmtInt(b.covered)}/{fmtInt(b.total)}</span
                          >
                          {#if b.covered >= b.total}<b class="cfd-ok">✓</b>{/if}
                        {/if}
                      </span>
                    </button>
                  {/each}
                </div>
              </div>

              <div class="cfd-bcol cfd-bcol-fonts">
                {#if selectedBlock}
                  {@const sel = selectedBlock}
                  <div class="cfd-fh">
                    <div class="cfd-fh-top">
                      <span class="cfd-fh-name">{sel.name}</span>
                      <code class="cfd-brange">{blockRange(sel)}</code>
                      <span class="cfd-dim"
                        >{fmtInt(sel.total)} {t("composite.chars")}</span
                      >
                    </div>
                    <div class="cfd-fh-actions">
                      <span class="cfd-dim">
                        {sel.preferred_font
                          ? `${t("composite.preferred")}: ${sel.preferred_font}`
                          : ""}
                      </span>
                      <span class="cfd-spacer"></span>
                      {#if assignedByBlock.get(sel.name)}
                        <button
                          class="cfd-btn"
                          onclick={() => {
                            clearBlockAssignment(sel.name);
                            void refreshPreview();
                          }}
                          title={t("composite.unpin_hint")}
                          >{t("composite.unpin")}</button
                        >
                      {/if}
                      <button
                        class="cfd-btn primary"
                        onclick={() => assignBlock(sel)}
                        disabled={!previewFontFamily}
                        title={t("composite.set_font_hint")}
                        >{t("composite.set_font")}</button
                      >
                    </div>
                  </div>

                  <!-- preview: the block's FULL character set, one character per
                       box (a continuous string would let cursive scripts join).
                       Clicking a font below re-renders this grid in that font;
                       characters it does not map are greyed out. -->
                  <div class="cfd-prevwrap">
                    {#if blockChars}
                      <div class="cfd-prevmeta">
                        <span class="cfd-dim">
                          {t("composite.preview_font")}:
                          <b>{previewFontFamily || "—"}</b>
                        </span>
                        {#if previewFont}
                          <span class="cfd-dim">
                            {fmtInt(
                              previewSupport?.covered ?? previewFont.covered,
                            )}/{fmtInt(sel.total)}
                            {t("composite.supported")}
                          </span>
                        {/if}
                      </div>
                      <div class="cfd-prev-grid">
                        {#each visibleCells as c (c.cp)}
                          <span
                            class="cfd-prev-cell"
                            class:unsupported={!c.ok}
                            style="font-family:'{previewFontFamily ||
                              'inherit'}'"
                            title="U+{c.cp
                              .toString(16)
                              .toUpperCase()
                              .padStart(4, '0')}">{c.char}</span
                          >
                        {/each}
                      </div>
                      {#if hiddenCharCount > 0}
                        <button
                          class="cfd-btn cfd-more"
                          onclick={showMoreChars}
                        >
                          {t("composite.show_more")} ({fmtInt(hiddenCharCount)})
                        </button>
                      {/if}
                    {:else}
                      <div class="cfd-empty">
                        {t("composite.loading_chars")}
                      </div>
                    {/if}
                  </div>

                  <!-- the COMPLETE list of fonts covering this block; clicking
                       one switches the preview grid above to that font -->
                  <div class="cfd-flist">
                    <div class="cfd-flist-head">
                      {sel.font_count}
                      {t("composite.fonts_covering")}
                    </div>
                    {#each visibleFonts as f (f.index)}
                      <button
                        class="cfd-frow"
                        class:best={f.index === sel.best_index}
                        class:on={previewFont?.index === f.index}
                        onclick={() => selectFont(f)}
                        title={t("composite.preview_this")}
                      >
                        <span
                          class="cfd-frow-name"
                          style="font-family:'{f.family}'">{f.family}</span
                        >
                        <span class="cfd-frow-sub">{f.subfamily}</span>
                        <span class="cfd-bnum"
                          >{fmtInt(f.covered)}/{fmtInt(f.total)}</span
                        >
                        {#if f.preferred}<span class="cfd-chip pref"
                            >{t("composite.preferred")}</span
                          >{/if}
                        {#if f.index === sel.best_index}<span
                            class="cfd-chip auto">{t("composite.best")}</span
                          >{/if}
                        <span
                          class="cfd-micro"
                          role="button"
                          tabindex="0"
                          title={t("composite.set_font_hint")}
                          onclick={(e) => {
                            e.stopPropagation();
                            setBlockFont(sel, f);
                          }}
                          onkeydown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.stopPropagation();
                              setBlockFont(sel, f);
                            }
                          }}>{t("composite.set_font")}</span
                        >
                      </button>
                    {/each}
                    {#if hiddenFontCount > 0}
                      <button class="cfd-btn cfd-more" onclick={showMoreFonts}>
                        {t("composite.show_more")} ({hiddenFontCount})
                      </button>
                    {/if}
                  </div>
                {:else}
                  <div class="cfd-empty">{t("composite.pick_block")}</div>
                {/if}
              </div>
            </div>
          {/if}
        {:else if tab === "entries"}
          <!-- ── add row (appended to the end) ── -->
          <fieldset class="cfd-add">
            <legend>{t("composite.add_entry")}</legend>
            <div class="cfd-addgrid">
              <label class="cfd-f">
                <span>{t("composite.font")}</span>
                <select
                  value={draft.source === "user" && draft.userId
                    ? "u:" + draft.userId
                    : draft.family}
                  onchange={(e) =>
                    onPickFont((e.target as HTMLSelectElement).value)}
                >
                  <option value="">{t("composite.pick_font")}</option>
                  {#if fontStack.userFonts.length}
                    <optgroup
                      label="{t('composite.added_group')} ({fontStack.userFonts
                        .length})"
                    >
                      {#each fontStack.userFonts as u}
                        <option value={"u:" + u.id}>{u.family || u.name}</option
                        >
                      {/each}
                    </optgroup>
                  {/if}
                  <optgroup
                    label="{t('composite.system_fonts')} ({allFontChoices.sys
                      .length})"
                  >
                    {#each allFontChoices.sys as f}<option value={f}>{f}</option
                      >{/each}
                  </optgroup>
                </select>
              </label>

              <label class="cfd-f">
                <span>{t("composite.style")}</span>
                <select bind:value={draft.style}>
                  {#each styleChoices as s}
                    <option value={s}>{styleText(s as FontStyle)}</option>
                  {/each}
                </select>
              </label>

              <label class="cfd-f cfd-wide">
                <span>{t("composite.chars")}</span>
                <input
                  type="text"
                  value={rangeText}
                  placeholder="e.g. 你  or  4E00-9FFF  or  U+3000-303F, U+FF00-FFEF"
                  oninput={(e) =>
                    onRangeInput((e.target as HTMLInputElement).value)}
                />
              </label>

              <label class="cfd-f">
                <span>{t("composite.note")}</span>
                <input
                  type="text"
                  bind:value={draft.note}
                  placeholder="CJK ideographs"
                />
              </label>
            </div>

            <!-- Variable axes — shown only for fonts that actually declare
                 them (fvar).  A static font has no weight to choose: the face
                 IS its weight, so nothing is offered. -->
            {#if draftAxes.length}
              <div class="cfd-axes">
                <span class="cfd-dim">{t("composite.variable_axes")}</span>
                {#each draftAxes as a (a.tag)}
                  <label class="cfd-axis">
                    <code>{a.tag}</code>
                    <input
                      type="range"
                      min={a.min}
                      max={a.max}
                      step={(a.max - a.min) / 100 || 1}
                      value={axisValue(draft.axis, a.tag, a.default)}
                      oninput={(e) =>
                        setAxis(
                          a.tag,
                          Number((e.target as HTMLInputElement).value),
                        )}
                    />
                    <span class="cfd-bnum"
                      >{axisValue(draft.axis, a.tag, a.default)}</span
                    >
                  </label>
                {/each}
              </div>
            {/if}

            {#if rangeErr}<div class="cfd-warn">{rangeErr}</div>{/if}
            <div class="cfd-addrow">
              <span class="cfd-preview" style={previewStyle}
                >{rangeText || ""}</span
              >
              <button class="cfd-btn primary" onclick={appendItem}
                >+ {t("composite.append")}</button
              >
            </div>
            {#if draftErr}<div class="cfd-err">{draftErr}</div>{/if}
          </fieldset>

          <!-- ── current stack ── -->
          <div class="cfd-list">
            {#if fontStack.items.length === 0}
              <div class="cfd-empty">{t("composite.no_entries")}</div>
            {:else}
              {#each fontStack.items as it, i (it.id)}
                <div class="cfd-item" class:off={!it.enabled}>
                  <span class="cfd-ord">{i + 1}</span>
                  <input
                    type="checkbox"
                    checked={it.enabled}
                    onchange={() => toggleItem(it.id)}
                    title="Enable / disable"
                  />
                  <span
                    class="cfd-fam"
                    style="font-family: {it.family || 'inherit'}"
                    >{it.family || "(no font)"}</span
                  >
                  <span class="cfd-chip">{styleText(it.style)}</span>
                  {#if it.axis}<span class="cfd-chip">{it.axis}</span>{/if}
                  {#if it.source === "user"}<span class="cfd-chip user"
                      >added</span
                    >{/if}
                  <code class="cfd-range">{it.unicodeRange}</code>
                  <span class="cfd-note">{it.note || ""}</span>
                  <span class="cfd-acts">
                    <button
                      onclick={() => moveItem(it.id, -1)}
                      disabled={i === 0}
                      title={t("composite.move_up")}
                      ><Icon name="chevron-up" size={12} /></button
                    >
                    <button
                      onclick={() => moveItem(it.id, 1)}
                      disabled={i === fontStack.items.length - 1}
                      title={t("composite.move_down")}
                      ><Icon name="chevron-down" size={12} /></button
                    >
                    <button
                      onclick={() => removeItem(it.id)}
                      title={t("composite.remove")}
                      ><Icon name="trash" size={12} /></button
                    >
                  </span>
                </div>
              {/each}
            {/if}
          </div>
        {:else if tab === "css"}
          <!-- Read-only: the CSS is DERIVED, never typed.  It is built from
               the Blocks tab's per-block assignments first, then the Entries
               tab's ranges appended after them — so the ordering below is the
               actual cascade order the browser will use. -->
          <div class="cfd-cssout cfd-cssonly">
            <div
              class="cfd-status"
              class:ok={fontStack.report?.ok}
              class:bad={fontStack.report && !fontStack.report.ok}
            >
              {#if !fontStack.applied}
                {t("composite.off")}
              {:else if !fontStack.report}
                {t("composite.not_compiled")}
              {:else if fontStack.report.ok}
                ✓ {t("composite.compile_ok")}
                {#if fontStack.report.stats.warnings}<span class="cfd-dim">
                    · {fontStack.report.stats.warnings} warning(s)</span
                  >{/if}
              {:else}
                ✗ {fontStack.report.stats.errors} error(s)
              {/if}
            </div>
            {#if fontStack.report}
              {#each fontStack.report.errors as e}
                <div class="cfd-msg err" role="button" tabindex="0">
                  line {e.line}: {e.message}
                </div>
              {/each}
              {#each fontStack.report.warnings as e}
                <div class="cfd-msg warn">line {e.line}: {e.message}</div>
              {/each}
            {/if}
            <div class="cfd-sub2">{t("composite.compiled_from")}</div>
            <pre class="cfd-compiled">{generatedCss || "/* no entries */"}</pre>
          </div>
        {/if}
      </div>

      <div class="cfd-foot">
        <span class="cfd-dim">{t("composite.autoupdate_hint")}</span>
        <span class="cfd-spacer"></span>
        {#if fontStack.applied}
          <button class="cfd-btn" onclick={() => clearStack()}
            >{t("composite.turn_off")}</button
          >
        {/if}
        <button class="cfd-btn primary" onclick={onClose}
          >{t("composite.close")}</button
        >
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-mask {
    position: fixed;
    inset: 0;
    background: transparent;
    /* must clear the menu bar (z-index 100/200) — at 60 the dialog could be
       drawn *under* it when dragged near the top of the screen */
    z-index: 300;
  }
  .cfd {
    position: fixed;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
    overflow: hidden;
    /* the inline width/height are the OUTER size (see clampToViewport) */
    box-sizing: border-box;
    max-width: calc(100vw - 16px);
    max-height: calc(100vh - 16px);
  }
  .cfd-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    cursor: move;
    user-select: none;
  }
  .cfd-title {
    font-weight: 600;
    font-size: 13px;
  }
  .cfd-sub {
    font-size: 11px;
    color: var(--fg3);
  }
  .cfd-spacer {
    flex: 1;
  }
  .cfd-x {
    border: none;
    background: transparent;
    color: var(--fg);
    cursor: pointer;
    display: flex;
    align-items: center;
    padding: 4px;
    border-radius: 4px;
  }
  .cfd-x:hover {
    background: var(--sc);
  }

  .cfd-tabs {
    display: flex;
    gap: 2px;
    padding: 6px 10px 0;
    border-bottom: 1px solid var(--bd);
  }
  .cfd-tabs button {
    border: 1px solid transparent;
    border-bottom: none;
    background: transparent;
    color: var(--fg3);
    padding: 5px 12px;
    font-size: 12px;
    cursor: pointer;
    border-radius: 6px 6px 0 0;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .cfd-tabs button.on {
    background: var(--bg2);
    color: var(--fg);
    border-color: var(--bd);
  }
  .cfd-badge {
    font-size: 10px;
    background: var(--sc);
    color: var(--fg);
    border-radius: 8px;
    padding: 0 6px;
    line-height: 16px;
  }
  .cfd-badge.err {
    background: #e23d3d;
    color: #fff;
  }

  .cfd-body {
    flex: 1;
    overflow: auto;
    padding: 12px;
    min-height: 0;
  }
  /* The Blocks tab manages its own scrolling (two independent columns), so the
     body must not also scroll — otherwise the whole dialog scrolls as one. */
  .cfd-body.nofullscroll {
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* ── blocks ── */
  /* First-open scan progress (a cold scan takes tens of seconds). */
  .cfd-scan {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: center;
    margin: auto;
    padding: 24px 16px;
    width: min(420px, 100%);
  }
  .cfd-scan-title {
    font-size: 12px;
    color: var(--fg2);
    text-align: center;
  }
  .cfd-bar {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--bg3);
    overflow: hidden;
  }
  .cfd-bar.indet .cfd-bar-fill {
    width: 35% !important;
    animation: cfd-indet 1.1s ease-in-out infinite;
  }
  @keyframes cfd-indet {
    0% {
      margin-left: -35%;
    }
    100% {
      margin-left: 100%;
    }
  }
  .cfd-bar-fill {
    height: 100%;
    background: var(--ac);
    transition: width 0.15s;
  }
  .cfd-scan-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 11px;
    color: var(--fg3);
    font-variant-numeric: tabular-nums;
  }
  .cfd-scan-time {
    font-family: ui-monospace, Consolas, monospace;
  }
  .cfd-scan-file {
    font-size: 11px;
    color: var(--fg3);
    font-family: ui-monospace, Consolas, monospace;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cfd-cov-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--bd);
  }
  .cfd-cov-stat {
    font-size: 11px;
    color: var(--fg2);
  }
  .cfd-cov-stat.cfd-ok {
    color: #2f9e44;
  }
  .cfd-cov-filter {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 0;
  }
  .cfd-search {
    flex: 1;
    min-width: 160px;
  }
  .cfd-search input {
    width: 100%;
    font-family: inherit;
    font-size: 12px;
    color: var(--fg);
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 5px;
    padding: 4px 8px;
    box-sizing: border-box;
  }

  /* the two columns: blocks (left) | fonts covering the selected block (right).
     Each column scrolls on its own; the split itself never scrolls. */
  .cfd-bsplit {
    display: grid;
    grid-template-columns: minmax(260px, 1fr) minmax(280px, 1fr);
    gap: 12px;
    align-items: stretch;
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }
  .cfd-bcol {
    min-width: 0;
    min-height: 0;
    overflow: auto;
  }
  .cfd-bcol-blocks {
    overflow: auto;
  }
  .cfd-bcol-fonts {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow: hidden;
  }
  .cfd-btable {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .cfd-bhead,
  .cfd-brow {
    display: grid;
    grid-template-columns: minmax(110px, 1.6fr) 56px minmax(90px, 1.2fr) 84px;
    gap: 8px;
    align-items: center;
    font-size: 11px;
  }
  .cfd-bhead {
    color: var(--fg3);
    font-weight: 600;
    padding: 4px 6px;
    border-bottom: 1px solid var(--bd);
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
  }
  .cfd-brow {
    padding: 3px 6px;
    border: 1px solid transparent;
    border-radius: 4px;
    background: var(--bg2);
    font-family: inherit;
    color: var(--fg);
    text-align: left;
    cursor: pointer;
    width: 100%;
    /* 340 block rows: let the engine skip layout/paint for offscreen ones. */
    content-visibility: auto;
    contain-intrinsic-size: auto 22px;
  }
  .cfd-brow:hover {
    background: var(--sc);
  }
  .cfd-brow.on {
    border-color: var(--ac);
    background: var(--sc);
  }
  .cfd-brow.pua {
    opacity: 0.6;
  }
  /* A block with a saved font is the one that compiles into the CSS. */
  .cfd-brow.assigned .cfd-bname {
    font-weight: 600;
  }
  .cfd-brow.assigned .cfd-bname::before {
    content: "●";
    color: var(--ac);
    font-size: 8px;
    margin-right: 4px;
    vertical-align: middle;
  }
  .cfd-brange {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 10px;
    color: var(--fg3);
  }
  .cfd-bname {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cfd-bnum {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 10px;
    color: var(--fg3);
    text-align: right;
    white-space: nowrap;
  }
  .cfd-bfont {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    overflow: hidden;
  }
  .cfd-bfamtext {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cfd-bcov {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 4px;
  }
  .cfd-chip.auto {
    background: var(--ac);
    color: #fff;
  }
  /* saved assignment: "A" = came from Auto, "✎" = edited by hand */
  .cfd-chip.pin {
    background: #2f9e44;
    color: #fff;
    min-width: 14px;
    justify-content: center;
  }
  .cfd-chip.pref {
    background: #e67700;
    color: #fff;
  }
  .cfd-ok {
    color: #2f9e44;
  }

  /* ── right column: fonts covering the selected block ── */
  .cfd-fh {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--bd);
  }
  .cfd-fh-top {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
  .cfd-fh-name {
    font-size: 14px;
    font-weight: 600;
  }
  .cfd-fh-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  /* Preview: one box per character, so cursive/connected scripts cannot run
     the sample together — each glyph is isolated by its own cell. */
  .cfd-prevwrap {
    border: 1px solid var(--bd);
    border-radius: 6px;
    background: var(--bg2);
    padding: 6px;
    /* The block can hold thousands of characters; the grid scrolls itself so
       the font list below stays reachable. */
    max-height: 42%;
    overflow: auto;
    flex-shrink: 0;
  }
  .cfd-prevmeta {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 0 2px 6px;
    position: sticky;
    top: 0;
    background: var(--bg2);
    z-index: 1;
  }
  .cfd-prev-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
  }
  .cfd-prev-cell {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    font-size: 22px;
    line-height: 1;
    background: var(--bg);
    border: 1px solid var(--bd);
    border-radius: 3px;
    overflow: hidden;
    content-visibility: auto;
    contain-intrinsic-size: 34px 34px;
  }
  /* "Show more" — the font list and the preview grid are windowed so a block
     with 380 fonts / 20 000 characters does not have to render at once. */
  .cfd-more {
    margin-top: 4px;
    width: 100%;
    font-size: 11px;
    padding: 3px 8px;
  }
  /* A character the selected font does not map — shown, but greyed so the
     gap in the font's coverage is visible. */
  .cfd-prev-cell.unsupported {
    color: var(--fg3);
    opacity: 0.35;
    background: var(--bg3);
    border-style: dashed;
  }
  .cfd-flist {
    display: flex;
    flex-direction: column;
    gap: 1px;
    overflow: auto;
    min-height: 0;
    flex: 1;
  }
  .cfd-flist-head {
    font-size: 11px;
    color: var(--fg3);
    padding: 2px 0 4px;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
  }
  .cfd-frow {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 6px;
    border: 1px solid transparent;
    border-radius: 4px;
    background: var(--bg2);
    font-family: inherit;
    color: var(--fg);
    text-align: left;
    cursor: pointer;
    width: 100%;
    font-size: 11px;
    content-visibility: auto;
    contain-intrinsic-size: auto 22px;
  }
  .cfd-frow:hover {
    background: var(--sc);
  }
  .cfd-frow.best {
    border-color: var(--ac);
  }
  /* The font currently rendered in the preview grid. */
  .cfd-frow.on {
    background: var(--ac);
    color: #fff;
  }
  .cfd-frow.on .cfd-frow-sub,
  .cfd-frow.on .cfd-bnum {
    color: rgba(255, 255, 255, 0.85);
  }
  .cfd-frow-name {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cfd-frow-sub {
    font-size: 10px;
    color: var(--fg3);
    min-width: 60px;
  }
  /* The "Set font" button inside a font row — assigns the selected block to
     that font. */
  .cfd-frow .cfd-micro {
    font-size: 10px;
    line-height: 1;
    padding: 2px 6px;
    border: 1px solid var(--bd);
    border-radius: 4px;
    background: var(--bg);
    color: var(--fg2);
    cursor: pointer;
    flex-shrink: 0;
  }
  .cfd-frow .cfd-micro:hover {
    background: var(--ac);
    color: #fff;
  }
  .cfd-frow.on .cfd-micro {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.45);
  }

  /* ── entries ── */
  .cfd-add {
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 10px 12px;
    margin: 0 0 12px;
  }
  .cfd-add legend {
    font-size: 11px;
    color: var(--fg3);
    padding: 0 6px;
  }
  .cfd-addgrid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px 12px;
  }
  .cfd-f {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 11px;
    color: var(--fg3);
  }
  .cfd-f.cfd-wide {
    grid-column: span 2;
  }
  .cfd-f select,
  .cfd-f input {
    font-family: inherit;
    font-size: 12px;
    color: var(--fg);
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 5px;
    padding: 4px 6px;
    min-width: 0;
  }
  .cfd-addrow {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
  }
  .cfd-preview {
    font-size: 13px;
    color: var(--fg3);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cfd-btn {
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    background: var(--bg2);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 6px;
    padding: 5px 12px;
  }
  .cfd-btn:hover {
    background: var(--sc);
  }
  .cfd-btn.primary {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .cfd-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .cfd-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .cfd-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 1px solid var(--bd);
    border-radius: 7px;
    background: var(--bg2);
  }
  .cfd-item.off {
    opacity: 0.45;
  }
  .cfd-ord {
    width: 20px;
    height: 20px;
    flex: 0 0 20px;
    border-radius: 50%;
    background: var(--ac);
    color: #fff;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cfd-fam {
    font-size: 13px;
    min-width: 120px;
  }
  .cfd-chip {
    font-size: 10px;
    background: var(--sc);
    color: var(--fg);
    border-radius: 8px;
    padding: 1px 7px;
    white-space: nowrap;
  }
  .cfd-chip.user {
    background: #2f9e44;
    color: #fff;
  }
  .cfd-range {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 11px;
    color: var(--fg3);
  }
  .cfd-note {
    font-size: 11px;
    color: var(--fg3);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cfd-acts {
    display: flex;
    gap: 2px;
  }
  .cfd-acts button {
    border: 1px solid var(--bd);
    background: var(--bg);
    color: var(--fg);
    border-radius: 4px;
    cursor: pointer;
    padding: 2px 5px;
    font-size: 11px;
    display: flex;
    align-items: center;
  }
  .cfd-acts button:disabled {
    opacity: 0.35;
    cursor: default;
  }
  .cfd-empty {
    color: var(--fg3);
    font-size: 12px;
    padding: 16px;
    text-align: center;
  }

  /* ── css (read-only view of the generated rules) ── */
  .cfd-cssout {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    min-height: 0;
  }
  /* The CSS tab is a single full-height pane: the rules are generated from
     Blocks + Entries, so there is no editor to split against. */
  .cfd-cssonly {
    min-height: 300px;
  }
  /* ── variable axes in the entry editor ── */
  .cfd-axes {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--bd);
  }
  .cfd-axis {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .cfd-axis code {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 10px;
    color: var(--fg3);
  }
  .cfd-axis input[type="range"] {
    width: 110px;
    accent-color: var(--ac);
  }
  .cfd-axis .cfd-bnum {
    min-width: 34px;
  }
  .cfd-status {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 8px;
    border-radius: 6px;
    background: var(--bg2);
  }
  .cfd-status.ok {
    background: #2f9e44;
    color: #fff;
  }
  .cfd-status.bad {
    background: #e23d3d;
    color: #fff;
  }
  .cfd-msg {
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 5px;
  }
  .cfd-msg.err {
    background: rgba(226, 61, 61, 0.15);
    color: #e23d3d;
  }
  .cfd-msg.warn {
    background: rgba(230, 119, 0, 0.15);
    color: #e67700;
  }
  .cfd-sub2 {
    font-size: 11px;
    color: var(--fg3);
    margin-top: 4px;
  }
  .cfd-compiled {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 11px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 6px;
    padding: 8px;
    margin: 0;
    white-space: pre-wrap;
    overflow: auto;
    flex: 1;
  }

  .cfd-dim {
    font-size: 11px;
    color: var(--fg3);
  }
  .cfd-err {
    font-size: 11px;
    color: #e23d3d;
  }
  .cfd-warn {
    font-size: 11px;
    color: #e67700;
  }

  /* ── footer ── */
  .cfd-foot {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-top: 1px solid var(--bd);
    background: var(--bg2);
  }
  .cfd-applied {
    font-size: 11px;
    color: var(--fg3);
  }
</style>
