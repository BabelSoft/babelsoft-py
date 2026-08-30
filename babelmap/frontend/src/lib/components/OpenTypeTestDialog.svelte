<script lang="ts">
  import Icon from "../icons/Icon.svelte";

  // OpenType Test Framework — a full Crowbar-style text shaping debugger.
  // Backend: babelmap/backend/opentype.py (HarfBuzz via uharfbuzz).

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();
  const API = "http://127.0.0.1:18080/api";

  // ── fonts ──
  let fonts = $state<any[]>([]);
  let fontPath = $state("");
  let fontB64 = $state("");
  let fontName = $state("");
  let lastFontKey = $state("");

  // ── text + options ──
  let text = $state("ffi fi fl");
  let direction = $state("auto");
  let script = $state("auto");
  let language = $state("");
  let cluster = $state("monotone_graphemes");
  let bufferFlags = $state<string[]>([]);
  let showAllLookups = $state(false);
  let glyphMode = $state(false);
  let engine = $state("harfbuzz");
  let size = $state(96);
  let features = $state<Record<string, "on" | "off" | "default">>({});
  let featureString = $state("");
  let variations = $state<Record<string, number>>({});
  let featureTags = $state<{ gsub: string[]; gpos: string[] }>({
    gsub: [],
    gpos: [],
  });

  const DIRECTIONS: [string, string][] = [
    ["auto", "Automatically detect"],
    ["ltr", "Left to right"],
    ["rtl", "Right to left"],
    ["ttb", "Top to bottom"],
    ["btt", "Bottom to top"],
  ];
  const CLUSTERS: [string, string][] = [
    ["monotone_graphemes", "Monotone graphemes"],
    ["monotone_characters", "Monotone characters"],
    ["characters", "Characters"],
    ["graphemes", "Graphemes"],
  ];
  const BUFFER_FLAGS: [string, string][] = [
    ["BOT", "Beginning of text paragraph"],
    ["EOT", "End of text paragraph"],
    ["PRESERVE_DEFAULT_IGNORABLES", "Preserve default ignorables"],
    ["REMOVE_DEFAULT_IGNORABLES", "Remove default ignorables"],
    ["DO_NOT_INSERT_DOTTED_CIRCLE", "Do not insert dotted circle"],
    ["VERIFY", "Verify"],
    ["PRODUCE_UNSAFE_TO_CONCAT", "Produce unsafe to concat"],
    ["PRODUCE_SAFE_TO_INSERT_TATWEEL", "Produce safe to insert tatweel"],
  ];
  const PALETTE = [
    "#C23B23",
    "#c79c52",
    "#857b2a",
    "#03C03C",
    "#579ABE",
    "#976ED7",
    "#e6194b",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#808000",
    "#008080",
    "#e6beff",
    "#9a6324",
    "#800000",
    "#aaffc3",
  ];

  // ── meta (script/language lists) + font info ──
  let meta = $state<{
    scripts: { tag: string; label: string }[];
    languages: { tag: string; label: string }[];
  }>({ scripts: [], languages: [] });
  let fontInfo = $state<any>(null);
  let hbVersion = $state("");

  // ── result ──
  let result = $state<any>(null);
  let glyphNames = $state<Record<number, string>>({});
  let loading = $state(false);
  let err = $state("");
  let shownSvg = $state("");
  let shownUpem = $state(2048);
  let shownGlyphs = $state<any[]>([]);
  let hoverCl = $state(-1);
  let hoverStageIx = $state(-1);

  // ── drag / position state ──
  let x = $state(180);
  let y = $state(90);
  let w = $state(
    Math.min(
      1280,
      (typeof window !== "undefined" ? window.innerWidth : 1280) - 32,
    ),
  );
  let h = $state(
    Math.min(
      780,
      (typeof window !== "undefined" ? window.innerHeight : 780) - 40,
    ),
  );
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
    w = Math.max(840, winStartW + (e.clientX - resizeStartX));
    h = Math.max(440, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  // ── helpers ──
  function hex4(n: number): string {
    return n.toString(16).toUpperCase().padStart(4, "0");
  }
  function paletteFor(cl: number): string {
    return PALETTE[Math.abs(cl) % PALETTE.length];
  }
  function fgColor(): string {
    // SVG 输出区域为白底，固定深色字形以保证可见。
    return "#1a1a1a";
  }
  function fontKey(): string {
    return fontB64 ? "upload:" + (fontName || "font") : "sys:" + fontPath;
  }
  function glyphName(g: any): string {
    return glyphNames[g.g] ?? "U+" + hex4(g.g);
  }
  function isSupportedScript(tag: string): boolean {
    return !!fontInfo?.supported_scripts?.includes(String(tag).toLowerCase());
  }
  function isSupportedLang(tag: string): boolean {
    return !!fontInfo?.supported_languages?.includes(String(tag).toUpperCase());
  }
  function stageTag(m: string): string | null {
    const mm = m.match(/start table (\w+)/);
    return mm ? mm[1] : null;
  }
  function featureOf(msg: string): string | null {
    const m = msg.match(/feature '(\w+)'/);
    return m ? m[1] : null;
  }
  function lookupOf(msg: string): number | null {
    const m = msg.match(/lookup (\d+)/);
    return m ? parseInt(m[1], 10) : null;
  }
  function debugFor(msg: string, stage: string) {
    const ix = lookupOf(msg);
    if (ix === null || !fontInfo?.debg) return null;
    try {
      const d = fontInfo.debg["com.github.fonttools.feaLib"]?.[stage]?.[ix];
      if (!d) return null;
      return { source: d[0], name: d[1] };
    } catch {
      return null;
    }
  }

  $effect(() => {
    if (show) init();
  });
  async function init() {
    try {
      const [fr, mr] = await Promise.all([
        fetch(API + "/opentype/fonts"),
        fetch(API + "/opentype/meta"),
      ]);
      const fd = await fr.json();
      fonts = fd.fonts ?? [];
      if (mr.ok) meta = (await mr.json()) ?? meta;
      if (fonts.length && !fontPath && !fontB64) fontPath = fonts[0].path;
      if (text) shape();
    } catch {
      /* ignore */
    }
  }

  function onFontSelect() {
    fontB64 = "";
    fontName = "";
    shape();
  }

  function onUpload(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const fr = new FileReader();
    fr.onload = () => {
      const b64 = (fr.result as string).split(",")[1] ?? fr.result;
      fontB64 = b64;
      fontPath = "";
      fontName = file.name;
      shape();
    };
    fr.readAsDataURL(file);
  }

  function featureDict(): Record<string, boolean> {
    const out: Record<string, boolean> = {};
    for (const [k, v] of Object.entries(features)) {
      if (v === "on") out[k] = true;
      else if (v === "off") out[k] = false;
    }
    return out;
  }

  async function shape() {
    if (!fontPath && !fontB64) return;
    // Reset features/variations when the font changes.
    const key = fontKey();
    if (key !== lastFontKey) {
      lastFontKey = key;
      features = {};
      featureString = "";
      variations = {};
      fontInfo = null;
      hbVersion = "";
    }
    loading = true;
    err = "";
    const body: any = {
      text,
      direction,
      script,
      language,
      cluster,
      engine,
      flags: bufferFlags,
      features: featureString.trim() ? featureString : featureDict(),
      variations: Object.keys(variations).length ? variations : undefined,
      show_all_lookups: showAllLookups,
      glyph_mode: glyphMode,
      render: true,
      size,
      color: fgColor(),
    };
    if (fontB64) body.font_b64 = fontB64;
    else body.font_path = fontPath;
    try {
      const r = await fetch(API + "/opentype/shape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) {
        err = d.error ?? String(r.status);
        loading = false;
        return;
      }
      result = d;
      glyphNames = d.glyph_names ?? {};
      featureTags = d.features ?? { gsub: [], gpos: [] };
      fontInfo = d.font_info ?? null;
      hbVersion = d.font_info?.hb_version ?? "";
      const next = { ...features };
      for (const t of [...featureTags.gsub, ...featureTags.gpos])
        if (!(t in next)) next[t] = "default";
      features = next;
      shownGlyphs = d.final ?? [];
      shownUpem = d.upem ?? 2048;
      shownSvg = d.svg ?? "";
      hoverCl = -1;
      hoverStageIx = -1;
    } catch (e: any) {
      err = e.message;
    }
    loading = false;
  }

  let renderTimer: any;
  function renderGlyphs(glyphs: any[], cl: number) {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(async () => {
      try {
        const body: any = {
          glyphs,
          upem: shownUpem,
          size,
          color: fgColor(),
          highlight_cl: cl,
        };
        if (Object.keys(variations).length) body.variations = variations;
        if (fontB64) body.font_b64 = fontB64;
        else body.font_path = fontPath;
        const r = await fetch(API + "/opentype/render", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (r.ok) {
          const d = await r.json();
          shownSvg = d.svg;
        }
      } catch {
        /* ignore */
      }
    }, 120);
  }

  function onStageEnter(stage: any) {
    if (stage.glyphs && stage.glyphs.length) {
      shownGlyphs = stage.glyphs;
      renderGlyphs(stage.glyphs, hoverCl);
    }
  }
  function onStageLeave() {
    shownGlyphs = result?.final ?? [];
    renderGlyphs(result?.final ?? [], hoverCl);
  }
  function onGlyphEnter(g: any) {
    hoverCl = g.cl;
    renderGlyphs(shownGlyphs, g.cl);
  }
  function onGlyphLeave() {
    hoverCl = -1;
    renderGlyphs(shownGlyphs, -1);
  }

  function toggleFeature(tag: string) {
    const cur = features[tag];
    features = {
      ...features,
      [tag]: cur === "on" ? "off" : cur === "off" ? "default" : "on",
    };
    shape();
  }
  function onOptionChange() {
    shape();
  }

  // diff a row's glyphs vs the previous row (Crowbar highlight)
  function diffColors(prev: any[] | null, cur: any[]): (string | null)[] {
    if (!prev) return cur.map(() => null);
    return cur.map((g, i) => {
      const p = prev[i];
      if (!p) return "added";
      if (p.g !== g.g || p.ax !== g.ax || p.dx !== g.dx || p.dy !== g.dy)
        return "modified";
      return null;
    });
  }
  function stageHeader(m: string): string | null {
    const t = stageTag(m);
    return t ? `${t} Stage` : null;
  }
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && onClose()} />

{#if show}
  <div
    class="otd"
    class:dragging
    class:resizing
    style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
  >
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="otd-header" onmousedown={onDragStart}>
      <span class="otd-title">OpenType Test</span>
      <select
        class="otd-font"
        bind:value={fontPath}
        onchange={onFontSelect}
        disabled={!!fontB64}
      >
        {#each fonts as f}
          <option value={f.path}>{f.name}</option>
        {/each}
      </select>
      <label class="otd-upload">
        <Icon name="copy" size={13} />
        <span>{fontName || "Upload font"}</span>
        <input type="file" accept=".ttf,.otf,.ttc" onchange={onUpload} />
      </label>
      <button class="otd-close" onclick={onClose} title="Close"
        ><Icon name="close" size={14} /></button
      >
    </div>

    <div class="otd-body">
      <div class="otd-options">
        <textarea
          class="otd-text"
          bind:value={text}
          oninput={onOptionChange}
          placeholder="Enter text to shape…"
          spellcheck="false"
          style:font-family={fontName ? `"${fontName}"` : undefined}
        ></textarea>

        <label class="otd-opt"
          >Shaping Engine
          <select
            bind:value={engine}
            onchange={() => {
              featureString = "";
              variations = {};
              shape();
            }}
          >
            <option value="harfbuzz">HarfBuzz (OT · full trace)</option>
            <option value="babelscript"
              >BabelScript (OT reimplementation)</option
            >
            <option value="harfbuzz_fallback">HarfBuzz fallback (cmap)</option>
            <option value="graphite">Graphite (SIL)</option>
            <option value="uniscribe">Uniscribe</option>
            <option value="directwrite">DirectWrite</option>
            <option value="icu">ICU (Arabic reshape)</option>
            <option value="freetype">FreeType (cmap · no shaping)</option>
          </select></label
        >

        <label class="otd-opt"
          >Direction
          <select bind:value={direction} onchange={onOptionChange}>
            {#each DIRECTIONS as [v, l]}<option value={v}>{l}</option>{/each}
          </select></label
        >

        <label class="otd-opt"
          >Script
          <input
            list="otd-scripts"
            bind:value={script}
            oninput={onOptionChange}
            placeholder="auto / e.g. latn, arab"
          /></label
        >
        <datalist id="otd-scripts">
          <option value="auto">Auto</option>
          {#each meta.scripts as s}
            <option value={s.tag}
              >{s.label}{isSupportedScript(s.tag) ? " ✅" : ""}</option
            >
          {/each}
        </datalist>

        <label class="otd-opt"
          >Language
          <input
            list="otd-langs"
            bind:value={language}
            oninput={onOptionChange}
            placeholder="e.g. ENG, ARA"
          /></label
        >
        <datalist id="otd-langs">
          {#each meta.languages as l}
            <option value={l.tag}
              >{l.label}{isSupportedLang(l.tag) ? " ✅" : ""}</option
            >
          {/each}
        </datalist>

        <label class="otd-opt"
          >Clustering
          <select bind:value={cluster} onchange={onOptionChange}>
            {#each CLUSTERS as [v, l]}<option value={v}>{l}</option>{/each}
          </select></label
        >

        <label class="otd-opt"
          >Size <input
            type="range"
            min="24"
            max="240"
            bind:value={size}
            onchange={onOptionChange}
          /><span class="otd-sizev">{size}</span></label
        >

        <div class="otd-axes">
          <div class="otd-sub">Variation Axes</div>
          {#if fontInfo?.axes?.length}
            {#each fontInfo.axes as ax}
              <label class="otd-opt"
                >{ax.tag}
                <input
                  type="range"
                  min={ax.min}
                  max={ax.max}
                  step={Math.max(1, (ax.max - ax.min) / 20)}
                  value={variations[ax.tag] ?? ax.default}
                  oninput={(e) => {
                    variations = {
                      ...variations,
                      [ax.tag]: Number(
                        (e.currentTarget as HTMLInputElement).value,
                      ),
                    };
                    shape();
                  }}
                /><span class="otd-sizev"
                  >{variations[ax.tag] ?? ax.default}</span
                ></label
              >
            {/each}
          {:else}
            <div class="otd-empty2">No variation axes in this font.</div>
          {/if}
        </div>

        <div class="otd-features">
          <div class="otd-sub">Features</div>
          <input
            class="otd-fstr"
            bind:value={featureString}
            oninput={onOptionChange}
            placeholder="Feature string, e.g. +liga,-kern (overrides chips)"
          />
          {#if !featureString.trim()}
            <div class="otd-flist">
              {#if featureTags.gsub.length || featureTags.gpos.length}
                {#each [...featureTags.gsub, ...featureTags.gpos] as tag}
                  <button
                    class="otd-feat"
                    class:on={features[tag] === "on"}
                    class:off={features[tag] === "off"}
                    title={features[tag] === "on"
                      ? "Forced on — click to force off"
                      : features[tag] === "off"
                        ? "Forced off — click to restore default"
                        : "Default — click to force on"}
                    onclick={() => toggleFeature(tag)}>{tag}</button
                  >
                {/each}
              {:else}
                <div class="otd-empty2">No OpenType features in this font.</div>
              {/if}
            </div>
          {/if}
        </div>

        <label class="otd-check"
          ><input
            type="checkbox"
            bind:checked={showAllLookups}
            onchange={onOptionChange}
          />Show All Lookups</label
        >
        <label class="otd-check"
          ><input
            type="checkbox"
            bind:checked={glyphMode}
            onchange={onOptionChange}
          />Glyph Mode (ids)</label
        >

        <div class="otd-bflg">
          <div class="otd-sub">Buffer Flags</div>
          {#each BUFFER_FLAGS as [v, l]}
            <label class="otd-check"
              ><input
                type="checkbox"
                checked={bufferFlags.includes(v)}
                onchange={(e) => {
                  const on = (e.target as HTMLInputElement).checked;
                  bufferFlags = on
                    ? [...bufferFlags, v]
                    : bufferFlags.filter((f) => f !== v);
                  shape();
                }}
              /><span class="otd-flag" title={l}>{v}</span></label
            >
          {/each}
        </div>

        <div class="otd-hb">
          {#if hbVersion}HarfBuzz {hbVersion}{/if}
          {#if fontInfo?.debg}
            · Debg ✓{/if}
        </div>
      </div>

      <div class="otd-main">
        <div class="otd-svgwrap">
          {#if loading}
            <div class="otd-empty">Shaping…</div>
          {:else if err}
            <div class="otd-empty otd-err">{err}</div>
          {:else if shownSvg}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              class="otd-svg"
              onmouseleave={() => {
                hoverCl = -1;
                renderGlyphs(shownGlyphs, -1);
              }}
            >
              {@html shownSvg}
            </div>
          {:else}
            <div class="otd-empty">Select a font and enter text.</div>
          {/if}
        </div>

        <div class="otd-trace">
          <div class="otd-trace-head">Shaping Trace</div>
          <div class="otd-trace-body">
            {#if result?.stages?.length}
              <table class="otd-ttable">
                <thead>
                  <tr><th>Stage</th><th>Glyphs</th></tr>
                </thead>
                <tbody>
                  {#each result.stages as stage, ix (ix)}
                    {@const prev = ix > 0 ? result.stages[ix - 1].glyphs : null}
                    {@const hdr = stageHeader(stage.m)}
                    {#if hdr}
                      <tr class="otd-stage">
                        <td colspan="2">{hdr}</td>
                      </tr>
                    {:else if !(stage.m === "Start of shaping" && cluster !== "characters")}
                      {@const feat = featureOf(stage.m)}
                      {@const dbg = debugFor(
                        stage.m,
                        stageTag(stage.m) || "GSUB",
                      )}
                      <tr
                        class:lookup={!!feat}
                        style:padding-left={stage.depth * 14 + "px"}
                        onmouseenter={() => onStageEnter(stage)}
                        onmouseleave={onStageLeave}
                      >
                        <td class="otd-msg">
                          {#if feat}
                            <span class="otd-featname">{feat}</span>
                            <span class="otd-msgtxt"> · {stage.m}</span>
                          {:else}
                            <span class="otd-msgtxt">{stage.m}</span>
                          {/if}
                          {#if dbg}
                            <div class="otd-dbg">
                              {dbg.source} : <b>{dbg.name}</b>
                            </div>
                          {/if}
                        </td>
                        <td>
                          {#if stage.glyphs?.length}
                            {@const cols = diffColors(prev, stage.glyphs)}
                            {#each stage.glyphs as g, gi (gi)}
                              <!-- svelte-ignore a11y_no_static_element_interactions -->
                              <span
                                class="otd-glyph"
                                class:added={cols[gi] === "added"}
                                class:modified={cols[gi] === "modified"}
                                class:hl={hoverCl === g.cl}
                                style:color={paletteFor(g.cl)}
                                style:border-color={paletteFor(g.cl)}
                                title={`gid ${g.g} · cluster ${g.cl} · adv ${g.ax ?? 0} ${g.ay ?? 0} · off ${g.dx ?? 0} ${g.dy ?? 0}`}
                                onmouseenter={() => onGlyphEnter(g)}
                                onmouseleave={onGlyphLeave}
                              >
                                <span class="otd-gname">{glyphName(g)}</span>
                                <span class="otd-gid">({g.g})</span>
                                {#if g.ax || g.ay}
                                  <span class="otd-gadv"
                                    >{#if g.ax}→{g.ax}{/if}{#if g.ay}↑{g.ay}{/if}</span
                                  >
                                {/if}
                                {#if g.dx || g.dy}
                                  <span class="otd-goff"
                                    >{#if g.dx}↦{g.dx}{/if}{#if g.dy}↥{g.dy}{/if}</span
                                  >
                                {/if}
                              </span>
                            {/each}
                          {/if}
                        </td>
                      </tr>
                    {/if}
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="otd-empty">No shaping trace yet.</div>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="otd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .otd {
    position: fixed;
    z-index: 320;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 840px;
    min-height: 440px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 24px);
    user-select: none;
  }
  .otd.dragging,
  .otd.resizing {
    opacity: 0.92;
  }
  .otd-header {
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
  .otd-header:active {
    cursor: grabbing;
  }
  .otd-title {
    font-size: 13px;
    font-weight: 600;
  }
  .otd-font {
    font-size: 12px;
    max-width: 320px;
    padding: 2px 6px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
  }
  .otd-font option {
    color: #000;
    background: #fff;
  }
  .otd-upload {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    cursor: pointer;
  }
  .otd-upload input {
    display: none;
  }
  .otd-close {
    margin-left: auto;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 4px;
    border-radius: 4px;
  }
  .otd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .otd-body {
    flex: 1;
    display: flex;
    min-height: 0;
  }
  .otd-options {
    width: 260px;
    flex-shrink: 0;
    border-right: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    overflow: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .otd-text {
    width: 100%;
    min-height: 60px;
    font-size: 18px;
    padding: 6px;
    border-radius: 5px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg, #eee);
    resize: vertical;
  }
  .otd-opt {
    display: flex;
    flex-direction: column;
    font-size: 11px;
    color: var(--fg2, #999);
    gap: 3px;
  }
  .otd-opt select,
  .otd-opt input {
    font-size: 12px;
    padding: 3px 6px;
    border-radius: 5px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg, #eee);
  }
  .otd-opt input[type="range"] {
    padding: 0;
  }
  .otd-sizev {
    font-size: 11px;
  }
  .otd-check {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--fg, #eee);
    cursor: pointer;
  }
  .otd-bflg,
  .otd-features,
  .otd-axes {
    border-top: 1px solid var(--br, rgba(128, 128, 128, 0.25));
    padding-top: 6px;
  }
  .otd-sub {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--fg3, #6e7191);
    margin-bottom: 4px;
  }
  .otd-fstr {
    width: 100%;
    font-size: 12px;
    padding: 3px 6px;
    border-radius: 5px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg, #eee);
    box-sizing: border-box;
  }
  .otd-flag {
    font-family: Consolas, Menlo, monospace;
    font-size: 11px;
  }
  .otd-flist {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
  }
  .otd-feat {
    font-family: Consolas, Menlo, monospace;
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 4px;
    border: 1px solid var(--br, rgba(128, 128, 128, 0.4));
    background: var(--bg3, #26272b);
    color: var(--fg2, #b0b3cc);
    cursor: pointer;
  }
  .otd-feat.on {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  .otd-feat.off {
    opacity: 0.45;
    text-decoration: line-through;
  }
  .otd-hb {
    font-size: 11px;
    color: var(--fg3, #6e7191);
    border-top: 1px solid var(--br, rgba(128, 128, 128, 0.25));
    padding-top: 6px;
  }
  .otd-empty,
  .otd-empty2 {
    padding: 12px;
    font-size: 12px;
    color: var(--fg2, #999);
  }
  .otd-empty2 {
    padding: 2px 0;
  }
  .otd-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .otd-svgwrap {
    flex-shrink: 0;
    min-height: 90px;
    max-height: 36%;
    overflow: auto;
    padding: 10px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    background: #ffffff;
    display: flex;
    align-items: center;
  }
  .otd-svg {
    user-select: none;
  }
  .otd-svg :global(svg) {
    display: block;
  }
  .otd-err {
    color: #e57373;
  }
  .otd-trace {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .otd-trace-head {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--fg3, #6e7191);
    padding: 6px 12px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    flex-shrink: 0;
  }
  .otd-trace-body {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }
  .otd-ttable {
    border-collapse: collapse;
    font-size: 12px;
    width: 100%;
  }
  .otd-ttable th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--bg3, #26272b);
    color: var(--fg2, #999);
    font-weight: 600;
    text-align: left;
    padding: 4px 10px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
  }
  .otd-ttable td {
    padding: 3px 10px;
    border-bottom: 1px solid rgba(128, 128, 128, 0.08);
    vertical-align: top;
  }
  .otd-ttable tr.otd-stage td {
    background: var(--ac);
    color: #fff;
    font-weight: 700;
    text-align: center;
    padding: 4px;
  }
  .otd-ttable tr.lookup td {
    background: var(--bg3, #26272b);
  }
  .otd-ttable tr:hover td {
    background: rgba(128, 128, 128, 0.08);
  }
  .otd-msg {
    white-space: nowrap;
  }
  .otd-featname {
    font-weight: 700;
    font-family: Consolas, Menlo, monospace;
  }
  .otd-msgtxt {
    opacity: 0.8;
  }
  .otd-dbg {
    font-size: 11px;
    color: var(--fg2, #999);
  }
  .otd-glyph {
    display: inline-block;
    font-size: 11px;
    padding: 1px 5px;
    margin: 1px;
    border: 1px solid transparent;
    border-radius: 4px;
    background: var(--bg3, #26272b);
    cursor: default;
    white-space: nowrap;
  }
  .otd-gname {
    font-family: Consolas, Menlo, monospace;
  }
  .otd-gid,
  .otd-gadv,
  .otd-goff {
    font-family: Consolas, Menlo, monospace;
    font-size: 10px;
    opacity: 0.7;
  }
  .otd-gadv,
  .otd-goff {
    color: var(--fg3, #6e7191);
  }
  .otd-glyph.added {
    font-weight: 700;
    box-shadow: inset 0 0 0 2px currentColor;
  }
  .otd-glyph.modified {
    background: repeating-linear-gradient(
      -45deg,
      transparent 0 4px,
      rgba(128, 128, 128, 0.15) 4px 6px
    );
  }
  .otd-glyph.hl {
    outline: 2px solid #e23d3d;
    outline-offset: 1px;
  }
  .otd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
</style>
