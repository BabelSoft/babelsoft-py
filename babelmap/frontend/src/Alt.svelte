<script lang="ts">
  import type { GridPage, BlockInfo } from "./lib/types";
  import { t, lang, langList, localizedMenus, type LangDef } from "./lib/i18n.svelte";

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
  let gv = $state("");
  let sv = $state("");
  let blocks = $state<BlockInfo[]>([]);
  let sblock = $state("");
  let sr = $state(-1);
  let sc = $state(-1);
  let om = $state(-1);
  let showLang = $state(false);
  let editVisible = $state(true);
  let _navBusy = false;

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

  function click(r: number, c: number) {
    sr = r;
    sc = c;
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
  function selCp() {
    if (sr < 0 || !grid) return null;
    return grid.cells[sr]?.[sc]?.codepoint ?? null;
  }
  function selName() {
    if (sr < 0 || !grid) return "";
    return grid.cells[sr]?.[sc]?.char_name || "";
  }
  let visibleRows = $derived(grid ? grid.cells.map((row, ri) => ({ row, ri, vis: row.some((c) => c.codepoint >= 0 && !c.reserved) })).filter((r) => r.vis) : []);
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
      click(sr, sc);
      e.preventDefault();
    } else if (e.key === "PageUp") {
      nav(-8);
      e.preventDefault();
    } else if (e.key === "PageDown") {
      nav(8);
      e.preventDefault();
    } else if (e.key === "Escape") {
      om = -1;
    }
  }

  // Close menu on outside click
  function onGlobalClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (!t.closest(".mw")) om = -1;
    if (!t.closest(".lang-wrap")) showLang = false;
  }

  interface MI {
    l: string;
    k?: string;
    sub?: MI[];
  }
  // Derive localized menus reactively — updates when lang.v changes
  let _menus = $derived(localizedMenus());
  function mc(i: number) {
    om = om === i ? -1 : i;
  }
  function ma(item: MI) {
    om = -1;
    if (item.l === t("view.toggle_theme")) dark = !dark;
    else if (item.l === t("edit.clear")) buf = "";
    else if (item.l === t("edit.glyph_mode")) glyph = true;
    else if (item.l === t("edit.text_mode")) glyph = false;
    else if (item.l === t("edit.char")) mode = "char";
    else if (item.l === t("edit.ncr_hex")) mode = "ncr_hex";
    else if (item.l === t("edit.ncr_dec")) mode = "ncr_dec";
    else if (item.l === t("edit.html")) mode = "html";
    else if (item.l === t("edit.ucn")) mode = "ucn";
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

<svelte:window onclick={onGlobalClick} onkeydown={onKey} />

<div class="app" class:dark>
  <nav class="mb">
    {#each _menus as m, i}
      <div class="mw">
        <button class="mbtn" class:on={om === i} onclick={() => mc(i)}>{m.label}</button>
        {#if om === i}<div class="mdrop" role="menu">
            {#each m.items as it}{#if it.sub}
                <div class="msw">
                  <div class="mi mst">{it.l}<span class="ar">▶</span></div>
                  <div class="msub">
                    {#each it.sub as s}<div class="mi" role="menuitem" onclick={() => ma(s)} onkeydown={(e) => e.key === "Enter" && ma(s)} tabindex="0">
                        {s.l}
                      </div>{/each}
                  </div>
                </div>
              {:else}<div class="mi" role="menuitem" onclick={() => ma(it)} onkeydown={(e) => e.key === "Enter" && ma(it)} tabindex="0">{it.l}<span class="sk">{it.k || ""}</span></div>{/if}{/each}
          </div>{/if}
      </div>
    {/each}
    <span class="msp"></span>
    <!-- Language Switcher -->
    <div class="lang-wrap">
      <button class="lang-btn" onclick={() => (showLang = !showLang)} title={t("lang.title")}>
        {langList.find((l: LangDef) => l.code === lang.v)?.nativeName || "English"}
      </button>
      {#if showLang}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="lang-drop" onkeydown={(e) => e.key === "Escape" && (showLang = false)}>
          {#each langList as l}
            <div
              class="lang-item"
              class:active={lang.v === l.code}
              onclick={() => {
                lang.v = l.code;
                showLang = false;
              }}
              onkeydown={(e) => e.key === "Enter" && ((lang.v = l.code), (showLang = false))}
              role="menuitem"
              tabindex="0"
            >
              {l.nativeName}
            </div>
          {/each}
        </div>
      {/if}
    </div>
    <button class="tbtn" onclick={() => (dark = !dark)}>{dark ? "☀" : "☾"}</button>
  </nav>

  <div class="tabs">
    {#each PLANES as p}<button class:on={plane === p.id} onclick={() => goPlane(p.id)}>{p.l}</button>{/each}
  </div>

  <div class="main">
    <div class="gw">
      <div class="gh">
        <span class="gt"
          >{#if loading}{t("general.loading")}{:else if err}{err}{:else if grid}{grid.block_name}{:else}{t("general.ready")}{/if}</span
        >{#if grid}<span class="gr">U+{grid.block_start.toString(16).toUpperCase().padStart(4, "0")}–U+{grid.block_end.toString(16).toUpperCase().padStart(4, "0")}</span><span class="gc"
            >({grid.block_assigned}/{grid.block_count})</span
          >{/if}
      </div>
      <div class="ch">
        <span></span>{#each Array(16) as _, c}<span>_{c.toString(16).toUpperCase()}</span>{/each}
      </div>
      <div
        class="gb"
        role="grid"
        tabindex="0"
        onwheel={(e: WheelEvent) => {
          e.preventDefault();
          nav(e.deltaY > 0 ? 1 : -1);
        }}
        onclick={(e) => {
          const b = (e.target as HTMLElement).closest("button[data-ri]") as HTMLElement | null;
          if (b) {
            click(+b.dataset.ri!, +b.dataset.ci!);
          }
        }}
        onkeydown={(e) => {
          if (!(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) e.preventDefault();
        }}
      >
        {#if grid}{#each grid.cells as row, ri (ri)}
            {@const isBB = grid.block_boundaries.includes(ri)}
            {#if row.some((c) => c.codepoint >= 0) || grid.cells.slice(ri).every((r) => r.every((c) => c.codepoint < 0))}
              <span class="rl" class:bb={isBB}
                >{row.every((c) => c.codepoint < 0)
                  ? "\u2014"
                  : (plane * 0x10000 + (grid.row_bases?.[ri] ?? (grid.scroll_position + ri) * 16)).toString(16).toUpperCase().padStart(4, "0").slice(0, -1) + "_"}</span
              >
              {#each row as cell, ci (ci)}{@const s = sr === ri && sc === ci}
                <button
                  class="cel"
                  class:empty={cell.codepoint < 0}
                  class:reserved={cell.reserved === true}
                  class:sel={s}
                  class:bb={isBB}
                  data-ri={ri}
                  data-ci={ci}
                  title={cell.char_name || (cell.codepoint >= 0 ? `U+${cell.codepoint.toString(16).toUpperCase().padStart(4, "0")}` : "")}
                >
                  {#if cell.codepoint >= 0}<span class="gc2">{String.fromCodePoint(cell.codepoint)}</span>{/if}
                </button>
              {/each}
            {/if}
          {/each}{/if}
      </div>
    </div>

    <aside class="rn">
      <div class="vs">
        <input
          type="range"
          {...{ orient: "vertical" }}
          min="0"
          max={grid?.max_scroll ?? 4095}
          value={scroll}
          oninput={(e) => {
            scroll = parseInt((e.target as HTMLInputElement).value) || 0;
            load(undefined, scroll, true);
          }}
        />
      </div>
      <div class="nb">
        <button onclick={() => goPlane(0)} title={t("nav.plane_start")}>⏮️</button>
        <button onclick={() => goPlane(16)} title={t("nav.plane_end")}>⏭️</button>
        <button onclick={() => nblock(-1)} title={t("nav.prev_block")}>⏪</button>
        <button onclick={() => nblock(1)} title={t("nav.next_block")}>⏩</button>
        <button onclick={() => nav(-8)} title={t("nav.page_up")}>⬆️</button>
        <button onclick={() => nav(8)} title={t("nav.page_down")}>⬇️</button>
        <button
          onclick={() => {
            sr = 0;
          }}
          title={t("nav.row_start")}>⤒</button
        >
        <button
          onclick={() => {
            sr = 7;
          }}
          title={t("nav.row_end")}>⤓</button
        >
        <button onclick={() => {}} title={t("nav.ivs")} disabled>〰️</button>
        <button
          onclick={() => {
            const cp = Math.floor(Math.random() * 0x110000);
            gv = cp.toString(16).toUpperCase();
            doGo();
          }}
          title={t("nav.random")}>🎲</button
        >
      </div>
    </aside>
  </div>

  <div class="ir">
    <input
      class="ir1"
      readonly
      value={selInfo ? `U+${selInfo.hex} ${selInfo.char} ${selInfo.name}` : ""}
      placeholder={t("general.select_char")}
      onclick={(e) => {
        const t = e.target as HTMLInputElement;
        if (t.value) {
          navigator.clipboard.writeText(t.value);
        }
      }}
    />
    <input class="ir2" readonly value={selInfo?.dec || ""} />
  </div>

  <div class="bot">
    <div class="br1">
      <fieldset>
        <legend>{t("bottom.select_block")}</legend><select
          value={sblock}
          onchange={(e: any) => {
            sblock = e.target.value;
            doBlock();
          }}
          ><option value="">-- {t("bottom.select_block")} --</option>{#each blocks as b}<option value={b.name}>{b.name}</option>{/each}</select
        >
      </fieldset>
      <fieldset class="fs">
        <legend>{t("bottom.search_name")}</legend><input
          type="text"
          bind:value={sv}
          onkeydown={(e) => {
            if (e.key === "Enter") doSearch();
          }}
        /><button onclick={doSearch}>🔍</button>
      </fieldset>
      <fieldset class="fg">
        <legend>{t("bottom.goto_cp")}</legend><input
          type="text"
          bind:value={gv}
          placeholder={t("general.hex")}
          onkeydown={(e) => {
            if (e.key === "Enter") doGo();
          }}
        /><button onclick={doGo}>{t("bottom.go")}</button>
      </fieldset>
    </div>
    <div class="br2">
      <label class="rd"><input type="radio" name="fm" checked /> {t("font.composite_font")}</label><button class="sb">{t("font.configure")}</button>
      <label class="rd"><input type="radio" name="fm" /> {t("font.single_font")}</label><select class="fsel"><option>Arial</option></select>
      <input
        type="number"
        class="fsz"
        value={fsize}
        min="8"
        max="72"
        onchange={(e: any) => {
          fsize = parseInt(e.target.value) || 16;
          load();
        }}
      /><button class="sb" style="margin-left:auto">{t("font.show")}</button>
    </div>
    <fieldset class="eb">
      <legend>{t("bottom.edit_buffer")}</legend>
      <textarea bind:value={buf} rows={3} spellcheck={false} placeholder="Click cells to add. Arrow keys navigate. Enter to add selected."></textarea>
      <div class="ebc">
        <div class="ebr">
          <label class="rd"><input type="radio" name="rdr" checked={glyph} onchange={() => (glyph = true)} /> {t("bottom.glyph")}</label>
          <label class="rd"><input type="radio" name="rdr" checked={!glyph} onchange={() => (glyph = false)} /> {t("bottom.text")}</label>
          <label class="ck"><input type="checkbox" /> {t("bottom.colour")}</label>
        </div>
        <div class="ebr">
          {#each [{ l: t("edit.char"), v: "char" }, { l: t("edit.ncr_hex"), v: "ncr_hex" }, { l: t("edit.ncr_dec"), v: "ncr_dec" }, { l: t("edit.html"), v: "html" }, { l: t("edit.ucn"), v: "ucn" }] as m}
            <label class="rd"><input type="radio" name="em" value={m.v} checked={mode === m.v} onchange={() => (mode = m.v as any)} /> {m.l}</label>{/each}
        </div>
        <div class="ebr ebtns">
          <button class="sb" onclick={() => (editVisible = !editVisible)}>{t("bottom.hide")}</button>
          <button
            class="sb"
            onclick={() => {
              /* save */
            }}>{t("bottom.save")}</button
          >
          <button class="sb" onclick={() => (buf = "")}>{t("bottom.clear")}</button>
          <button
            class="sb"
            onclick={() => {
              navigator.clipboard.writeText(conv());
            }}>{t("bottom.copy")}</button
          >
          <button
            class="sb"
            onclick={() => {
              navigator.clipboard.writeText(conv());
              buf = "";
            }}>{t("bottom.cut")}</button
          >
        </div>
      </div>
    </fieldset>
  </div>

  <footer class="st">
    <span
      >{#if sr >= 0 && grid}U+{selCp()!.toString(16).toUpperCase().padStart(4, "0")} – {selName()}{:else if grid}{grid.block_name}{:else}{t("general.ready")}{/if}</span
    >
    <span>{PLANES.find((p) => p.id === plane)?.l} · Arial {fsize}px · {grid ? `U+${(plane * 0x10000 + (grid.row_bases[0] ?? 0)).toString(16).toUpperCase().padStart(4, "0")}` : ""}</span>
  </footer>
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
  }
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  button {
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    border: none;
    border-radius: 8px;
    transition: all 0.15s;
  }
  input,
  select,
  textarea {
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
  input:focus,
  select:focus,
  textarea:focus {
    border-color: var(--ac);
    box-shadow: 0 0 0 3px rgba(92, 124, 250, 0.12);
  }
  fieldset {
    border: 1px solid var(--bd);
    border-radius: 10px;
    padding: 4px 10px 6px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  fieldset legend {
    font-size: 10px;
    color: var(--fg3);
    padding: 0 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .mb {
    display: flex;
    align-items: center;
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    padding: 0 8px;
    flex-shrink: 0;
    height: 36px;
    z-index: 100;
    box-shadow: var(--sh);
  }
  .mw {
    position: relative;
  }
  .mbtn {
    background: transparent;
    color: var(--fg2);
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 8px;
  }
  .mbtn:hover,
  .mbtn.on {
    background: var(--bg3);
    color: var(--fg);
  }
  .mdrop {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 220px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
    padding: 6px;
    z-index: 200;
  }
  .mi {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 12px;
    color: var(--fg);
    font-size: 12px;
    cursor: pointer;
    border-radius: 8px;
    white-space: nowrap;
  }
  .mi:hover {
    background: var(--ac);
    color: #fff;
  }
  .sk {
    color: var(--fg3);
    font-size: 10px;
    margin-left: 20px;
  }
  .mi:hover .sk {
    color: rgba(255, 255, 255, 0.6);
  }
  .msw {
    position: relative;
  }
  .mst {
    display: flex;
    justify-content: space-between;
  }
  .ar {
    font-size: 10px;
    margin-left: 8px;
    color: var(--fg3);
  }
  .msub {
    display: none;
    position: absolute;
    left: 100%;
    top: -6px;
    min-width: 180px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
    padding: 6px;
    z-index: 201;
  }
  .msw:hover .msub {
    display: block;
  }
  .msp {
    flex: 1;
  }
  .tbtn {
    background: transparent;
    color: var(--fg);
    font-size: 16px;
    padding: 4px 10px;
    border-radius: 8px;
  }
  .tbtn:hover {
    background: var(--bg3);
  }

  /* ── Language Switcher ── */
  .lang-wrap {
    position: relative;
    margin-right: 2px;
  }
  .lang-btn {
    background: transparent;
    color: var(--fg2);
    font-size: 11px;
    padding: 5px 10px;
    border-radius: 8px;
    border: 1px solid transparent;
    white-space: nowrap;
  }
  .lang-btn:hover {
    background: var(--bg3);
    color: var(--fg);
  }
  .lang-drop {
    position: absolute;
    top: 100%;
    right: 0;
    min-width: 140px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
    padding: 6px;
    z-index: 200;
    max-height: 260px;
    overflow-y: auto;
  }
  .lang-item {
    padding: 6px 12px;
    font-size: 12px;
    color: var(--fg);
    cursor: pointer;
    border-radius: 8px;
    white-space: nowrap;
  }
  .lang-item:hover,
  .lang-item.active {
    background: var(--ac);
    color: #fff;
  }
  .tabs {
    display: flex;
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    padding: 0 8px;
    gap: 2px;
    flex-shrink: 0;
  }
  .tabs button {
    background: transparent;
    color: var(--fg3);
    padding: 6px 16px;
    font-size: 11px;
    font-weight: 700;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    letter-spacing: 0.3px;
  }
  .tabs button:hover {
    color: var(--fg);
    background: var(--bg3);
  }
  .tabs button.on {
    color: var(--ac);
    border-bottom-color: var(--ac);
  }
  .main {
    flex: 1;
    display: flex;
    overflow: hidden;
    min-height: 0;
    background: var(--bg);
  }
  .gw {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 6px 10px;
    gap: 0;
    min-height: 0;
  }
  .gh {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 6px;
    flex-shrink: 0;
  }
  .gt {
    font-size: 14px;
    font-weight: 700;
    color: var(--fg);
  }
  .gr {
    font-family: monospace;
    font-size: 11px;
    color: var(--ac);
  }
  .gc {
    font-size: 11px;
    color: var(--fg3);
  }
  .ch {
    display: grid;
    grid-template-columns: 64px repeat(16, 1fr);
    flex-shrink: 0;
    border-bottom: 1px solid var(--bd);
  }
  .ch span {
    text-align: center;
    font-size: 13px;
    font-family: monospace;
    color: var(--fg3);
    padding: 2px 0;
  }
  .gb {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    display: grid;
    grid-template-columns: 64px repeat(16, 1fr);
    grid-auto-rows: 1fr;
    gap: 0;
    min-height: 0;
  }
  .gb::-webkit-scrollbar {
    width: 6px;
  }
  .gb::-webkit-scrollbar-thumb {
    background: var(--sc);
    border-radius: 3px;
  }
  .rl {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 6px;
    font-size: 13px;
    font-family: monospace;
    color: var(--fg3);
    background: var(--bg2);
    border-bottom: 1px solid var(--bd);
    position: sticky;
    left: 0;
    z-index: 1;
  }

  .cel {
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid var(--bd);
    border-right: 1px solid var(--bd);
    background: var(--celbg);
    padding: 0;
    border-radius: 0;
    color: var(--fg);
    outline: none;
  }
  .cel.bb {
    border-top: 2px solid var(--fg);
  }
  .cel:hover {
    background: var(--celh);
  }
  .cel.empty {
    background: var(--bg3);
    opacity: 0.5;
  }
  .cel.reserved {
    background: var(--bg3);
    opacity: 0.55;
  }
  .cel.reserved .gc2 {
    opacity: 0.35;
  }
  .cel.sel {
    background: var(--ac) !important;
    color: #fff !important;
    z-index: 1;
    border-radius: 2px;
    outline: none;
  }
  .gc2 {
    font-size: clamp(15px, 3.5vh, 24px);
    line-height: 1;
    color: inherit;
  }
  .rn {
    display: flex;
    flex-direction: row;
    gap: 0;
    background: var(--bg2);
    border-left: 1px solid var(--bd);
    flex-shrink: 0;
  }
  .vs {
    width: 24px;
    display: flex;
    align-items: stretch;
    padding: 4px 0 4px 2px;
  }
  .vs input {
    writing-mode: vertical-lr;
    width: 100%;
    accent-color: var(--ac);
  }
  .ir {
    display: flex;
    gap: 6px;
    padding: 4px 10px;
    background: var(--bg2);
    border-top: 1px solid var(--bd);
    flex-shrink: 0;
  }
  .ir1 {
    flex: 1;
    font-family: monospace;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 4px 8px;
    outline: none;
    cursor: text;
  }
  .ir2 {
    width: 80px;
    text-align: center;
    font-family: monospace;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 4px 8px;
    outline: none;
    cursor: text;
  }
  .nb {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 2px;
    width: 36px;
  }
  .nb button {
    width: 100%;
    height: 28px;
    font-size: 14px;
    background: var(--bg3);
    color: var(--fg2);
    border: 1px solid var(--bd);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }
  .nb button:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .nb button:disabled {
    opacity: 0.3;
    cursor: default;
  }
  .nb button:disabled:hover {
    background: var(--bg3);
    color: var(--fg2);
    border-color: var(--bd);
  }
  .bot {
    flex-shrink: 0;
    background: var(--bg2);
    border-top: 2px solid var(--bd);
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.04);
  }
  .br1 {
    display: flex;
    gap: 8px;
  }
  .br1 fieldset:first-child {
    max-width: 190px;
  }
  .br1 fieldset:first-child select {
    width: 100%;
  }
  .fs {
    flex: 2;
  }
  .fs input {
    flex: 1;
    width: 0;
  }
  .fg {
    flex: 0 0 auto;
    min-width: 130px;
  }
  .fg input {
    width: 70px;
    font-family: monospace;
  }
  .br1 button,
  .sb {
    height: 26px;
    padding: 0 10px;
    font-size: 11px;
    font-weight: 600;
    background: var(--bg3);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
  }
  .br1 button:hover,
  .sb:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .br2 {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .rd {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg);
    cursor: pointer;
    font-weight: 500;
  }
  .rd input {
    accent-color: var(--ac);
  }
  .ck {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--fg);
    cursor: pointer;
  }
  .ck input {
    accent-color: var(--ac);
  }
  .fsel {
    width: 140px;
  }
  .fsz {
    width: 50px;
    text-align: center;
    font-family: monospace;
    background: var(--bg) !important;
  }
  .eb textarea {
    width: 100%;
    flex: 1;
    resize: none;
    font-family: monospace;
    font-size: 12px;
    min-height: 52px;
    line-height: 1.5;
  }
  .ebc {
    margin-top: 3px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .ebr {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .ebtns {
    padding-top: 4px;
    border-top: 1px solid var(--bd);
  }
  .sep {
    flex: 1;
  }
  .st {
    display: flex;
    justify-content: space-between;
    padding: 3px 14px;
    background: var(--bg2);
    border-top: 1px solid var(--bd);
    font-size: 11px;
    color: var(--fg3);
    flex-shrink: 0;
  }
</style>
