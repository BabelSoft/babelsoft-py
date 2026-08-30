<script lang="ts">
  import Icon from "../icons/Icon.svelte";

  // Character Properties + Character History.
  // Shows the current UCD properties of a character and how its codepoint/name
  // changed across Unicode versions (early characters moved codepoints — the
  // data comes from data/scripts/unicode_1_0_mappings.tsv, not the UCD).

  interface Props {
    show: boolean;
    cp: number;
    onClose: () => void;
  }
  let { show, cp, onClose }: Props = $props();

  const API = "http://127.0.0.1:18080/api";

  interface HistRow {
    version: string;
    date: string;
    present: boolean;
    codepoint: number | null;
    name: string;
    moved: boolean;
    gc: string;
    ccc: string;
    bidi: string;
    decomp: string;
    dec: string;
    digit: string;
    num: string;
    mirrored: string;
    uni1: string;
    iso: string;
    up: string;
    lo: string;
    ti: string;
  }

  // UCD property columns (after Version / Code Point / Name), UnicodeData order.
  const PROP_COLS = [
    "gc",
    "ccc",
    "bidi",
    "decomp",
    "dec",
    "digit",
    "num",
    "mirrored",
    "iso",
    "up",
    "lo",
    "ti",
  ];
  // Headers match the C++ Unicode::UCDFields labels (c/Unicode/Properties.h).
  const HEAD_COLS = [
    "Version",
    "Code Point",
    "Character Name",
    "General Category",
    "Canonical Combining Class",
    "Bidi Class",
    "Decomposition",
    "Numeric Value (1)",
    "Numeric Value (2)",
    "Numeric Value (3)",
    "Bidi Mirrored",
    "ISO Comment",
    "Upper Case Mapping",
    "Lower Case Mapping",
    "Title Case Mapping",
  ];

  type PRow = [key: string, label: string, mono?: boolean];
  // Property sections — mirrors the C++ CDialogProperties fields.
  const PROPS: [string, PRow[]][] = [
    [
      "Identity",
      [
        ["name", "Name"],
        ["formal_aliases", "Formal Alias"],
        ["abbreviation", "Abbreviation"],
        ["unicode1_name", "Unicode 1.0 Name"],
        ["unicode1_codepoint", "Unicode 1.0 Code Point", true],
      ],
    ],
    [
      "Block & Script",
      [
        ["block", "Block"],
        ["script", "Script"],
        ["introduced", "Introduced in Version"],
        ["east_asian_width", "East Asian Width"],
      ],
    ],
    [
      "General",
      [
        ["general_category", "General Category"],
        ["canonical_combining_class", "Canonical Combining Class", true],
        ["bidi_class", "Bidi Class"],
        ["bidi_mirrored", "Bidi Mirrored"],
        ["line_break", "Line Break"],
      ],
    ],
    [
      "Decomposition & Numeric",
      [
        ["decomposition_type", "Decomposition Type"],
        ["decomposition", "Decomposition", true],
        ["numeric_type", "Numeric Type"],
        ["numeric_value", "Numeric Value"],
      ],
    ],
    [
      "Joining",
      [
        ["joining_type", "Joining Type"],
        ["joining_group", "Joining Group"],
      ],
    ],
    [
      "Case Mappings",
      [
        ["simple_uppercase", "Uppercase", true],
        ["simple_lowercase", "Lowercase", true],
        ["simple_titlecase", "Titlecase", true],
      ],
    ],
    [
      "Encodings",
      [
        ["utf8", "UTF-8", true],
        ["utf16", "UTF-16", true],
        ["utf32", "UTF-32", true],
      ],
    ],
  ];

  // Joining Type short char (enum name) -> full name — matches the C++ build
  // which displays "T (Transparent)" etc.
  const JOINING_TYPE_NAMES: Record<string, string> = {
    U: "Non Joining",
    C: "Join Causing",
    D: "Dual Joining",
    L: "Left Joining",
    R: "Right Joining",
    T: "Transparent",
  };

  // "short code [long description]" maps — labels match the C++ build
  // (c/Unicode/Properties.h StrGeneralCategory / StrBidiClass / StrLineBreak /
  // StrCanonicalCombiningClass).
  const GC_LONG: Record<string, string> = {
    Lu: "Letter, Uppercase",
    Ll: "Letter, Lowercase",
    Lt: "Letter, Titlecase",
    Lm: "Letter, Modifier",
    Lo: "Letter, Other",
    Mn: "Mark, Non-Spacing",
    Mc: "Mark, Spacing Combining",
    Me: "Mark, Enclosing",
    Nd: "Number, Decimal",
    Nl: "Number, Letter",
    No: "Number, Other",
    Pc: "Punctuation, Connector",
    Pd: "Punctuation, Dash",
    Ps: "Punctuation, Open",
    Pe: "Punctuation, Close",
    Pi: "Punctuation, Initial quote",
    Pf: "Punctuation, Final quote",
    Po: "Punctuation, Other",
    Sm: "Symbol, Math",
    Sc: "Symbol, Currency",
    Sk: "Symbol, Modifier",
    So: "Symbol, Other",
    Zs: "Separator, Space",
    Zl: "Separator, Line",
    Zp: "Separator, Paragraph",
    Cc: "Other, Control",
    Cf: "Other, Format",
    Cs: "Other, Surrogate",
    Co: "Other, Private Use",
    Cn: "Other, Not Assigned",
  };
  const BIDI_LONG: Record<string, string> = {
    L: "Left-to-Right",
    LRE: "Left-to-Right Embedding",
    LRO: "Left-to-Right Override",
    R: "Right-to-Left",
    AL: "Right-to-Left Arabic",
    RLE: "Right-to-Left Embedding",
    RLO: "Right-to-Left Override",
    PDF: "Pop Directional Format",
    EN: "European Number",
    ES: "European Number Separator",
    ET: "European Number Terminator",
    AN: "Arabic Number",
    CS: "Common Number Separator",
    NSM: "Non-Spacing Mark",
    BN: "Boundary Neutral",
    B: "Paragraph Separator",
    S: "Segment Separator",
    WS: "Whitespace",
    ON: "Other Neutrals",
    LRI: "Left-To-Right Isolate",
    RLI: "Right-To-Left Isolate",
    FSI: "First Strong Isolate",
    PDI: "Pop Directional Isolate",
  };
  const LB_LONG: Record<string, string> = {
    BK: "Mandatory Break",
    CR: "Carriage Return",
    LF: "Line Feed",
    CM: "Attached Characters and Combining Marks",
    NL: "Next Line",
    SG: "Surrogates",
    WJ: "Word Joiner",
    ZW: "Zero Width Space",
    GL: 'Non-breaking ("Glue")',
    CB: "Contingent Break Opportunity",
    SP: "Space",
    B2: "Break Opportunity Before and After",
    BA: "Break Opportunity After",
    BB: "Break Opportunity Before",
    HY: "Hyphen",
    CL: "Closing Punctuation",
    CP: "Closing Parenthesis",
    EX: "Exclamation/Interrogation",
    IN: "Inseparable",
    NS: "Non Starter",
    OP: "Opening Punctuation",
    QU: "Ambiguous Quotation",
    IS: "Infix Separator (Numeric)",
    NU: "Numeric",
    PO: "Postfix (Numeric)",
    PR: "Prefix (Numeric)",
    SY: "Symbols Allowing Breaks",
    AI: "Ambiguous (Alphabetic or Ideographic)",
    AL: "Ordinary Alphabetic and Symbol Characters",
    H2: "Hangul LV Syllable",
    H3: "Hangul LVT Syllable",
    ID: "Ideographic",
    JL: "Hangul L Jamo",
    JV: "Hangul J Jamo",
    JT: "Hangul T Jamo",
    SA: "Complex Context (South East Asian)",
    XX: "Unknown",
    HL: "Hebrew Letter",
    CJ: "Conditional Japanese Starter",
    RI: "Regional Indicator",
    ZWJ: "Zero Width Joiner",
    EB: "Emoji Base",
    EM: "Emoji Modifier",
  };
  const CCC_LONG: Record<string, string> = {
    "0": "Not Reordered",
    "1": "Overlay",
    "6": "Han Reading",
    "7": "Nukta",
    "8": "Kana Voicing",
    "9": "Virama",
    "200": "Attached Below Left",
    "202": "Attached Below",
    "204": "Attached Bottom Right",
    "208": "Attached Left",
    "210": "Attached Right",
    "212": "Attached Top Left",
    "214": "Attached Above",
    "216": "Attached Above Right",
    "218": "Below Left",
    "220": "Below",
    "222": "Below Right",
    "224": "Left",
    "226": "Right",
    "228": "Above Left",
    "230": "Above",
    "232": "Above Right",
    "233": "Double Below",
    "234": "Double Above",
    "240": "Iota Subscript",
  };

  let info = $state<Record<string, any> | null>(null);
  let rows = $state<HistRow[]>([]);
  let loading = $state(false);
  let err = $state("");
  let view = $state<"props" | "extended" | "ideographic" | "history">("props");

  // ── Drag / position state ──
  let x = $state(240);
  let y = $state(120);
  let w = $state(
    Math.min(
      880,
      (typeof window !== "undefined" ? window.innerWidth : 880) - 32,
    ),
  );
  let h = $state(
    Math.min(
      660,
      (typeof window !== "undefined" ? window.innerHeight : 660) - 40,
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
    w = Math.max(640, winStartW + (e.clientX - resizeStartX));
    h = Math.max(360, winStartH + (e.clientY - resizeStartY));
  }
  function onResizeEnd() {
    resizing = false;
    document.removeEventListener("mousemove", onResizeMove);
    document.removeEventListener("mouseup", onResizeEnd);
  }

  function fmt(n: number): string {
    return n.toLocaleString("en-US");
  }
  function hex(n: number): string {
    return n.toString(16).toUpperCase().padStart(4, "0");
  }
  function uhex(n: number): string {
    return "U+" + hex(n);
  }

  $effect(() => {
    if (show && cp >= 0) load();
  });

  async function load() {
    loading = true;
    err = "";
    info = null;
    rows = [];
    try {
      const r1 = await fetch(API + "/codepoint/" + cp);
      if (r1.ok) info = await r1.json();
      const r2 = await fetch(API + "/unicode/history?cp=" + cp);
      if (r2.ok) {
        const d = await r2.json();
        rows = d.rows ?? [];
      } else {
        err = String(r2.status);
      }
    } catch (e: any) {
      err = e.message;
    }
    loading = false;
  }

  const movedCount = $derived(rows.filter((r) => r.moved).length);
  const firstPresent = $derived(rows.find((r) => r.present));
  const glyph = $derived.by(() => {
    try {
      return String.fromCodePoint(cp);
    } catch {
      return "";
    }
  });

  // ── property value formatting ──
  function val(key: string): string {
    if (key === "introduced") {
      // Introduced version is computed from the character history (the first
      // version where this codepoint was present), e.g. "1.0.0 (October 1991)".
      return firstPresent
        ? `${firstPresent.version} (${firstPresent.date})`
        : "";
    }
    if (!info) return "";
    const v = (info as any)[key];
    if (v === undefined || v === null || v === "") {
      // C++ always shows the Joining Group row ("No Joining Group" when none).
      if (key === "joining_group") return "No Joining Group";
      return "";
    }
    if (Array.isArray(v)) return v.join(", ");
    if (key === "unicode1_codepoint") return uhex(v);
    if (key.startsWith("simple_")) return "U+" + v;
    if (key === "joining_type" && JOINING_TYPE_NAMES[v]) {
      return `${v} (${JOINING_TYPE_NAMES[v]})`;
    }
    if (key === "general_category" && GC_LONG[v]) return `${v} [${GC_LONG[v]}]`;
    if (key === "bidi_class" && BIDI_LONG[v]) return `${v} [${BIDI_LONG[v]}]`;
    if (key === "line_break" && LB_LONG[v]) return `${v} [${LB_LONG[v]}]`;
    if (key === "canonical_combining_class" && CCC_LONG[v]) {
      return `${v} [${CCC_LONG[v]}]`;
    }
    if (key === "bidi_mirrored") {
      return v === "Y" ? "Yes" : v === "N" ? "No" : String(v);
    }
    if (key === "decomposition_type" && v === "None_") return "";
    if (key === "numeric_type" && v === "None") return "";
    return String(v);
  }
  function nonEmpty(key: string): boolean {
    return val(key) !== "";
  }

  const nameslistHas = $derived(
    !!info?.nameslist &&
      (info.nameslist.aliases?.length ||
        info.nameslist.notes?.length ||
        info.nameslist.xrefs?.length),
  );
  const stdVarCount = $derived(
    (info?.standardized_variants?.length || 0) +
      (info?.emoji_variants?.length || 0),
  );
  function vsIndex(vs: number): number {
    if (vs >= 0xfe00 && vs <= 0xfe0f) return vs - 0xfe00 + 1; // VS1..VS16
    if (vs >= 0xe0100 && vs <= 0xe01ef) return vs - 0xe0100 + 17; // VS17..VS256
    return vs;
  }
  function hexSeq(cps: number[]): string {
    return cps.map((c) => uhex(c)).join(" ");
  }

  // ── Copy properties as text (mirrors C++ CopyProperties) ──
  async function copyProps() {
    if (!info) return;
    const lines: string[] = [
      `Character Properties for ${uhex(cp)} — ${info.name ?? ""}`,
    ];
    for (const [title, props] of PROPS) {
      const filled = props.filter((r) => nonEmpty(r[0]));
      if (!filled.length) continue;
      lines.push(`[${title}]`);
      for (const [k, label] of filled) lines.push(`  ${label}: ${val(k)}`);
    }
    if (info.binary_properties?.length)
      lines.push("[Binary Properties]\n  " + info.binary_properties.join(", "));
    if (nameslistHas) {
      lines.push("[Notes, Aliases & Cross-References]");
      for (const a of info.nameslist?.aliases ?? []) lines.push(`  = ${a}`);
      for (const n of info.nameslist?.notes ?? []) lines.push(`  * ${n}`);
      for (const x of info.nameslist?.xrefs ?? []) lines.push(`  x ${x}`);
    }
    if (info.standardized_variants?.length) {
      lines.push("[Standardized Variation Sequences]");
      for (const [vs, desc] of info.standardized_variants)
        lines.push(`  VS${vsIndex(vs)} <${uhex(cp)} ${uhex(vs)}> = ${desc}`);
    }
    if (info.named_sequences?.length) {
      lines.push("[Named Sequences]");
      for (const [name, cps] of info.named_sequences)
        lines.push(`  ${name}; ${hexSeq(cps)}`);
    }
    if (rows.length) {
      lines.push("[Character History]");
      for (const r of rows) {
        lines.push(
          `  ${r.version} ${r.present && r.codepoint != null ? uhex(r.codepoint) : "—"} ${r.name}`,
        );
      }
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
    } catch {
      /* clipboard unavailable */
    }
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }
</script>

<svelte:window onkeydown={onKey} />

{#if show}
  <div
    class="cpd"
    class:dragging
    class:resizing
    style="left:{x}px; top:{y}px; width:{w}px; height:{h}px;"
  >
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="cpd-header" onmousedown={onDragStart}>
      <span class="cpd-title"
        >Character Properties — {info?.name || uhex(cp)}</span
      >
      {#if movedCount > 0}
        <span class="cpd-moved">moved {movedCount}×</span>
      {/if}
      <button class="cpd-copy" onclick={copyProps} title="Copy properties"
        ><Icon name="copy" size={14} /></button
      >
      <button class="cpd-close" onclick={onClose} title="Close"
        ><Icon name="close" size={14} /></button
      >
    </div>

    <div class="cpd-body">
      {#if loading}
        <div class="cpd-empty">Loading…</div>
      {:else}
        <!-- summary bar -->
        <div class="cpd-summary">
          <span class="cpd-glyph">{glyph}</span>
          <div class="cpd-sinfo">
            <div class="cpd-sname">{info?.name || "—"}</div>
            <div class="cpd-smeta">
              <span class="mono cpd-cp">{uhex(cp)}</span>
              {#if info?.block}<span class="cpd-chip">{info.block}</span>{/if}
              {#if info?.script}<span class="cpd-chip">{info.script}</span>{/if}
              {#if firstPresent}<span class="cpd-chip"
                  >Unicode {firstPresent.version}</span
                >{/if}
            </div>
          </div>
        </div>

        <!-- tabs -->
        <div class="cpd-tabs">
          <button class:on={view === "props"} onclick={() => (view = "props")}
            >Unicode Properties</button
          >
          <button
            class:on={view === "extended"}
            onclick={() => (view = "extended")}>Extended Properties</button
          >
          {#if info?.ideographic && Object.keys(info.ideographic).length}
            <button
              class:on={view === "ideographic"}
              onclick={() => (view = "ideographic")}
              >Ideographic Properties</button
            >
          {/if}
          <button
            class:on={view === "history"}
            onclick={() => (view = "history")}
            >Character History ({rows.length})</button
          >
        </div>

        {#if view === "props"}
          <div class="cpd-props">
            <div class="cpd-cols">
              <div class="cpd-col">
                {#each PROPS as [title, props]}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">{title}</div>
                    <table class="cpd-ptable">
                      <tbody>
                        {#each props as r}
                          <tr class:empty={!nonEmpty(r[0])}>
                            <td class="cpd-k">{r[1]}</td>
                            <td class="mono">{val(r[0])}</td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/each}
              </div>

              <div class="cpd-col">
                {#if nameslistHas}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">
                      Notes, Aliases &amp; Cross-References
                    </div>
                    <table class="cpd-ptable">
                      <tbody>
                        {#each info!.nameslist.aliases as a}<tr
                            ><td class="cpd-k mono">=</td><td class="mono"
                              >{a}</td
                            ></tr
                          >{/each}
                        {#each info!.nameslist.notes as n}<tr
                            ><td class="cpd-k mono">*</td><td
                              class="mono cpd-wrap">{n}</td
                            ></tr
                          >{/each}
                        {#each info!.nameslist.xrefs as x}<tr
                            ><td class="cpd-k mono">x</td><td class="mono"
                              >{x}</td
                            ></tr
                          >{/each}
                      </tbody>
                    </table>
                  </div>
                {/if}

                {#if info?.binary_properties?.length}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">Binary Properties</div>
                    <div class="cpd-bins">
                      {#each info.binary_properties as bp}<span class="cpd-bin"
                          >{bp}</span
                        >{/each}
                    </div>
                  </div>
                {/if}

                {#if stdVarCount > 0}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">
                      Standardized Variation Sequences
                    </div>
                    <table class="cpd-ptable">
                      <tbody>
                        {#each info!.standardized_variants as [vs, desc]}
                          <tr>
                            <td class="cpd-k cpd-vs"
                              >{glyph}{String.fromCodePoint(vs)}</td
                            >
                            <td>
                              <div class="cpd-vs-t">
                                <span class="cpd-vs-n">VS{vsIndex(vs)}</span
                                ><span class="mono cpd-vs-s"
                                  >{uhex(cp)} {uhex(vs)}</span
                                >
                              </div>
                              <div class="cpd-vs-b cpd-wrap">{desc}</div>
                            </td>
                          </tr>
                        {/each}
                        {#each info!.emoji_variants as [vs, style]}
                          <tr>
                            <td class="cpd-k cpd-vs"
                              >{glyph}{String.fromCodePoint(vs)}</td
                            >
                            <td>
                              <div class="cpd-vs-t">
                                <span class="cpd-vs-n">VS{vsIndex(vs)}</span
                                ><span class="mono cpd-vs-s"
                                  >{uhex(cp)} {uhex(vs)}</span
                                >
                              </div>
                              <div class="cpd-vs-b cpd-wrap">{style}</div>
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}

                {#if info?.ideographic_variants?.length}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">
                      Ideographic Variation Sequences
                    </div>
                    <table class="cpd-ptable">
                      <tbody>
                        {#each info!.ideographic_variants as [vs, coll, ref]}
                          <tr>
                            <td class="cpd-k cpd-vs"
                              >{glyph}{String.fromCodePoint(vs)}</td
                            >
                            <td>
                              <div class="cpd-vs-t">
                                <span class="cpd-vs-n">VS{vsIndex(vs)}</span
                                ><span class="mono cpd-vs-s"
                                  >{uhex(cp)} {uhex(vs)}</span
                                >
                              </div>
                              <div class="cpd-vs-b2">
                                <span class="cpd-vs-src">{coll}</span><span
                                  class="cpd-vs-id">{ref}</span
                                >
                              </div>
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}

                {#if info?.named_sequences?.length}
                  <div class="cpd-sec">
                    <div class="cpd-sec-title">Named Sequences</div>
                    <table class="cpd-ptable">
                      <tbody>
                        {#each info!.named_sequences as [name, cps]}
                          <tr
                            ><td class="cpd-k mono cpd-wrap">{name}</td><td
                              class="mono">{hexSeq(cps)}</td
                            ></tr
                          >
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </div>
            </div>
          </div>
        {:else if view === "extended"}
          <div class="cpd-props">
            <div class="cpd-x">
              <div class="cpd-sec-title">Extended Character Properties</div>
              <table class="cpd-ptable">
                <thead>
                  <tr>
                    <th class="cpd-xh">Property</th>
                    <th class="cpd-xh">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {#each info?.extended ?? [] as [label, value]}
                    <tr class:empty={!value}>
                      <td class="cpd-k">{label}</td>
                      <td class="mono cpd-wrap">{value}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
              <div class="cpd-x-alias">
                <div class="cpd-sec-title">Name Aliases</div>
                <table class="cpd-ptable">
                  <thead>
                    <tr>
                      <th class="cpd-xh">Alias Type</th>
                      <th class="cpd-xh">Alias</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each info?.name_aliases ?? [] as [type, alias]}
                      <tr>
                        <td class="cpd-k mono">{type}</td>
                        <td class="mono">{alias}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        {:else if view === "ideographic"}
          <div class="cpd-props">
            <div class="cpd-x">
              <div class="cpd-sec-title">Ideographic Properties</div>
              <table class="cpd-ptable">
                <tbody>
                  <tr class:empty={!info?.ideographic?.radical?.glyph}>
                    <td class="cpd-k">Kangxi Radical</td>
                    <td>
                      {#if info?.ideographic?.radical?.glyph}
                        <span class="cpd-glyph-sm"
                          >{info.ideographic.radical.glyph.char}</span
                        >
                        <span class="mono cpd-cp2"
                          >{uhex(info.ideographic.radical.glyph.cp)}</span
                        >
                      {/if}
                    </td>
                  </tr>
                  <tr class:empty={!info?.ideographic?.radical?.strokes}>
                    <td class="cpd-k">Radical/Strokes</td>
                    <td class="mono"
                      >{info?.ideographic?.radical?.strokes ?? ""}</td
                    >
                  </tr>
                  <tr class:empty={!info?.ideographic?.ids}>
                    <td class="cpd-k">IDS</td>
                    <td class="cpd-wrap">{info?.ideographic?.ids ?? ""}</td>
                  </tr>
                </tbody>
              </table>

              <div class="cpd-sec-title">Related Characters</div>
              <table class="cpd-ptable">
                <tbody>
                  {#each [["Traditional Form", "traditional"], ["Chinese Simplified", "simplified_chinese"], ["Japanese Simplified", "simplified_japanese"]] as [label, key]}
                    {@const g = info?.ideographic?.related?.[key]}
                    <tr class:empty={!g}>
                      <td class="cpd-k">{label}</td>
                      <td>
                        {#if g}
                          <span class="cpd-glyph-sm">{g.char}</span>
                          <span class="mono cpd-cp2">{uhex(g.cp)}</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>

              <div class="cpd-sec-title">Readings</div>
              <table class="cpd-ptable">
                <tbody>
                  {#each [["Mandarin", "mandarin"], ["Cantonese", "cantonese"], ["Korean", "korean"], ["Vietnamese", "vietnamese"]] as [label, key]}
                    <tr class:empty={!info?.ideographic?.readings?.[key]}>
                      <td class="cpd-k">{label}</td>
                      <td class="cpd-wrap"
                        >{info?.ideographic?.readings?.[key] ?? ""}</td
                      >
                    </tr>
                  {/each}
                </tbody>
              </table>

              <div class="cpd-sec-title">Source References</div>
              <table class="cpd-ptable">
                <tbody>
                  {#each info?.ideographic?.sources ?? [] as [label, ref]}
                    <tr class:empty={!ref}>
                      <td class="cpd-k">{label}</td>
                      <td class="mono">{ref}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {:else}
          <div class="cpd-h">
            <span class="cpd-htitle">Character History</span>
            {#if firstPresent}
              <span class="cpd-hsub"
                >first encoded in {firstPresent.version}</span
              >
            {/if}
          </div>
          <div class="cpd-hwrap">
            <table class="cpd-htable">
              <thead>
                <tr>
                  {#each HEAD_COLS as h}<th>{h}</th>{/each}
                </tr>
              </thead>
              <tbody>
                {#each rows as r}
                  <tr class:abs={!r.present} class:mv={r.moved}>
                    <td class="cpd-ver mono">{r.version}</td>
                    <td class="mono"
                      >{r.present && r.codepoint != null
                        ? uhex(r.codepoint)
                        : "—"}</td
                    >
                    <td class="cpd-nm mono">{r.present ? r.name : ""}</td>
                    {#each PROP_COLS as k}
                      <td class="mono">{(r as any)[k]}</td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
            {#if err}<div class="cpd-empty">Error {err}</div>{/if}
          </div>
        {/if}
      {/if}
    </div>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="cpd-resize" onmousedown={onResizeStart}></div>
  </div>
{/if}

<style>
  .cpd {
    position: fixed;
    z-index: 310;
    background: var(--bg2);
    border: 2px solid var(--ac);
    border-radius: 10px;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 560px;
    min-height: 320px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 24px);
    user-select: none;
  }
  .cpd.dragging,
  .cpd.resizing {
    opacity: 0.92;
    transition: none;
  }
  .cpd-header {
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
  .cpd-header:active {
    cursor: grabbing;
  }
  .cpd-title {
    font-size: 13px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cpd-moved {
    background: rgba(255, 255, 255, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.5);
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 5px;
  }
  .cpd-close {
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
  .cpd-close:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .cpd-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .cpd-props {
    flex: 1;
    overflow: auto;
  }
  .cpd-cols {
    display: flex;
    gap: 28px;
    align-items: flex-start;
    padding: 4px 14px 14px;
  }
  .cpd-col {
    flex: 1;
    min-width: 0;
  }
  .cpd-wrap {
    white-space: normal;
    word-break: break-word;
  }
  .cpd-sec {
    margin-top: 10px;
  }
  .cpd-sec-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--fg3, #6e7191);
    margin: 4px 0 2px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.15));
  }
  .cpd-summary {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    flex-shrink: 0;
  }
  .cpd-glyph {
    font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji",
      sans-serif;
    font-size: 44px;
    line-height: 1;
    min-width: 56px;
    text-align: center;
  }
  .cpd-sinfo {
    min-width: 0;
  }
  .cpd-sname {
    font-size: 15px;
    font-weight: 600;
  }
  .cpd-smeta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    margin-top: 4px;
  }
  .cpd-cp {
    font-weight: 600;
  }
  .cpd-chip {
    background: var(--bg3, #2d2e4a);
    color: var(--fg2, #b0b3cc);
    font-size: 11px;
    padding: 1px 8px;
    border-radius: 10px;
  }
  .cpd-bins {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .cpd-bin {
    background: var(--bg3, #2d2e4a);
    border: 1px solid var(--br, rgba(128, 128, 128, 0.25));
    color: var(--fg2, #b0b3cc);
    font-family: Consolas, Menlo, monospace;
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 4px;
  }
  .cpd-tabs {
    display: flex;
    gap: 4px;
    padding: 6px 12px 0;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    flex-shrink: 0;
  }
  .cpd-tabs button {
    border: 1px solid transparent;
    border-bottom: none;
    background: transparent;
    color: var(--fg2, #b0b3cc);
    font-size: 12px;
    padding: 6px 12px;
    cursor: pointer;
    border-radius: 6px 6px 0 0;
  }
  .cpd-tabs button.on {
    background: var(--bg3, #2d2e4a);
    color: var(--fg, #e4e6f0);
    font-weight: 600;
  }
  .cpd-copy {
    margin-left: auto;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.85);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .cpd-copy:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.2);
  }
  .cpd-ptable {
    border-collapse: collapse;
    font-size: 12px;
    width: 100%;
  }
  .cpd-ptable td {
    padding: 1px 12px 1px 0;
    vertical-align: top;
  }
  .cpd-k {
    color: var(--fg2, #999);
    white-space: nowrap;
    width: 1%;
    padding-right: 16px !important;
  }
  .cpd-ptable tr.empty td {
    color: var(--fg3, #6e7191);
    opacity: 0.6;
  }
  .cpd-ptable th.cpd-xh {
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--fg2, #999);
    padding: 2px 12px 2px 0;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
  }
  .cpd-x {
    padding: 4px 14px 14px;
  }
  .cpd-x-alias {
    margin-top: 18px;
  }
  .cpd-glyph-sm {
    font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji",
      "Segoe UI", sans-serif;
    font-size: 26px;
    line-height: 1.1;
    vertical-align: middle;
    margin-right: 8px;
  }
  .cpd-cp2 {
    color: var(--fg2, #999);
    font-size: 11px;
    vertical-align: middle;
  }
  .cpd-vs {
    font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji",
      "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 22px;
    line-height: 1.2;
    color: var(--fg, #e4e6f0);
    white-space: nowrap;
  }
  .cpd-vs-t {
    display: flex;
    align-items: baseline;
    gap: 10px;
    white-space: nowrap;
  }
  .cpd-vs-n {
    font-family: Consolas, Menlo, monospace;
    font-weight: 600;
    color: var(--fg, #e4e6f0);
    font-size: 12px;
  }
  .cpd-vs-s {
    color: var(--fg2, #999);
    font-size: 11px;
  }
  .cpd-vs-b {
    font-size: 11px;
    color: var(--fg2, #999);
    margin-top: 1px;
  }
  .cpd-vs-b2 {
    display: flex;
    gap: 14px;
    font-size: 11px;
    color: var(--fg2, #999);
    margin-top: 1px;
  }
  .cpd-vs-src {
    color: var(--fg2, #999);
    min-width: 120px;
    white-space: nowrap;
  }
  .cpd-vs-id {
    color: var(--fg2, #999);
  }
  .cpd-h {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    flex-shrink: 0;
  }
  .cpd-htitle {
    font-size: 12px;
    font-weight: 600;
  }
  .cpd-hsub {
    font-size: 11px;
    color: var(--fg2, #999);
  }
  .cpd-hwrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
    padding: 0 12px 12px;
  }
  .cpd-htable {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  .cpd-htable th {
    text-align: left;
    position: sticky;
    top: 0;
    background: var(--bg2);
    color: var(--fg2, #999);
    font-weight: 600;
    padding: 4px 10px 4px 0;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.3));
    white-space: nowrap;
  }
  .cpd-htable td {
    padding: 2px 10px 2px 0;
    vertical-align: top;
    border-bottom: 1px solid var(--br, rgba(128, 128, 128, 0.12));
    white-space: nowrap;
  }
  .cpd-nm {
    white-space: normal !important;
    min-width: 220px;
  }
  .cpd-htable tr.abs td {
    color: var(--fg2, #999);
    opacity: 0.55;
  }
  .cpd-htable tr.mv td {
    background: color-mix(in srgb, var(--ac, #4a90d9) 14%, transparent);
  }
  .cpd-ver {
    white-space: nowrap;
  }
  .mono {
    font-family: Consolas, Menlo, monospace;
    white-space: nowrap;
  }
  .cpd-empty {
    padding: 12px;
    font-size: 12px;
    color: var(--fg2, #999);
  }
  .cpd-resize {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 16px;
    height: 16px;
    cursor: nwse-resize;
  }
  .cpd-resize::after {
    content: "";
    position: absolute;
    right: 3px;
    bottom: 3px;
    width: 8px;
    height: 8px;
    border-right: 2px solid var(--fg3, #6e7191);
    border-bottom: 2px solid var(--fg3, #6e7191);
    border-bottom-right-radius: 3px;
  }
</style>
