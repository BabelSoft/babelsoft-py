<script lang="ts">
  import Icon from "../icons/Icon.svelte";
  import { API_BASE } from "../api";
  import {
    fontStack,
    loadUserFonts,
    uploadFont,
    removeUserFont,
  } from "../fontStack.svelte";

  // Font Overview — every installed font, grouped by font family and then by
  // primary writing system (script), with a live preview and full metadata.
  // Backend: babelmap/backend/font_overview.py → GET /api/fonts/overview.

  interface Props {
    show: boolean;
    onClose: () => void;
  }
  let { show, onClose }: Props = $props();
  const API = "http://127.0.0.1:18080/api";

  interface Axe {
    tag: string;
    min: number;
    default: number;
    max: number;
    step: number;
  }
  // A writing-system tag.  ``chapter`` is the Unicode Core Specification
  // chapter number that documents the script (see /api/fonts/overview →
  // "chapters"), used to color the chip — one color per chapter.
  interface Tag {
    tag: string;
    label: string;
    chapter?: number | null;
  }
  interface Face {
    path: string;
    file: string;
    ext: string;
    face_index: number;
    source: string;
    family: string;
    hyper_family: string;
    subfamily: string;
    full_name: string;
    ps_name: string;
    version: string;
    copyright: string;
    manufacturer: string;
    designer: string;
    designer_url: string;
    license: string;
    license_url: string;
    trademark: string;
    weight: number;
    width: number;
    italic: boolean;
    symbol: boolean;
    fs_type: number;
    panose: number[];
    upem: number;
    glyphs: number;
    glyph_count: number;
    // hyper-family aggregate counts (stamped identically on every member face)
    hyper_scripts: number;
    hyper_chars: number;
    hyper_glyphs: number;
    created: string | null;
    modified: string | null;
    variable: boolean;
    axes: Axe[];
    tables: string[];
    file_size: number;
    main_script: string;
    main_label: string;
    tags: Tag[];
    coverage: number;
    coverage_pct: number;
    scripts: {
      tag: string;
      label: string;
      chapter?: number | null;
      covered: number;
      total: number;
      ratio: number;
      blocks: {
        name: string;
        start: number;
        end: number;
        covered: number;
        total: number;
      }[];
    }[];
    ot_langs: string[];
    // OpenType Layout feature tags declared in GSUB/GPOS (e.g. liga, kern, ss01…)
    ot_features: string[];
    // localized name-table strings, one entry per language (first = primary)
    meta_langs: {
      label: string;
      family: string;
      subfamily: string;
      full_name: string;
      ps_name: string;
      version: string;
      copyright: string;
      manufacturer: string;
      designer: string;
      designer_url: string;
      license: string;
      license_url: string;
      trademark: string;
      description: string;
    }[];
  }
  interface FamilyGroup {
    family: string;
    hyper_family: string;
    faces: Face[];
  }
  interface HyperGroup {
    key: string;
    label: string;
    tags: Tag[];
    scripts: number;
    chars: number;
    glyphs: number;
    families: FamilyGroup[];
    faceCount: number;
  }

  // ── data / state ──
  let fonts = $state<Face[]>([]);
  // Unicode Core Specification chapters (one color per chapter) — from the
  // API so the whole ISO 15924 tag space has a color.
  let chapters = $state<{ num: number; label: string; color: string }[]>([]);
  let loading = $state(false);
  let err = $state("");
  let loaded = $state(false);

  let search = $state("");
  let scriptFilter = $state(""); // '' = all
  let groupSort = $state("name"); // name (A–Z) | size (by face count)
  let collapsed = $state<Set<string>>(new Set());
  let selected = $state<Face | null>(null);
  // expanded per-script block ranges in the coverage panel
  let covOpen = $state<Set<string>>(new Set());

  // ── left column split ──
  // The scanned fonts and "My fonts" stack in one column; the divider between
  // them is draggable so either half can be given more room.  ``myHeight`` is
  // the height of the lower (My fonts) pane in px.
  let myHeight = $state(180);
  let MIN_MINE = 90;
  let MIN_SCAN = 120;
  let splitting = $state(false);
  let splitEl = $state<HTMLDivElement>();

  function splitStart(e: MouseEvent) {
    e.preventDefault();
    splitting = true;
    document.addEventListener("mousemove", splitMove);
    document.addEventListener("mouseup", splitEnd);
  }
  function splitMove(e: MouseEvent) {
    if (!splitEl) return;
    // Distance from the pointer up to the top of the pane = new pane height.
    const bottom = splitEl.getBoundingClientRect().bottom;
    const max = splitEl.clientHeight - MIN_SCAN;
    myHeight = Math.min(
      Math.max(bottom - e.clientY, MIN_MINE),
      Math.max(MIN_MINE, max),
    );
  }
  function splitEnd() {
    splitting = false;
    document.removeEventListener("mousemove", splitMove);
    document.removeEventListener("mouseup", splitEnd);
  }

  // preview
  let previewText = $state("");
  let previewSize = $state(56);
  let showFaces = $state(true);

  // OpenType Layout features — each declared feature gets its own on/off/
  // default switch.  Click a feature chip to cycle: On → Off → Default.  The
  // preview applies the features that are On via font-feature-settings
  // ("tag" 1), disables the ones that are Off ("tag" 0), and leaves Default
  // ones to the browser / font.
  type FeatState = "on" | "off" | "default";
  let featState = $state<Record<string, FeatState>>({});
  function featLabel(s: FeatState): string {
    return s === "on" ? "On" : s === "off" ? "Off" : "Default";
  }
  function cycleFeat(tag: string) {
    const cur = featState[tag] || "default";
    featState[tag] = cur === "on" ? "off" : cur === "off" ? "default" : "on";
  }
  const featSettings = $derived.by(() => {
    const f = selected;
    if (!f?.ot_features?.length) return "";
    const parts: string[] = [];
    for (const tag of f.ot_features) {
      const s = featState[tag] || "default";
      if (s === "on") parts.push(`"${tag}" 1`);
      else if (s === "off") parts.push(`"${tag}" 0`);
    }
    return parts.join(", ");
  });

  // Variable-font axes — one draggable slider per fvar axis, applied to the
  // preview via font-variation-settings.  Reset to the font's defaults each
  // time a face is selected.
  let axisVals = $state<Record<string, number>>({});
  const AXIS_NAMES: Record<string, string> = {
    wght: "Weight",
    wdth: "Width",
    ital: "Italic",
    slnt: "Slant",
    opsz: "Optical size",
    GRAD: "Grade",
    XTRA: "Xtra",
    YOPQ: "Y-opq",
    YTAS: "YTAS",
    YTDE: "YTDE",
    YTFI: "YTFI",
    YTLC: "YTLC",
    YTUC: "YTUC",
  };
  function axisName(tag: string): string {
    return AXIS_NAMES[tag] || tag;
  }
  function resetAxes(f: Face) {
    axisVals = {};
    for (const a of f.axes || []) axisVals[a.tag] = a.default;
  }
  // Preview font style derived from the variable axes.  The variable font is
  // loaded as a web font (see ``varFontFamily`` / ``fog-var-font``), so the
  // registered axes mapped to font-weight / font-stretch / font-style now
  // interpolate smoothly; opsz and custom axes go through
  // font-variation-settings.
  const previewFontStyle = $derived.by(() => {
    const f = selected;
    if (!f)
      return { weight: 400, stretch: "100%", style: "normal", variation: "" };
    let weight = f.weight;
    let stretch = "100%";
    let style = f.italic ? "italic" : "normal";
    const varParts: string[] = [];
    for (const a of f.axes || []) {
      const v = axisVals[a.tag] ?? a.default;
      switch (a.tag) {
        case "wght":
          weight = v;
          break;
        case "wdth":
          stretch = `${v}%`;
          break;
        case "ital":
          style = v >= 0.5 ? "italic" : "normal";
          break;
        case "slnt":
          style = v === 0 ? "normal" : `oblique ${v}deg`;
          break;
        default:
          varParts.push(`"${a.tag}" ${v}`);
      }
    }
    return { weight, stretch, style, variation: varParts.join(", ") };
  });

  // Web-font @font-face for the selected variable font.  This browser renders
  // OS-installed variable fonts at discrete named instances (no interpolation)
  // and ignores font-variation-settings for them — but a variable font loaded
  // as a web font through the backend interpolates smoothly.  So the preview
  // pulls the real font file via /api/fonts/raw and declares it here.
  const varFontFamily = $derived.by(() => {
    const f = selected;
    if (!f?.variable || !f.axes?.length) return "";
    const base =
      f.path.replace(/[^A-Za-z0-9]/g, "") + "-" + (f.face_index ?? 0);
    return "fogvar-" + base.slice(0, 60);
  });
  $effect(() => {
    const f = selected;
    const fam = varFontFamily;
    const el = document.getElementById(
      "fog-var-font",
    ) as HTMLStyleElement | null;
    if (!f?.variable || !fam) {
      if (el) el.textContent = "";
      return;
    }
    const wght = f.axes.find((a) => a.tag === "wght");
    const wdth = f.axes.find((a) => a.tag === "wdth");
    const ital = f.axes.find((a) => a.tag === "ital");
    const slnt = f.axes.find((a) => a.tag === "slnt");
    const src = `${API}/fonts/raw?path=${encodeURIComponent(f.path)}`;
    const fmt = f.ext === "otf" ? "opentype" : "truetype";
    const decl = [
      `font-family: "${fam}"`,
      `src: url("${src}") format("${fmt}")`,
      wght ? `font-weight: ${wght.min} ${wght.max}` : "",
      wdth ? `font-stretch: ${wdth.min}% ${wdth.max}%` : "",
      ital || slnt ? "font-style: normal italic" : "",
    ]
      .filter(Boolean)
      .join("; ");
    let node = el;
    if (!node) {
      node = document.createElement("style");
      node.id = "fog-var-font";
      document.head.appendChild(node);
    }
    node.textContent = `@font-face { ${decl}; }`;
  });

  // window chrome
  let x = $state(140);
  let y = $state(70);
  let w = $state(
    Math.min(
      1240,
      (typeof window !== "undefined" ? window.innerWidth : 1240) - 32,
    ),
  );
  let h = $state(
    Math.min(
      820,
      (typeof window !== "undefined" ? window.innerHeight : 820) - 40,
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
    w = Math.max(760, winStartW + (e.clientX - resizeStartX));
    h = Math.max(420, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  // ── helpers ──
  function key(f: Face): string {
    return f.path + "#" + f.face_index;
  }
  function isSel(f: Face): boolean {
    return !!selected && key(selected) === key(f);
  }
  const WEIGHTS: Record<number, string> = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black",
  };
  const WIDTHS: Record<number, string> = {
    1: "UltraCondensed",
    2: "ExtraCondensed",
    3: "Condensed",
    4: "SemiCondensed",
    5: "Normal",
    6: "SemiExpanded",
    7: "Expanded",
    8: "ExtraExpanded",
    9: "UltraExpanded",
  };
  function fmtSize(n: number): string {
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / 1024 / 1024).toFixed(1) + " MB";
  }
  function pct(r: number): number {
    return Math.round(r * 100);
  }
  function styleLabel(f: Face): string {
    const s = (f.subfamily || "Regular").trim();
    return f.variable ? s + " · Var" : s;
  }
  function sampleChar(main: string): string {
    const m: Record<string, string> = {
      latn: "Ag",
      grek: "Ωα",
      cyrl: "Бб",
      armn: "Աբ",
      hebr: "אב",
      arab: "عرب",
      syrc: "ܐܒ",
      thaa: "ހށ",
      deva: "अक",
      beng: "অক",
      guru: "ਅਕ",
      gujr: "અક",
      orya: "ଅକ",
      taml: "அக",
      telu: "అక",
      knda: "ಅಕ",
      mlym: "അക",
      sinh: "අක",
      thai: "กข",
      laoo: "ກຂ",
      tibt: "ཀཁ",
      mymr: "ကခ",
      geor: "აბ",
      hang: "가나",
      kore: "가나",
      ethi: "ሀሁ",
      cher: "ᎠᏆ",
      cans: "ᐊᐋ",
      ogam: "ᚁᚂ",
      runr: "ᚠᚢ",
      khmr: "កខ",
      mong: "ᠠᠪ",
      hira: "あ",
      kana: "ア",
      jpan: "亜",
      bopo: "ㄅ",
      hani: "永",
      yiii: "ꀀꀁ",
      lisu: "ꓐꓑ",
      vai: "ꔀꔁ",
      copt: "Ϣϣ",
      zsym: "☺",
      zsye: "😀",
      emoji: "😀",
      zzzz: "Aa",
    };
    return m[main] ?? "Aa";
  }
  function defaultPreview(main: string): string {
    const m: Record<string, string> = {
      latn: "The quick brown fox jumps over the lazy dog · 0123456789",
      hani: "永字八法 — 中文字型概览 汉字测试",
      jpan: "あいうえお かきくけこ — 日本語フォント",
      kore: "가나다라 마바사아 — 한글 글꼴",
      hang: "가나다라 마바사아 — 한글 글꼴",
      arab: "الخط العربي — اختبار النص",
      hebr: "א ב ג ד ה — טקסט עברי",
      thai: "ก ไก่ ข ไข่ — ภาษาไทย",
      deva: "अ आ इ ई — देवनागरी",
      cyrl: "Абвгдеж — Кириллица",
      grek: "Α Β Γ Δ — Ελληνικό κείμενο",
      zsym: "→ ⇒ ∑ ∞ ≈ ⌘ ★ ♥ ☺ ✓",
      zsye: "😀 😂 🎉 ❤️ 🚀 🌟",
      emoji: "😀 😂 🎉 ❤️ 🚀 🌟",
    };
    return m[main] ?? "The quick brown fox jumps over the lazy dog";
  }

  const DOT_COLORS: string[] = [
    "#5c7cfa",
    "#e23d3d",
    "#2f9e44",
    "#e67700",
    "#ae3ec9",
    "#0ca678",
    "#d6336c",
    "#1971c2",
    "#f08c00",
    "#7048e8",
    "#12b886",
    "#e8590c",
    "#3bc9db",
  ];
  function dotColor(tag: string): string {
    let h = 0;
    for (let i = 0; i < tag.length; i++) h = (h * 31 + tag.charCodeAt(i)) >>> 0;
    return DOT_COLORS[h % DOT_COLORS.length];
  }

  // Chapter colors: the header dot is colored by the Core Spec chapter that
  // documents the primary script (one color per chapter).
  const chapterMap = $derived(new Map(chapters.map((c) => [c.num, c])));
  function chapterInfo(
    tg: Tag,
  ): { num: number; label: string; color: string } | undefined {
    if (tg.chapter == null) return undefined;
    return chapterMap.get(tg.chapter);
  }
  function mainDotColor(g: HyperGroup): string {
    if (g.tags.length)
      return chapterInfo(g.tags[0])?.color ?? dotColor(g.tags[0].tag);
    return dotColor(g.key);
  }
  function fmtInt(n: number): string {
    return (n || 0).toLocaleString();
  }

  // ── grouping (hyper family → family) ──
  const groups = $derived(buildGroups());
  function buildGroups(): HyperGroup[] {
    const q = search.trim().toLowerCase();
    const filtered = fonts.filter((f) => {
      const tags = f.tags?.length
        ? f.tags
        : [{ tag: f.main_script, label: f.main_label }];
      if (scriptFilter && !tags.some((t) => t.tag === scriptFilter))
        return false;
      if (!q) return true;
      return (
        f.family +
        " " +
        (f.hyper_family || "") +
        " " +
        f.subfamily +
        " " +
        f.file +
        " " +
        (f.ps_name || "") +
        " " +
        f.main_label
      )
        .toLowerCase()
        .includes(q);
    });
    const byHyper = new Map<string, Map<string, Face[]>>();
    for (const f of filtered) {
      const hk = f.hyper_family || f.family;
      let fam = byHyper.get(hk);
      if (!fam) {
        fam = new Map();
        byHyper.set(hk, fam);
      }
      let arr = fam.get(f.family);
      if (!arr) {
        arr = [];
        fam.set(f.family, arr);
      }
      arr.push(f);
    }
    const out: HyperGroup[] = [];
    for (const [hk, famMap] of byHyper) {
      const families: FamilyGroup[] = [...famMap.entries()]
        .map(([family, faces]) => ({
          family,
          hyper_family: hk,
          faces,
        }))
        .sort((a, b) =>
          a.family.localeCompare(b.family, undefined, { sensitivity: "base" }),
        );
      const first = families[0]?.faces[0];
      out.push({
        key: hk,
        label: hk,
        tags: first?.tags?.length
          ? first.tags
          : first
            ? [{ tag: first.main_script, label: first.main_label }]
            : [],
        scripts: first?.hyper_scripts ?? first?.tags?.length ?? 0,
        chars: first?.hyper_chars ?? first?.coverage ?? 0,
        glyphs: first?.hyper_glyphs ?? first?.glyph_count ?? first?.glyphs ?? 0,
        families,
        faceCount: families.reduce((n, f) => n + f.faces.length, 0),
      });
    }
    out.sort((a, b) =>
      groupSort === "name"
        ? a.label.localeCompare(b.label, undefined, { sensitivity: "base" })
        : b.faceCount - a.faceCount,
    );
    return out;
  }

  // One classification unit = one hyper family.  A writing system's option
  // counts how many distinct hyper families carry a face tagged with it
  // (not the number of faces).
  const scriptOptions = $derived(() => {
    const perTag = new Map<string, { label: string; hypers: Set<string> }>();
    for (const f of fonts) {
      const hk = f.hyper_family || f.family;
      const tags = f.tags?.length
        ? f.tags
        : [{ tag: f.main_script, label: f.main_label }];
      for (const t of tags) {
        let e = perTag.get(t.tag);
        if (!e) {
          e = { label: t.label, hypers: new Set() };
          perTag.set(t.tag, e);
        }
        e.hypers.add(hk);
      }
    }
    return [...perTag.entries()]
      .map(
        ([tag, e]) =>
          [tag, { label: e.label, count: e.hypers.size }] as [
            string,
            { label: string; count: number },
          ],
      )
      .sort(
        (a, b) =>
          b[1].count - a[1].count || a[1].label.localeCompare(b[1].label),
      );
  });

  const totalFamilies = $derived(new Set(fonts.map((f) => f.family)).size);
  const totalHyper = $derived(
    new Set(fonts.map((f) => f.hyper_family || f.family)).size,
  );

  // ── selection / preview ──
  function select(f: Face) {
    selected = f;
    covOpen = new Set();
    previewText = defaultPreview(f.main_script);
    resetAxes(f);
  }
  // Keep the detail panel in sync with the filtered view: if the current
  // selection is filtered out, fall back to the first visible face.
  $effect(() => {
    const g = groups;
    if (!g.length) return;
    if (!selected) {
      const first = g[0]?.families[0]?.faces[0];
      if (first) select(first);
      return;
    }
    const inView = g.some((gr) =>
      gr.families.some((fam) =>
        fam.faces.some((f) => key(f) === key(selected!)),
      ),
    );
    if (!inView) {
      const first = g[0]?.families[0]?.faces[0];
      if (first) select(first);
    }
  });
  function toggleScript(tag: string) {
    const next = new Set(collapsed);
    if (next.has(tag)) next.delete(tag);
    else next.add(tag);
    collapsed = next;
  }
  function toggleCov(tag: string) {
    const next = new Set(covOpen);
    if (next.has(tag)) next.delete(tag);
    else next.add(tag);
    covOpen = next;
  }
  function hex4(n: number): string {
    return "U+" + n.toString(16).toUpperCase().padStart(4, "0");
  }
  function expandAll() {
    collapsed = new Set();
  }
  function collapseAll() {
    collapsed = new Set(groups.map((g) => g.key));
  }

  // ── load ──
  $effect(() => {
    if (show && !loaded) load();
  });
  // Scan progress, fed by the SSE endpoint (/api/fonts/overview/stream):
  // the backend reports SCAN events per font file before the final RESULT.
  let scanDone = $state(0);
  let scanTotal = $state(0);
  let scanFile = $state("");
  let scanStarted = $state(0);
  let scanElapsed = $state(0);
  const scanPct = $derived(
    scanTotal > 0 ? Math.min(100, (scanDone / scanTotal) * 100) : 0,
  );
  // Keep the elapsed-time readout ticking while a scan is running.
  $effect(() => {
    if (!loading) return;
    const t = setInterval(() => {
      scanElapsed = (Date.now() - scanStarted) / 1000;
    }, 200);
    return () => clearInterval(t);
  });

  async function load() {
    loading = true;
    err = "";
    scanDone = 0;
    scanTotal = 0;
    scanFile = "";
    scanStarted = Date.now();
    scanElapsed = 0;
    try {
      const r = await fetch(API + "/fonts/overview/stream");
      if (!r.ok) throw new Error(String(r.status));
      const reader = r.body?.getReader();
      if (!reader) throw new Error("Stream not supported");
      const decoder = new TextDecoder();
      let buffer = "";
      let got = false;

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") continue;
          if (payload.startsWith("SCAN ")) {
            try {
              const p = JSON.parse(payload.slice(5));
              scanDone = p.done ?? 0;
              scanTotal = p.total ?? 0;
              scanFile = p.file ?? "";
            } catch {
              /* skip malformed */
            }
            continue;
          }
          if (payload.startsWith("ERROR ")) {
            try {
              throw new Error(JSON.parse(payload.slice(6)));
            } catch (e: any) {
              throw e instanceof Error ? e : new Error(String(e));
            }
          }
          if (payload.startsWith("RESULT ")) {
            const d = JSON.parse(payload.slice(7));
            fonts = d.fonts ?? [];
            chapters = d.chapters ?? [];
            got = true;
          }
        }
      }
      if (!got) throw new Error("No data");
      loaded = true;
      collapsed = new Set();
      if (fonts.length && !selected) {
        const first = fonts.find((f) => f.main_script === "latn") || fonts[0];
        select(first);
      }
    } catch (e: any) {
      err = e.message || "Failed to load fonts";
    }
    loading = false;
  }
  function refresh() {
    loaded = false;
    fonts = [];
    selected = null;
    load();
  }

  // ── Added fonts (uploaded via the registry) ────────────────────────
  // These live OUTSIDE the system font directories, so the directory scan
  // above never sees them.  They are listed at the bottom of the left column so
  // Add / Remove and their font analysis sit next to the installed-font
  // analysis.  The Composite Font dialog's entry editor reads the same registry.
  let uploadErr = $state("");
  let uploading = $state(false);
  let addedFileInput = $state<HTMLInputElement>();
  let analysis = $state<Record<string, any>>({});

  async function onAddedFiles(files: FileList | null) {
    if (!files?.length) return;
    uploadErr = "";
    uploading = true;
    try {
      for (const f of Array.from(files)) await uploadFont(f);
      await loadUserFonts();
    } catch (e: any) {
      uploadErr = e.message || "Upload failed";
    }
    uploading = false;
    if (addedFileInput) addedFileInput.value = "";
  }

  async function dropAdded(id: string) {
    try {
      await removeUserFont(id);
    } catch (e: any) {
      uploadErr = e.message || "Remove failed";
    }
  }

  /** Lazily fetch the fontTools analysis for one added font. */
  async function loadAnalysis(id: string) {
    if (analysis[id]) return;
    try {
      const d = await fetch(
        API_BASE + "/fonts/user/analyze?id=" + encodeURIComponent(id),
      ).then((r) => r.json());
      analysis = { ...analysis, [id]: d };
    } catch {
      analysis = { ...analysis, [id]: { error: "analysis failed" } };
    }
  }

  /**
   * The uploaded fonts, shaped exactly like the scanned list above so the two
   * halves of the left column read the same way: a script-group header, then a
   * family row with its faces as chips.
   *
   * The registry stores one entry per *file* (a `.ttc` may hold several faces),
   * which is the same relation the scan uses between a family row and its
   * faces — so a file here plays the role of a family.
   */
  const mineFamilies = $derived.by(() =>
    fontStack.userFonts.map((uf) => {
      const a = analysis[uf.id];
      // Prefer the analysis (fresher, and it fills in the names for
      // registrations made before this field existed), then the registry entry.
      const styles: string[] = a?.subfamilies?.length
        ? a.subfamilies
        : uf.subfamilies?.length
          ? uf.subfamilies
          : [];
      return { uf, a, styles };
    }),
  );

  /**
   * Sample glyph for an uploaded family, mirroring the scanned rows.
   *
   * The scan derives it from the family's primary script; the registry has no
   * script data, so fall back to a letter of the family name — a character that
   * is guaranteed to exist in the font.
   */
  function mineSample(uf: any): string {
    return (uf.family || uf.name || "?").trim().charAt(0).toUpperCase() || "?";
  }

  /**
   * The header's meta line, in the same shape the scanned groups use
   * ("N scripts · M chars · K glyphs").
   *
   * Only analyzed fonts contribute script/character counts, so before any
   * analysis this degrades to the glyph total the registry already knows.
   */
  const mineMeta = $derived.by(() => {
    const fonts = fontStack.userFonts;
    if (!fonts.length) return "no fonts added";
    const glyphs = fonts.reduce((s, uf) => s + (uf.glyphs || 0), 0);
    const analyzed = mineFamilies.map((m) => m.a).filter((a) => a && !a.error);
    if (!analyzed.length) {
      return `${fonts.length} files · ${fmtInt(glyphs)} glyphs`;
    }
    const scripts = new Set<string>();
    let chars = 0;
    for (const a of analyzed) {
      chars += a.coverage || 0;
      for (const b of a.blocks || []) scripts.add(b.name);
    }
    const parts = [`${scripts.size} blocks`, `${fmtInt(chars)} chars`];
    if (analyzed.length < fonts.length) {
      parts.push(`${analyzed.length}/${fonts.length} analyzed`);
    }
    return parts.join(" · ");
  });

  // Split a metadata value into plain-text and URL segments so any web
  // address (Designer/License URL rows, or URLs embedded in Copyright,
  // License, Trademark text, …) renders as a clickable link.
  function linkify(text: string): { text: string; url?: string }[] {
    if (!text) return [{ text }];
    const parts: { text: string; url?: string }[] = [];
    const re = /\b(?:https?:\/\/|www\.)[^\s<>"']+/gi;
    let last = 0;
    for (const m of text.matchAll(re)) {
      const idx = m.index ?? 0;
      if (idx > last) parts.push({ text: text.slice(last, idx) });
      // trim trailing punctuation that isn't part of the URL
      let raw = m[0].replace(/[.,;:!?)]+$/, "");
      if (raw.length) {
        const url = /^https?:\/\//i.test(raw) ? raw : "https://" + raw;
        parts.push({ text: raw, url });
      }
      last = idx + raw.length;
    }
    if (last < text.length) parts.push({ text: text.slice(last) });
    return parts.length ? parts : [{ text }];
  }

  // ── metadata rows for the detail panel ──
  const metaRows = $derived.by(() => {
    const f = selected;
    if (!f) return [] as [string, string][];
    const rows: [string, string][] = [
      ["Hyper family", f.hyper_family || f.family],
      ["Family", f.family],
      ["Style", f.subfamily || "Regular"],
      ["Full name", f.full_name],
      ["PostScript", f.ps_name],
      ["File", f.file + (f.face_index ? ` [face ${f.face_index}]` : "")],
      ["Location", f.path],
      ["Source", f.source],
      ["Weight", `${f.weight} (${WEIGHTS[f.weight] || "?"})`],
      ["Width", WIDTHS[f.width] || String(f.width)],
      ["Italic", f.italic ? "Yes" : "No"],
      ["Symbol font", f.symbol ? "Yes" : "No"],
      ["Glyphs", f.glyphs.toLocaleString()],
      ["Units / em", String(f.upem)],
      ["Created", f.created || "—"],
      ["Modified", f.modified || "—"],
      ["File size", fmtSize(f.file_size)],
      ["Version", f.version || "—"],
    ];
    if (f.variable) {
      rows.push([
        "Variable axes",
        f.axes.map((a) => `${a.tag} ${a.min}–${a.max}`).join(", ") || "—",
      ]);
    }
    if (f.manufacturer) rows.push(["Manufacturer", f.manufacturer]);
    if (f.designer) rows.push(["Designer", f.designer]);
    if (f.designer_url) rows.push(["Designer URL", f.designer_url]);
    if (f.license_url) rows.push(["License URL", f.license_url]);
    if (f.trademark) rows.push(["Trademark", f.trademark]);
    if (f.copyright) rows.push(["Copyright", f.copyright]);
    if (f.license) rows.push(["License", f.license]);
    if (f.ot_langs?.length) rows.push(["OT languages", f.ot_langs.join(", ")]);
    return rows;
  });

  // Localized name-table blocks after the primary "Default" language — only
  // the fields that differ per language are repeated in each block.
  const langBlocks = $derived.by(() => {
    const f = selected;
    if (!f?.meta_langs?.length)
      return [] as { label: string; rows: [string, string][] }[];
    const blocks: { label: string; rows: [string, string][] }[] = [];
    for (const lg of f.meta_langs.slice(1)) {
      const rows: [string, string][] = [];
      if (lg.family) rows.push(["Family", lg.family]);
      if (lg.subfamily) rows.push(["Style", lg.subfamily]);
      if (lg.full_name) rows.push(["Full name", lg.full_name]);
      if (lg.ps_name) rows.push(["PostScript", lg.ps_name]);
      if (lg.version) rows.push(["Version", lg.version]);
      if (lg.copyright) rows.push(["Copyright", lg.copyright]);
      if (lg.manufacturer) rows.push(["Manufacturer", lg.manufacturer]);
      if (lg.designer) rows.push(["Designer", lg.designer]);
      if (lg.designer_url) rows.push(["Designer URL", lg.designer_url]);
      if (lg.license) rows.push(["License", lg.license]);
      if (lg.license_url) rows.push(["License URL", lg.license_url]);
      if (lg.trademark) rows.push(["Trademark", lg.trademark]);
      if (lg.description) rows.push(["Description", lg.description]);
      if (rows.length) blocks.push({ label: lg.label, rows });
    }
    return blocks;
  });
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && onClose()} />

