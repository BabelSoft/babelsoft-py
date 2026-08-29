<script lang="ts">
  // Unified Unicode data window.
  // Model: Unicode is a versioned dataset — "version" is the largest container.
  //   Top bar: version selector + view switcher + per-version statistics.
  //   Left: navigator (Planes → Blocks / Scripts / two-version diff).
  //   Right top: detail (ranges + stats). Right bottom: character grid.
  // Clicking a character jumps to the main BabelMap grid (onGotoCP).

  interface Props {
    show: boolean;
    onClose: () => void;
    onGotoCP: (cp: number) => void;
  }
  let { show, onClose, onGotoCP }: Props = $props();

  const API = "http://127.0.0.1:18080/api";
  type View = "blocks" | "planes" | "scripts" | "diff";

  interface Blk {
    name: string;
    start: number;
    end: number;
    chars: number;
    version?: string;
    code_points?: number;
  }
  interface NavItem {
    id: string;
    depth: number;
    kind: "plane" | "block" | "script" | "script-block" | "diff-block" | "summary" | "group";
    label: string;
    count?: string;
    blockName?: string;
    version?: string;
    detail: [string, string][];
    expandable?: boolean;
  }

  let loaded = $state(false);
  const VIEWS: [View, string][] = [
    ["blocks", "Blocks"],
    ["planes", "Planes"],
    ["scripts", "Scripts"],
    ["diff", "Compare"],
  ];
  let versions = $state<{ version: string; date: string }[]>([]);
  let history = $state<Record<string, any>>({});
  let planeNames = $state<Record<number, { name: string; abbrev: string }>>({});

  let view = $state<View>("blocks");
  let version = $state("");
  let blocks = $state<Blk[]>([]);
  let filter = $state("");

  let scripts = $state<any[]>([]);
  let scriptBlocks = $state<Record<string, { name: string; chars: number; ranges: string[] }[]>>({});

  let diffFrom = $state("");
  let diffTo = $state("");
  let diff = $state<any>(null);

  let sel = $state<NavItem | null>(null);
  let chars = $state<{ codepoint: number; char: string; name: string }[]>([]);
  let charsLoading = $state(false);
  let charsLabel = $state("");
  let charsVersion = $state("");
  let limit = $state(2000);

  let expandedIds = $state<Set<string>>(new Set());
  let autoExpandDone = $state(false);
  const latestVersion = $derived(versions.length ? versions[versions.length - 1].version : "");

  // ── Drag / position state ──
  let x = $state(120);
  let y = $state(80);
  let w = $state(Math.min(1180, (typeof window !== "undefined" ? window.innerWidth : 1180) - 32));
  let h = $state(Math.min(720, (typeof window !== "undefined" ? window.innerHeight : 720) - 40));
  let dragging = $state(false);
  let dragStartX = $state(0);
  let dragStartY = $state(0);
  let winStartX = $state(0);
  let winStartY = $state(0);
  function onDragStart(e: MouseEvent) {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    winStartX = x;
    winStartY = y;
    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup", onDragEnd);
  }
  function onDragMove(e: MouseEvent) {
    x = winStartX + (e.clientX - dragStartX);
    y = winStartY + (e.clientY - dragStartY);
  }
  function onDragEnd() {
    dragging = false;
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
  }

  // ── Resize state ──
  let resizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartY = $state(0);
  let winStartW = $state(0);
  let winStartH = $state(0);
  function onResizeStart(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    resizing = true;
    resizeStartX = e.clientX;
    resizeStartY = e.clientY;
    winStartW = w;
    winStartH = h;
    document.addEventListener("mousemove", onResizeMove);
    document.addEventListener("mouseup", onResizeEnd);
  }
  function onResizeMove(e: MouseEvent) {
    w = Math.max(720, winStartW + (e.clientX - resizeStartX));
    h = Math.max(320, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  // ── helpers ──
  async function get<T>(p: string): Promise<T> {
    const r = await fetch(API + p);
    if (!r.ok) throw Error(String(r.status));
    return r.json();
  }
  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
  function hex4(n: number): string {
    return n.toString(16).toUpperCase().padStart(4, "0");
  }
  function uhex(n: number): string {
    return "U+" + hex4(n);
  }

  // ── initial load ──
  $effect(() => {
    if (show && !loaded) loadAll();
  });
  async function loadAll() {
    try {
      const v = await get<any>("/unicode/versions");
      versions = v.versions ?? [];
      const h: Record<string, any> = {};
      for (const row of v.history ?? []) h[row.version] = row;
      history = h;
      if (versions.length) {
        version = versions[versions.length - 1].version;
        diffTo = version;
        diffFrom = versions[Math.max(0, versions.length - 2)].version;
      }
      const p = await get<any>("/unicode/planes");
      for (const row of p.planes ?? []) planeNames[row.plane] = { name: row.name, abbrev: row.abbreviation };
      const sc = await get<any>("/unicode/scripts");
      scripts = sc.scripts ?? [];
      loaded = true;
    } catch {
      /* ignore */
    }
  }

  // ── per-version blocks ──
  $effect(() => {
    if (loaded && (view === "blocks" || view === "planes") && version) loadBlocks();
  });
  async function loadBlocks() {
    sel = null;
    chars = [];
    charsLabel = "";
    charsVersion = "";
    try {
      const r = await fetch(API + "/unicode/blocks?version=" + encodeURIComponent(version));
      if (!r.ok) throw Error(String(r.status));
      const d = await r.json();
      blocks = d.blocks ?? [];
      if (!autoExpandDone && view === "blocks") {
        const next = new Set(expandedIds);
        for (const b of blocks) next.add("p" + (b.start >> 16));
        expandedIds = next;
        autoExpandDone = true;
      }
    } catch {
      blocks = [];
    }
  }

  // ── two-version diff ──
  $effect(() => {
    if (loaded && view === "diff" && diffFrom && diffTo) loadDiff();
  });
  async function loadDiff() {
    sel = null;
    chars = [];
    charsLabel = "";
    charsVersion = "";
    try {
      const r = await fetch(API + `/unicode/diff?from=${encodeURIComponent(diffFrom)}&to=${encodeURIComponent(diffTo)}`);
      if (!r.ok) throw Error(String(r.status));
      diff = await r.json();
    } catch {
      diff = null;
    }
  }

  // ── navigator ──
  const filteredBlocks = $derived(filter ? blocks.filter((b) => b.name.toLowerCase().includes(filter.toLowerCase())) : blocks);

  const nav = $derived(buildNav());

  function buildNav(): NavItem[] {
    if (view === "blocks" || view === "planes") return buildBlockNav();
    if (view === "scripts") return buildScriptNav();
    return buildDiffNav();
  }

  function buildBlockNav(): NavItem[] {
    const items: NavItem[] = [];
    const byPlane = new Map<number, Blk[]>();
    for (const b of filteredBlocks) {
      const p = b.start >> 16;
      if (!byPlane.has(p)) byPlane.set(p, []);
      byPlane.get(p)!.push(b);
    }
    for (const [p, bs] of [...byPlane.entries()].sort((a, b) => a[0] - b[0])) {
      const charsTotal = bs.reduce((s, b) => s + b.chars, 0);
      const pn = planeNames[p]?.name ?? `Plane ${p}`;
      const nonchars = p === 0 ? 34 : 2;
      const surrogates = p === 0 ? 2048 : 0;
      const unassigned = 65536 - nonchars - surrogates - charsTotal;
      const id = "p" + p;
      items.push({
        id,
        depth: 0,
        kind: "plane",
        label: `Plane ${p} · ${pn}`,
        count: `${fmt(bs.length)} blk · ${fmt(charsTotal)} chr`,
        expandable: true,
        detail: [
          ["Plane", String(p)],
          ["Name", pn],
          ["Abbreviation", planeNames[p]?.abbrev ?? ""],
          ["Range", `${uhex(p * 0x10000)}..${uhex(p * 0x10000 + 0xffff)}`],
          ["Blocks", fmt(bs.length)],
          ["Characters", fmt(charsTotal)],
          ["Unassigned", fmt(Math.max(0, unassigned))],
        ],
      });
      if (!expandedIds.has(id)) continue;
      for (const b of bs) {
        items.push({
          id: "b" + p + ":" + b.name,
          depth: 1,
          kind: "block",
          label: b.name,
          count: fmt(b.chars),
          blockName: b.name,
          version,
          detail: [
            ["Name", b.name],
            ["Range", `${uhex(b.start)}..${uhex(b.end)}`],
            ["Code Points", fmt(b.end - b.start + 1)],
            ["Characters", fmt(b.chars)],
            ["Unicode Version", b.version ?? version],
            ["Plane", String(p)],
          ],
        });
      }
    }
    return items;
  }

  function buildScriptNav(): NavItem[] {
    const items: NavItem[] = [];
    for (const s of scripts) {
      const id = "s:" + s.code;
      items.push({
        id,
        depth: 0,
        kind: "script",
        label: s.name,
        count: `${s.code} · ${fmt(s.chars)}`,
        expandable: true,
        detail: [
          ["Code", s.code],
          ["Name", s.name],
          ["French", s.french || "—"],
          ["Characters", fmt(s.chars)],
          ["Version", s.version || "—"],
          ["Notes", s.notes || ""],
        ],
      });
      if (!expandedIds.has(id)) continue;
      const blks = scriptBlocks[s.code] ?? [];
      for (const b of blks) {
        items.push({
          id: "sb:" + s.code + ":" + b.name,
          depth: 1,
          kind: "script-block",
          label: b.name,
          count: fmt(b.chars),
          blockName: b.name,
          version: latestVersion,
          detail: [
            ["Block", b.name],
            ["Script", s.name],
            ["Characters", fmt(b.chars)],
            ["Range(s)", b.ranges.map((r) => "U+" + r).join("  ")],
          ],
        });
      }
    }
    return items;
  }

  function buildDiffNav(): NavItem[] {
    if (!diff) return [];
    const items: NavItem[] = [];
    items.push({
      id: "dsum",
      depth: 0,
      kind: "summary",
      label: "Changes summary",
      detail: [
        ["From", diff.from],
        ["To", diff.to],
        ["Added characters", fmt(diff.added_characters)],
        ["Removed characters", fmt(diff.removed_characters)],
        ["Added blocks", fmt(diff.added_blocks.length)],
        ["Removed blocks", fmt(diff.removed_blocks.length)],
      ],
    });
    pushDiffGroup(items, "g-add", `Added blocks (${diff.added_blocks.length})`, diff.added_blocks, diff.to);
    pushDiffGroup(items, "g-rem", `Removed blocks (${diff.removed_blocks.length})`, diff.removed_blocks, diff.from);
    return items;
  }

  function pushDiffGroup(items: NavItem[], gid: string, label: string, list: any[], ver: string) {
    const grp: NavItem = { id: gid, depth: 0, kind: "group", label, expandable: true, detail: [] };
    items.push(grp);
    if (!expandedIds.has(gid)) return;
    for (const b of list) {
      items.push({
        id: gid + ":" + b.name,
        depth: 1,
        kind: "diff-block",
        label: b.name,
        count: fmt(b.chars),
        blockName: b.name,
        version: ver,
        detail: [
          ["Block", b.name],
          ["Range", `${uhex(b.start)}..${uhex(b.end)}`],
          ["Characters", fmt(b.chars)],
          ["Introduced", b.version ?? ver],
        ],
      });
    }
  }

  // ── interaction ──
  function toggle(id: string) {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expandedIds = next;
    if (next.has(id) && id.startsWith("s:")) loadScriptBlocks(id.slice(2));
  }
  async function loadScriptBlocks(code: string) {
    if (scriptBlocks[code]) return;
    try {
      const r = await fetch(API + "/unicode/scripts/blocks?code=" + encodeURIComponent(code));
      if (!r.ok) throw Error(String(r.status));
      const d = await r.json();
      scriptBlocks = { ...scriptBlocks, [code]: d.blocks ?? [] };
    } catch {
      /* ignore */
    }
  }

  async function select(item: NavItem) {
    sel = item;
    limit = 2000;
    if (item.kind === "block" || item.kind === "script-block" || item.kind === "diff-block") {
      await loadChars(item);
    } else {
      chars = [];
      charsLabel = "";
    }
  }

  async function loadChars(item: NavItem) {
    charsLoading = true;
    charsVersion = item.version ?? version;
    charsLabel = item.label;
    try {
      const r = await fetch(API + "/unicode/blocks/" + encodeURIComponent(item.blockName!) + "/characters?version=" + encodeURIComponent(charsVersion));
      if (!r.ok) throw Error(String(r.status));
      const d = await r.json();
      chars = d.characters ?? [];
    } catch {
      chars = [];
    }
    charsLoading = false;
  }

  function isGroup(item: NavItem): boolean {
    return item.expandable === true;
  }
  function viewChange(v: View) {
    view = v;
    filter = "";
    charsLabel = "";
    charsVersion = "";
    if (v === "blocks" || v === "planes") {
      const next = new Set(expandedIds);
      for (const k of [...next]) if (k.startsWith("p")) next.delete(k);
      if (v === "blocks") {
        for (const b of blocks) next.add("p" + (b.start >> 16));
      }
      expandedIds = next;
    }
  }
</script>

{#if show}
  <div class="ud" class:dragging class:resizing style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ud-header" onmousedown={onDragStart}>
      <span class="ud-title">Unicode</span>
      <select
        class="ud-version"
        bind:value={version}
        onchange={() => {
          sel = null;
          chars = [];
        }}
        style:display={view === "scripts" || view === "diff" ? "none" : ""}
      >
        {#each versions as v}
          <option value={v.version}>{v.version}{v.date ? " · " + v.date : ""}</option>
        {/each}
      </select>
      <div class="ud-views">
        {#each VIEWS as v}
          <button class:on={view === v[0]} onclick={() => viewChange(v[0])}>{v[1]}</button>
        {/each}
      </div>
      <span class="ud-stats">
        {#if history[view === "scripts" ? latestVersion : version]}
          {fmt(history[view === "scripts" ? latestVersion : version].assigned ?? 0)} assigned · {fmt(history[view === "scripts" ? latestVersion : version].blocks ?? 0)} blocks · {fmt(
            history[view === "scripts" ? latestVersion : version].scripts ?? 0,
          )} scripts
        {/if}
      </span>
      <button class="ud-close" onclick={onClose} title="Close">✕</button>
    </div>

    {#if view === "diff"}
      <div class="ud-diffbar">
        <label
          >From <select bind:value={diffFrom} onchange={() => loadDiff()}>
            {#each versions as v}<option value={v.version}>{v.version}</option>{/each}
          </select></label
        >
        <span>→</span>
        <label
          >To <select bind:value={diffTo} onchange={() => loadDiff()}>
            {#each versions as v}<option value={v.version}>{v.version}</option>{/each}
          </select></label
        >
      </div>
    {/if}

    <div class="ud-body">
      <div class="ud-nav">
        {#if view === "blocks" || view === "planes"}
          <input class="ud-filter" placeholder="Filter blocks…" bind:value={filter} />
        {/if}
        <div class="ud-navlist">
          {#if view === "blocks" || view === "planes"}
            {#if blocks.length === 0}<div class="ud-empty">Loading blocks…</div>{/if}
          {:else if view === "scripts"}
            {#if scripts.length === 0}<div class="ud-empty">Loading scripts…</div>{/if}
          {:else if view === "diff" && !diff}<div class="ud-empty">Loading diff…</div>{/if}

          {#each nav as item (item.id)}
            <div class="ud-item" class:sel={sel?.id === item.id} class:grp={isGroup(item)}>
              {#if isGroup(item)}
                <button class="ud-toggle" onclick={() => toggle(item.id)}>{expandedIds.has(item.id) ? "▾" : "▸"}</button>
              {:else}
                <span class="ud-tsp"></span>
              {/if}
              <button class="ud-main" style:padding-left={item.depth === 0 ? "6px" : "26px"} onclick={() => select(item)}>
                <span class="ud-label">{item.label}</span>
                {#if item.count}<span class="ud-count">{item.count}</span>{/if}
              </button>
            </div>
          {/each}
        </div>
      </div>

      <div class="ud-right">
        <div class="ud-detail">
          {#if sel}
            <div class="ud-dtitle">{sel.label}</div>
            <table class="ud-dtable">
              <tbody>
                {#each sel.detail as row}
                  <tr><td class="ud-dk">{row[0]}</td><td class="ud-dv">{row[1]}</td></tr>
                {/each}
              </tbody>
            </table>
          {:else}
            <div class="ud-dtitle">Select an item</div>
            <div class="ud-empty">Choose a block, script or version change in the left panel.</div>
          {/if}
        </div>

        <div class="ud-chars">
          <div class="ud-chars-head">
            <span class="ud-chars-label">{charsLabel}{charsVersion && charsLabel ? ` · v${charsVersion}` : ""}</span>
            {#if charsLabel}
              <span class="ud-chars-count">{fmt(chars.length)} assigned</span>
            {/if}
            {#if chars.length > limit}
              <button class="ud-more" onclick={() => (limit += 2000)}>Show more (+{fmt(Math.min(2000, chars.length - limit))})</button>
            {/if}
          </div>
          <div class="ud-chars-body">
            {#if charsLoading}
              <div class="ud-empty">Loading characters…</div>
            {:else if chars.length === 0}
              <div class="ud-empty">{charsLabel ? "No assigned characters." : "Select a block to view its characters."}</div>
            {:else}
              <div class="ud-grid">
                {#each chars.slice(0, limit) as c}
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <button class="ud-cg" title="{uhex(c.codepoint)}  {c.name}" onclick={() => onGotoCP(c.codepoint)}>{c.char}</button>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="ud-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .ud {
    position: fixed;
    z-index: 300;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 720px;
    min-height: 320px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 24px);
    user-select: none;
  }
  .ud.dragging,
  .ud.resizing {
    opacity: 0.92;
    transition: none;
  }
  .ud-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--ac);
    color: #fff;
    cursor: grab;
    flex-shrink: 0;
    user-select: none;
  }
  .ud-header:active {
    cursor: grabbing;
  }
  .ud-title {
    font-size: 13px;
    font-weight: 600;
  }
  .ud-version {
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
  }
  .ud-version option {
    color: #000;
    background: #fff;
  }
  .ud-views {
    display: flex;
    gap: 4px;
  }
  .ud-views button {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .ud-views button.on {
    background: rgba(255, 255, 255, 0.95);
    color: var(--ac);
    font-weight: 600;
  }
  .ud-stats {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.9);
    margin-left: auto;
    white-space: nowrap;
  }
  .ud-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 4px;
    border-radius: 4px;
  }
  .ud-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .ud-diffbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--bg3, #26272b);
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    font-size: 12px;
    flex-shrink: 0;
  }
  .ud-diffbar select {
    font-size: 12px;
    margin-left: 4px;
  }
  .ud-body {
    display: flex;
    flex: 1;
    min-height: 0;
  }
  .ud-nav {
    width: 300px;
    flex-shrink: 0;
    border-right: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .ud-filter {
    margin: 6px 8px;
    padding: 4px 8px;
    font-size: 12px;
    border-radius: 5px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg, #eee);
    flex-shrink: 0;
  }
  .ud-navlist {
    flex: 1;
    overflow: auto;
    min-height: 0;
    padding: 4px 0 12px;
  }
  .ud-item {
    display: flex;
    align-items: center;
    font-size: 12px;
  }
  .ud-toggle {
    background: none;
    border: none;
    color: var(--fg, #eee);
    cursor: pointer;
    width: 18px;
    flex-shrink: 0;
    font-size: 10px;
  }
  .ud-tsp {
    width: 18px;
    flex-shrink: 0;
  }
  .ud-main {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: var(--fg, #eee);
    cursor: pointer;
    text-align: left;
    padding: 3px 6px;
    border-radius: 4px;
    min-width: 0;
  }
  .ud-main:hover {
    background: var(--bg3, #2c2d31);
  }
  .ud-item.sel .ud-main {
    background: var(--ac);
    color: #fff;
  }
  .ud-item.grp .ud-main {
    font-weight: 600;
  }
  .ud-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .ud-count {
    margin-left: auto;
    color: inherit;
    opacity: 0.75;
    font-size: 11px;
    flex-shrink: 0;
  }
  .ud-empty {
    padding: 12px;
    font-size: 12px;
    color: var(--fg2, #999);
  }
  .ud-right {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .ud-detail {
    flex-shrink: 0;
    padding: 8px 12px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    max-height: 40%;
    overflow: auto;
  }
  .ud-dtitle {
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
  }
  .ud-dtable {
    border-collapse: collapse;
    font-size: 12px;
  }
  .ud-dtable td {
    padding: 1px 10px 1px 0;
    vertical-align: top;
  }
  .ud-dk {
    color: var(--fg2, #999);
    white-space: nowrap;
  }
  .ud-dv {
    word-break: break-all;
  }
  .ud-chars {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .ud-chars-head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 12px;
    font-size: 12px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    flex-shrink: 0;
  }
  .ud-chars-label {
    font-weight: 600;
  }
  .ud-chars-count {
    opacity: 0.75;
  }
  .ud-more {
    margin-left: auto;
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 5px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg, #eee);
    cursor: pointer;
  }
  .ud-chars-body {
    flex: 1;
    overflow: auto;
    min-height: 0;
    padding: 8px;
  }
  .ud-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(30px, 1fr));
    gap: 2px;
  }
  .ud-cg {
    aspect-ratio: 1;
    font-size: 15px;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg3, #26272b);
    border: 1px solid var(--br, rgba(128, 128, 128, 0.25));
    border-radius: 4px;
    cursor: pointer;
    color: var(--fg, #eee);
    padding: 0;
    font-family: "Segoe UI Symbol", "Noto Sans Symbols", "Arial Unicode MS", serif;
  }
  .ud-cg:hover {
    background: var(--ac);
    color: #fff;
  }
  .ud-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