{#if show}
  <div
    class="fog"
    class:dragging
    class:resizing
    style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
  >
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fog-header" onmousedown={onDragStart}>
      <Icon name="dice" size={15} />
      <span class="fog-title">Font Overview</span>
      <span class="fog-sub"
        >{totalHyper} hyper families · {totalFamilies} families · {fonts.length}
        faces</span
      >
      <span class="fog-sp"></span>
      <button class="fog-ic" onclick={refresh} title="Re-scan font directories"
        ><Icon name="rewind" size={13} /></button
      >
      <button class="fog-close" onclick={onClose} title="Close"
        ><Icon name="close" size={14} /></button
      >
    </div>

    <div class="fog-toolbar">
      <div class="fog-search">
        <Icon name="wavy" size={13} />
        <input
          bind:value={search}
          placeholder="Search family, file, script…"
          spellcheck="false"
        />
      </div>
      <select class="fog-sel" bind:value={scriptFilter}>
        <option value="">All writing systems</option>
        {#each scriptOptions() as [tag, info]}
          <option value={tag}>{info.label} ({info.count})</option>
        {/each}
      </select>
      <select class="fog-sel" bind:value={groupSort}>
        <option value="size">Group: size</option>
        <option value="name">Group: A–Z</option>
      </select>
      <div class="fog-tools">
        <button class="fog-chip" onclick={expandAll}>Expand all</button>
        <button class="fog-chip" onclick={collapseAll}>Collapse all</button>
      </div>
      <div class="fog-tools">
        <label class="fog-check"
          ><input type="checkbox" bind:checked={showFaces} />faces</label
        >
      </div>
    </div>

    {#if loading}
      <div class="fog-center">
        <div class="fog-scan">
          <div class="fog-scan-title">Scanning font directories…</div>
          <div class="fog-bar" class:indet={scanTotal === 0}>
            <div class="fog-bar-fill" style="width:{scanPct}%"></div>
          </div>
          <div class="fog-scan-meta">
            {#if scanTotal > 0}
              <span class="fog-scan-count">{scanDone} / {scanTotal}</span>
              <span class="fog-scan-pct">{scanPct.toFixed(0)}%</span>
            {:else}
              <span class="fog-scan-count">enumerating…</span>
            {/if}
            <span class="fog-scan-time">{scanElapsed.toFixed(1)}s</span>
          </div>
          <div class="fog-scan-file" title={scanFile}>
            {scanFile || "\u00a0"}
          </div>
        </div>
      </div>
    {:else if err}
      <div class="fog-center"><div class="fog-empty fog-err">{err}</div></div>
    {:else if fonts.length === 0}
      <div class="fog-center"><div class="fog-empty">No fonts found.</div></div>
    {:else}
      <div class="fog-body">
        <!-- ── left: grouped list ── -->
        <div class="fog-list">
          <!-- ── the two panes are stacked and independently sized; the divider
             between them is draggable so either half can grow. ── -->
          <div class="fog-split" class:dragging={splitting} bind:this={splitEl}>
            <div class="fog-groups">
              {#each groups as g (g.key)}
                <section class="fog-script">
                  <button
                    class="fog-shead"
                    class:on={!collapsed.has(g.key)}
                    onclick={() => toggleScript(g.key)}
                  >
                    {#if collapsed.has(g.key)}
                      <Icon name="chevron-right" size={13} />
                    {:else}
                      <Icon name="chevron-down" size={13} />
                    {/if}
                    <span class="fog-dot" style:background={mainDotColor(g)}
                    ></span>
                    <span class="fog-slabel" title={g.key}>{g.label}</span>
                    <span
                      class="fog-smeta"
                      title="{g.scripts} scripts · {fmtInt(
                        g.chars,
                      )} characters · {fmtInt(g.glyphs)} glyphs"
                    >
                      {g.scripts} scripts · {fmtInt(g.chars)} chars · {fmtInt(
                        g.glyphs,
                      )} glyphs
                    </span>
                    <span class="fog-scount">{g.faceCount}</span>
                  </button>
                  {#if !collapsed.has(g.key)}
                    <div class="fog-famwrap">
                      {#each g.families as fam (g.key + ":" + fam.family)}
                        <div class="fog-family">
                          <div class="fog-fhead">
                            <span
                              class="fog-sample"
                              style:font-family={fam.faces[0].family}
                              >{sampleChar(fam.faces[0].main_script)}</span
                            >
                            <span class="fog-fname" title={fam.family}
                              >{fam.family}</span
                            >
                            <span class="fog-fcount">{fam.faces.length}</span>
                          </div>
                          {#if showFaces}
                            <div class="fog-faces">
                              {#each fam.faces as f (key(f))}
                                <button
                                  class="fog-face"
                                  class:on={isSel(f)}
                                  title="{f.full_name}\n{f.path}"
                                  onclick={() => select(f)}
                                  >{styleLabel(f)}</button
                                >
                              {/each}
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  {/if}
                </section>
              {/each}
            </div>

            <!-- drag to resize the two panes -->
            <div
              class="fog-hsplit"
              class:on={splitting}
              onmousedown={splitStart}
              role="slider"
              aria-label="Resize My fonts"
              aria-orientation="horizontal"
              aria-valuenow={myHeight}
              aria-valuemin={MIN_MINE}
              tabindex="0"
              title="Drag to resize"
            >
              <span></span>
            </div>

            <!-- ── left, bottom: the user's own fonts ──
             This is a top-level group of its own ("My fonts"), one level ABOVE
             the fonts it contains: the header is the group, and each uploaded
             file is a family row beneath it — the same shape the scanned groups
             use.  Uploaded fonts live outside the system font folders, so the
             directory scan never sees them. -->
            <section
              class="fog-script fog-mine-group"
              style="height:{myHeight}px"
            >
              <div class="fog-shead fog-mine-head">
                <span class="fog-dot" style:background={dotColor("mine")}
                ></span>
                <span class="fog-slabel">My fonts</span>
                <span class="fog-smeta" title={mineMeta}>{mineMeta}</span>
                <span class="fog-scount">{fontStack.userFonts.length}</span>
                <button
                  class="fog-chip fog-mine-add"
                  onclick={() => addedFileInput?.click()}
                  disabled={uploading}
                >
                  {uploading ? "Uploading…" : "+ Add font…"}
                </button>
                <input
                  type="file"
                  accept=".ttf,.otf,.ttc,.otc,.woff,.woff2"
                  multiple
                  bind:this={addedFileInput}
                  onchange={(e) =>
                    onAddedFiles((e.target as HTMLInputElement).files)}
                />
              </div>
              {#if uploadErr}<div class="fog-added-err">{uploadErr}</div>{/if}
              {#if fontStack.userFonts.length === 0}
                <div class="fog-famwrap">
                  <div class="fog-empty">No added fonts yet.</div>
                </div>
              {:else}
                <div class="fog-famwrap">
                  {#each mineFamilies as { uf, a, styles } (uf.id)}
                    <div class="fog-family">
                      <div class="fog-fhead">
                        <span
                          class="fog-sample"
                          style:font-family={uf.family || uf.name}
                          >{mineSample(uf)}</span
                        >
                        <span class="fog-fname" title={uf.file}
                          >{uf.family || uf.name}</span
                        >
                        <span class="fog-fcount"
                          >{styles.length || uf.faces || 1}</span
                        >
                        <button
                          class="fog-chip fog-mine-act"
                          onclick={async () => {
                            if (analysis[uf.id]) {
                              const m = { ...analysis };
                              delete m[uf.id];
                              analysis = m;
                            } else await loadAnalysis(uf.id);
                          }}>{analysis[uf.id] ? "Hide" : "Analyze"}</button
                        >
                        <button
                          class="fog-chip danger fog-mine-act"
                          onclick={() => dropAdded(uf.id)}>Remove</button
                        >
                      </div>
                      <!-- Face chips appear under the same "faces" toggle the
                         scanned families use, so a single-face font shows no
                         redundant "Regular" pill. -->
                      {#if showFaces && styles.length > 1}
                        <div class="fog-faces">
                          {#each styles as s (s)}
                            <span class="fog-face fog-face-static">{s}</span>
                          {/each}
                        </div>
                      {/if}
                      {#if a}
                        {#if a.error}
                          <div class="fog-added-err">{a.error}</div>
                        {:else}
                          <div class="fog-analysis">
                            <span><b>Family</b> {a.family || "—"}</span>
                            <span><b>File</b> {a.file || "—"}</span>
                            <span><b>UPEM</b> {a.upem || "—"}</span>
                            <span><b>Glyphs</b> {a.glyphs || 0}</span>
                            <span
                              ><b>Coverage</b> {fmtInt(a.coverage)} chars</span
                            >
                            <span
                              ><b>Variable</b>
                              {a.variable
                                ? `yes (${a.axes?.length ?? 0} axes)`
                                : "no"}</span
                            >
                            <span><b>Tables</b> {a.tables?.length ?? 0}</span>
                            {#if a.ot_features?.length}<span
                                ><b>OT features</b>
                                {a.ot_features.slice(0, 8).join(" ")}{a
                                  .ot_features.length > 8
                                  ? " …"
                                  : ""}</span
                              >{/if}
                            {#if a.blocks?.length}
                              <span class="fog-analysis-blocks"
                                ><b>Blocks</b>
                                {a.blocks
                                  .slice(0, 6)
                                  .map((b: any) => `${b.name} (${b.covered})`)
                                  .join(" · ")}{a.blocks.length > 6
                                  ? " …"
                                  : ""}</span
                              >
                            {/if}
                          </div>
                        {/if}
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </section>
          </div>
        </div>

        <!-- ── right: detail ── -->
        <div class="fog-detail">
          {#if selected}
            <div class="fog-dhead">
              <div class="fog-dtitle">{selected.family}</div>
              <div class="fog-dsub">
                {selected.subfamily || "Regular"}
                {#if selected.source}
                  <span
                    class="fog-badge"
                    class:user={selected.source === "User"}
                    >{selected.source}</span
                  >
                {/if}
                {#if selected.variable}<span class="fog-badge fog-var"
                    >Variable</span
                  >{/if}
                {#if selected.symbol}<span class="fog-badge">Symbol</span>{/if}
              </div>
            </div>

            <!-- preview -->
            <div class="fog-previewwrap">
              <div
                class="fog-preview"
                style:font-family={selected.variable && varFontFamily
                  ? `"${varFontFamily}"`
                  : `'${selected.family}'`}
                style:font-size="{previewSize}px"
                style:font-weight={previewFontStyle.weight}
                style:font-stretch={previewFontStyle.stretch}
                style:font-style={previewFontStyle.style}
                style:font-feature-settings={featSettings || undefined}
                style:font-variation-settings={previewFontStyle.variation ||
                  undefined}
              >
                {previewText || sampleChar(selected.main_script)}
              </div>
              <div class="fog-pcontrols">
                <textarea
                  bind:value={previewText}
                  spellcheck="false"
                  placeholder="Type a preview…"
                ></textarea>
                <input
                  type="range"
                  min="16"
                  max="160"
                  bind:value={previewSize}
                />
                <span class="fog-sizev">{previewSize}px</span>
              </div>
              {#if selected.ot_features?.length}
                <div class="fog-feats">
                  {#each selected.ot_features as tag (tag)}
                    <button
                      class="fog-feat"
                      class:on={featState[tag] === "on"}
                      class:off={featState[tag] === "off"}
                      onclick={() => cycleFeat(tag)}
                      title="{tag} · {featLabel(
                        featState[tag] || 'default',
                      )} — click to cycle On → Off → Default">{tag}</button
                    >
                  {/each}
                </div>
              {/if}
              {#if selected.variable && selected.axes?.length}
                <div class="fog-axes">
                  {#each selected.axes as a (a.tag)}
                    <div class="fog-axis">
                      <span class="fog-axistag" title={a.tag}
                        >{axisName(a.tag)}</span
                      >
                      <input
                        type="range"
                        min={a.min}
                        max={a.max}
                        step={a.step}
                        value={axisVals[a.tag] ?? a.default}
                        oninput={(e) =>
                          (axisVals[a.tag] = Number(
                            (e.currentTarget as HTMLInputElement).value,
                          ))}
                      />
                      <span class="fog-axisval"
                        >{axisVals[a.tag] ?? a.default}</span
                      >
                    </div>
                  {/each}
                </div>
              {/if}
            </div>

            <!-- coverage -->
            <div class="fog-cov">
              <div class="fog-sec-title">Script coverage</div>
              {#if selected.scripts?.length}
                {#each selected.scripts as s}
                  <button
                    class="fog-covrow"
                    class:open={covOpen.has(s.tag)}
                    onclick={() => toggleCov(s.tag)}
                  >
                    <Icon
                      name={covOpen.has(s.tag)
                        ? "chevron-down"
                        : "chevron-right"}
                      size={11}
                    />
                    <span class="fog-covlabel" title={s.label}>{s.label}</span>
                    <span class="fog-covbar"
                      ><span
                        class="fog-covfill"
                        style:width="{Math.max(2, pct(s.ratio))}%"
                      ></span></span
                    >
                    <span class="fog-covval"
                      >{pct(s.ratio)}% · {s.covered.toLocaleString()}</span
                    >
                  </button>
                  {#if covOpen.has(s.tag) && s.blocks?.length}
                    <div class="fog-covblocks">
                      {#each s.blocks as b (s.tag + ":" + b.start)}
                        <div
                          class="fog-covblock"
                          title="{hex4(b.start)}–{hex4(b.end)}"
                        >
                          <span class="fog-covblabel" title={b.name}
                            >{b.name}</span
                          >
                          <span class="fog-covbbar"
                            ><span
                              class="fog-covbfill"
                              style:width="{Math.max(
                                b.covered ? 1 : 0,
                                pct(b.covered / Math.max(1, b.total)),
                              )}%"
                            ></span></span
                          >
                          <span class="fog-covbval"
                            >{b.covered.toLocaleString()}/{b.total.toLocaleString()}</span
                          >
                        </div>
                      {/each}
                    </div>
                  {/if}
                {/each}
                <div class="fog-covtotal">
                  {selected.coverage.toLocaleString()} code points covered in this
                  font ·
                  {pct(selected.coverage_pct)}% of the common repertoire
                </div>
              {:else}
                <div class="fog-empty">No cmap coverage data.</div>
              {/if}
            </div>

            <!-- metadata -->
            <div class="fog-meta">
              <div class="fog-mlang">
                <div class="fog-mlangtitle">Metadata: Default</div>
                <table class="fog-mtable">
                  <tbody>
                    {#each metaRows as [k, v]}
                      <tr>
                        <td class="fog-mk">{k}</td>
                        <td class="fog-mv">
                          {#each linkify(v) as seg}
                            {#if seg.url}
                              <a
                                href={seg.url}
                                target="_blank"
                                rel="noopener noreferrer">{seg.text}</a
                              >
                            {:else}
                              {seg.text}
                            {/if}
                          {/each}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
              {#each langBlocks as lb}
                <div class="fog-mlang">
                  <div class="fog-mlangtitle">Metadata: {lb.label}</div>
                  <table class="fog-mtable">
                    <tbody>
                      {#each lb.rows as [k, v]}
                        <tr>
                          <td class="fog-mk">{k}</td>
                          <td class="fog-mv">
                            {#each linkify(v) as seg}
                              {#if seg.url}
                                <a
                                  href={seg.url}
                                  target="_blank"
                                  rel="noopener noreferrer">{seg.text}</a
                                >
                              {:else}
                                {seg.text}
                              {/if}
                            {/each}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/each}
            </div>
          {:else}
            <div class="fog-center">
              <div class="fog-empty">Select a font to inspect it.</div>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fog-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .fog {
    position: fixed;
    z-index: 310;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.35);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 760px;
    min-height: 420px;
    max-width: calc(100vw - 24px);
    max-height: calc(100vh - 16px);
    user-select: none;
  }
  .fog.dragging,
  .fog.resizing {
    opacity: 0.92;
    transition: none;
  }
  .fog-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: linear-gradient(
      135deg,
      var(--ac),
      color-mix(in srgb, var(--ac) 70%, #e23d3d)
    );
    color: #fff;
    cursor: grab;
    flex-shrink: 0;
    user-select: none;
  }
  .fog-header:active {
    cursor: grabbing;
  }
  .fog-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.2px;
  }
  .fog-sub {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.85);
    margin-left: 4px;
  }
  .fog-sp {
    flex: 1;
  }
  .fog-ic,
  .fog-close {
    background: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #fff;
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    cursor: pointer;
  }
  .fog-ic:hover,
  .fog-close:hover {
    background: rgba(255, 255, 255, 0.3);
  }
  .fog-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--bd);
    flex-shrink: 0;
    flex-wrap: wrap;
    background: var(--bg);
  }
  .fog-search {
    position: relative;
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 180px;
  }
  .fog-search :global(svg) {
    position: absolute;
    left: 8px;
    color: var(--fg3);
    pointer-events: none;
  }
  .fog-search input {
    width: 100%;
    padding-left: 26px;
  }
  .fog-sel {
    padding: 4px 8px;
  }
  .fog-tools {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .fog-chip {
    background: var(--bg3);
    color: var(--fg2);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    border: 1px solid transparent;
  }
  .fog-chip:hover {
    background: var(--ac);
    color: #fff;
  }
  .fog-check {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--fg2);
  }
  .fog-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .fog-empty {
    color: var(--fg3);
    font-size: 12px;
    padding: 18px;
    text-align: center;
  }
  /* ── added fonts (uploaded registry) ── */
  .fog-chip.danger:hover {
    background: #e23d3d;
    color: #fff;
  }
  .fog-added-err {
    font-size: 11px;
    color: #e23d3d;
    padding: 4px 0;
  }
  .fog-analysis {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 11px;
    color: var(--fg2);
    padding: 4px 8px 8px 14px;
  }
  .fog-analysis b {
    color: var(--fg3);
    font-weight: 600;
    margin-right: 3px;
  }
  .fog-analysis-blocks {
    flex-basis: 100%;
  }
  /* ── scan progress ── */
  .fog-scan {
    width: 320px;
    max-width: 70%;
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
  .fog-scan-title {
    font-size: 12px;
    color: var(--fg2);
    text-align: center;
  }
  .fog-bar {
    height: 6px;
    background: var(--bg3);
    border-radius: 3px;
    overflow: hidden;
  }
  .fog-bar-fill {
    height: 100%;
    background: var(--ac);
    border-radius: 3px;
    transition: width 0.15s ease;
  }
  /* before the file count is known the bar sweeps instead of filling */
  .fog-bar.indet .fog-bar-fill {
    width: 30% !important;
    animation: fog-indet 1.1s ease-in-out infinite;
  }
  @keyframes fog-indet {
    0% {
      margin-left: -30%;
    }
    100% {
      margin-left: 100%;
    }
  }
  .fog-scan-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: var(--fg3);
    font-variant-numeric: tabular-nums;
  }
  .fog-scan-pct {
    color: var(--fg2);
  }
  .fog-scan-time {
    margin-left: auto;
  }
  .fog-scan-file {
    font-size: 10px;
    color: var(--fg3);
    font-family: monospace;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    opacity: 0.75;
  }
  .fog-err {
    color: #e23d3d;
  }
  .fog-body {
    flex: 1;
    display: flex;
    min-height: 0;
  }

  /* ── left column ──
     Two panes stacked vertically (scanned fonts, then My fonts) with a
     draggable divider between them; ``.fog-split`` is the flex host that the
     divider measures against. */
  .fog-list {
    width: 44%;
    min-width: 300px;
    border-right: 1px solid var(--bd);
    padding: 6px;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .fog-split {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  /* The scanned groups take the remaining height and scroll internally. */
  .fog-split > .fog-groups {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  /* ── my fonts ──
     A top-level group whose children are the uploaded fonts: the header is the
     group (same look as a scanned group header), and each file sits one level
     below it as a family row.  Only the extras are styled here — the Add
     button and the per-row Analyze / Remove actions. */
  .fog-mine-group {
    flex: none;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    /* a hairline top border separates this pane from the scanned list above,
       whose scrollbar would otherwise run straight into the header */
    border-top: 1px solid var(--bd);
    padding-top: 5px;
  }
  .fog-mine-group > .fog-shead {
    flex: none;
  }
  /* the family list scrolls inside the pane, so the header stays put */
  .fog-mine-group > .fog-famwrap {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    /* one indent step deeper than the scanned groups' families, which makes
       the extra level (group → font) visible at a glance */
    padding-left: 14px;
  }
  /* the file picker is driven by the "+ Add font…" button */
  .fog-mine-group input[type="file"] {
    display: none;
  }
  /* the header is not a toggle here, so it must not look clickable */
  .fog-mine-head {
    cursor: default;
  }
  .fog-mine-head:hover {
    border-color: var(--bd);
  }
  .fog-mine-add {
    flex: none;
  }
  /* per-row actions: inline chips on the family row.  They are kept at a low
     opacity rather than hidden so the row keeps the same visual weight as the
     scanned families while the actions stay discoverable. */
  .fog-mine-act {
    flex: none;
    opacity: 0.55;
    transition: opacity 0.12s;
  }
  .fog-family:hover .fog-mine-act,
  .fog-mine-act:focus-visible {
    opacity: 1;
  }
  /* faces of an uploaded font are informational, not selectable */
  .fog-face-static {
    cursor: default;
    opacity: 0.85;
  }
  .fog-face-static:hover {
    border-color: transparent;
  }

  /* ── draggable divider between the two left panes ── */
  .fog-hsplit {
    flex: none;
    height: 7px;
    cursor: row-resize;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
  }
  .fog-hsplit span {
    display: block;
    width: 40px;
    height: 3px;
    border-radius: 2px;
    background: var(--bd);
  }
  .fog-hsplit:hover span,
  .fog-hsplit.on span {
    background: var(--ac);
  }
  /* while dragging, don't let the pointer pick text or fire hovers */
  .fog-split.dragging {
    user-select: none;
    cursor: row-resize;
  }
  .fog-script {
    margin-bottom: 4px;
  }
  .fog-shead {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 9px;
    padding: 6px 8px;
    color: var(--fg);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }
  .fog-shead:hover {
    border-color: var(--ac);
  }
  .fog-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex: none;
  }
  .fog-slabel {
    flex: 1;
    text-align: left;
  }
  .fog-scount {
    font-size: 10px;
    color: var(--fg3);
    background: var(--bg3);
    border-radius: 999px;
    padding: 1px 8px;
  }
  .fog-famwrap {
    padding: 3px 0 3px 8px;
  }
  .fog-family {
    border-radius: 8px;
    padding: 3px 6px;
  }
  .fog-family:hover {
    background: var(--bg3);
  }
  .fog-fhead {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 4px;
    overflow: hidden;
  }
  .fog-sample {
    font-size: 17px;
    line-height: 1;
    width: 26px;
    text-align: center;
    color: var(--fg2);
    flex: none;
  }
  .fog-fname {
    flex: 1;
    font-size: 12px;
    color: var(--fg);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .fog-fcount {
    font-size: 10px;
    color: var(--fg3);
    flex: none;
  }
  .fog-smeta {
    flex: none;
    font-size: 10px;
    font-weight: 500;
    color: var(--fg3);
    white-space: nowrap;
    letter-spacing: 0.2px;
  }
  .fog-faces {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 2px 4px 4px 34px;
  }
  .fog-face {
    background: var(--bg3);
    color: var(--fg2);
    border: 1px solid transparent;
    font-size: 10.5px;
    padding: 2px 8px;
    border-radius: 999px;
    cursor: pointer;
  }
  .fog-face:hover {
    border-color: var(--ac);
    color: var(--fg);
  }
  .fog-face.on {
    background: var(--ac);
    color: #fff;
  }

  /* ── right detail ── */
  .fog-detail {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 12px 14px;
    gap: 12px;
    background: var(--bg2);
  }
  .fog-dhead {
    border-bottom: 1px solid var(--bd);
    padding-bottom: 8px;
  }
  .fog-dtitle {
    font-size: 17px;
    font-weight: 700;
    color: var(--fg);
  }
  .fog-dsub {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--fg2);
    margin-top: 3px;
  }
  .fog-badge {
    background: var(--bg3);
    color: var(--fg2);
    font-size: 10px;
    padding: 1px 8px;
    border-radius: 999px;
  }
  .fog-badge.user {
    background: #e7f5ff;
    color: #1c7ed6;
  }
  .fog-badge.fog-var {
    background: #fff3bf;
    color: #e67700;
  }
  .fog-previewwrap {
    border: 1px solid var(--bd);
    border-radius: 10px;
    padding: 12px;
    background: var(--bg);
  }
  .fog-preview {
    min-height: 70px;
    line-height: 1.15;
    color: var(--fg);
    word-break: break-word;
    overflow-wrap: anywhere;
    user-select: text;
  }
  .fog-pcontrols {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
  }
  .fog-pcontrols textarea {
    flex: 1;
    resize: none;
    height: 30px;
    padding: 5px 8px;
  }
  .fog-pcontrols input[type="range"] {
    flex: none;
    width: 120px;
    padding: 0;
  }
  .fog-sizev {
    font-size: 11px;
    color: var(--fg3);
    width: 40px;
    text-align: right;
  }
  .fog-feats {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 8px;
    flex-wrap: wrap;
    min-width: 0;
  }
  .fog-feat {
    flex: none;
    background: var(--bg3);
    color: var(--fg2);
    border: 1px solid var(--bd);
    font-size: 10px;
    font-weight: 600;
    padding: 1px 8px;
    border-radius: 999px;
    cursor: pointer;
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  }
  .fog-feat:hover {
    border-color: var(--ac);
    color: var(--fg);
  }
  /* On = green, Off = red, Default = no special styling. */
  .fog-feat.on {
    background: #2f9e44;
    border-color: #2f9e44;
    color: #fff;
  }
  .fog-feat.off {
    background: #e03131;
    border-color: #e03131;
    color: #fff;
    text-decoration: line-through;
  }
  .fog-axes {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 8px;
  }
  .fog-axis {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10.5px;
  }
  .fog-axistag {
    width: 76px;
    flex: none;
    color: var(--fg2);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .fog-axis input[type="range"] {
    flex: 1;
    min-width: 0;
    padding: 0;
    height: 16px;
  }
  .fog-axisval {
    width: 52px;
    flex: none;
    text-align: right;
    color: var(--fg3);
    font-variant-numeric: tabular-nums;
  }
  .fog-sec-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--fg3);
    margin-bottom: 6px;
  }
  .fog-covrow {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 2px;
    font-size: 11px;
    width: 100%;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 3px 4px;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }
  .fog-covrow:hover,
  .fog-covrow.open {
    background: var(--bg3);
    border-color: var(--bd);
  }
  .fog-covlabel {
    width: 110px;
    color: var(--fg2);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: none;
  }
  .fog-covbar {
    flex: 1;
    height: 7px;
    border-radius: 999px;
    background: var(--bg3);
    overflow: hidden;
  }
  .fog-covfill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--ac), #5c7cfa);
  }
  .fog-covval {
    width: 78px;
    text-align: right;
    color: var(--fg3);
    flex: none;
  }
  .fog-covtotal {
    margin-top: 8px;
    font-size: 11px;
    color: var(--fg3);
    background: var(--bg3);
    border-radius: 8px;
    padding: 6px 10px;
  }
  .fog-covblocks {
    margin: 2px 0 6px 18px;
    border-left: 2px solid var(--bd);
    padding-left: 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .fog-covblock {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10.5px;
  }
  .fog-covblabel {
    width: 168px;
    color: var(--fg2);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: none;
  }
  .fog-covbbar {
    flex: 1;
    height: 6px;
    border-radius: 999px;
    background: var(--bg3);
    overflow: hidden;
  }
  .fog-covbfill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--ac), #5c7cfa);
    opacity: 0.75;
  }
  .fog-covbval {
    width: 96px;
    text-align: right;
    color: var(--fg3);
    flex: none;
    font-variant-numeric: tabular-nums;
  }
  .fog-mlang + .fog-mlang {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px dashed var(--bd);
  }
  .fog-mlangtitle {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--fg2);
    margin-bottom: 4px;
  }
  .fog-mtable {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }
  .fog-mtable td {
    padding: 4px 8px;
    vertical-align: top;
    border-bottom: 1px solid var(--bd);
  }
  .fog-mk {
    color: var(--fg3);
    width: 110px;
    white-space: nowrap;
    font-weight: 600;
  }
  .fog-mv {
    color: var(--fg);
    word-break: break-word;
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
    font-size: 11px;
  }
  .fog-mv a {
    color: var(--ac);
    text-decoration: underline;
    text-decoration-color: color-mix(in srgb, var(--ac) 50%, transparent);
    cursor: pointer;
  }
  .fog-mv a:hover {
    color: color-mix(in srgb, var(--ac) 75%, #fff);
    text-decoration-color: var(--ac);
  }
  .fog-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 18px;
    height: 18px;
    cursor: nwse-resize;
    background: radial-gradient(
      circle at 100% 100%,
      transparent 12px,
      var(--fg3) 12.5px,
      var(--fg3) 13px,
      transparent 13.5px
    );
    opacity: 0.5;
  }
</style>
