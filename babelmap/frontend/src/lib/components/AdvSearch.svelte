<script lang="ts">
  import { t } from "../i18n.svelte";

  interface Props {
    sv: string;
    onSvChange: (v: string) => void;
    onSearch: () => void;
    onSearchPrev: () => void;
    onSearchNext: () => void;
  }

  let { sv, onSvChange, onSearch, onSearchPrev, onSearchNext }: Props = $props();

  let sugOpen = $state(false);
  let suggestions = $state<any[]>([]);
  let sugIdx = $state(-1);
  let _sugQuery = $state("");

  // Static property list — no backend call needed
  const ALL_PROPS = [
    { key: "name", label: "Name", type: "text", desc: "|cc starts, cc| ends, |cc| exact, cc contains" },
    { key: "formalalias", label: "FormalAlias", type: "text", desc: "Formal name alias" },
    { key: "unicode1name", label: "Unicode1Name", type: "text", desc: "Unicode 1.0 name" },
    { key: "aliases", label: "Aliases", type: "text", desc: "All names & aliases" },
    { key: "wholewords", label: "WholeWords", type: "bool", values: ["True", "False"], desc: "Whole word matching" },
    {
      key: "gc",
      label: "GeneralCategory",
      type: "enum",
      values: ["Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "No", "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Zs", "Zl", "Zp", "Cc", "Cf", "Cs", "Co", "Cn"],
      desc: "",
    },
    { key: "ccc", label: "CanonicalCombiningClass", type: "text", desc: "0-240" },
    {
      key: "bc",
      label: "BidiClass",
      type: "enum",
      values: ["L", "R", "AL", "EN", "ES", "ET", "AN", "CS", "NSM", "BN", "B", "S", "WS", "ON", "LRE", "LRO", "RLE", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"],
      desc: "",
    },
    { key: "bm", label: "BidiMirrored", type: "bool", values: ["True", "False"], desc: "" },
    { key: "dt", label: "DecompositionType", type: "text", desc: "canonical, compat, circle, font" },
    { key: "nt", label: "NumericType", type: "text", desc: "Decimal, Digit, Numeric, None" },
    { key: "lb", label: "LineBreak", type: "text", desc: "AK, AL, BB, BK" },
    { key: "binary", label: "BinaryProperty", type: "text", desc: "Dash, Math, Emoji, ID_Start" },
    { key: "script", label: "Script", type: "text", desc: "Latn, Hani, Cyrl" },
    { key: "block", label: "Block", type: "text", desc: "Block name" },
    { key: "unicode", label: "Unicode", type: "version", desc: "5.0, >=5.0, <=5.0" },
    { key: "nocjkui", label: "NoCJKUI", type: "bool", values: ["True", "False"], desc: "Exclude CJK UI" },
    { key: "nopua", label: "NoPUA", type: "bool", values: ["True", "False"], desc: "Exclude PUA" },
  ];

  function fetchSuggestions(q: string) {
    if (!q) {
      suggestions = [];
      sugOpen = false;
      return;
    }
    _sugQuery = q;
    const qu = q.toLowerCase();
    // Property suggestions
    const props = ALL_PROPS.filter((p) => p.key.includes(qu) || p.label.toLowerCase().includes(qu)).map((p) => ({
      key: p.key,
      label: p.label,
      type: p.type,
      values: p.values,
      desc: p.desc || (p.values ? p.values.slice(0, 5).join(", ") + "…" : ""),
    }));
    // Operator suggestions
    const ops = [
      { key: " AND ", label: "AND", type: "op", values: undefined, desc: "Logical AND" },
      { key: " OR ", label: "OR", type: "op", values: undefined, desc: "Logical OR" },
      { key: " NOT ", label: "NOT", type: "op", values: undefined, desc: "Logical NOT" },
    ].filter((o) => o.label.toLowerCase().includes(qu));
    suggestions = [...props, ...ops];
    sugOpen = suggestions.length > 0;
    sugIdx = -1;
  }
  function onInput(e: Event) {
    const v = (e.target as HTMLInputElement).value;
    onSvChange(v);
    const words = v.split(/\s+/);
    const last = words[words.length - 1];
    if (last && !last.includes("=") && !last.includes(":") && !last.includes("!") && !last.includes(">") && !last.includes("<")) {
      fetchSuggestions(last);
    } else {
      sugOpen = false;
      suggestions = [];
    }
  }
  function pickSug(idx: number) {
    if (idx < 0 || idx >= suggestions.length) return;
    const s = suggestions[idx];
    const suffix = s.type === "op" ? s.key : s.key + "=";
    const v = sv.endsWith(_sugQuery) ? sv.slice(0, -_sugQuery.length) + suffix : sv + " " + suffix;
    onSvChange(v);
    suggestions = [];
    sugOpen = false;
  }
  function onKeydown(e: KeyboardEvent) {
    if (sugOpen) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        sugIdx = Math.min(sugIdx + 1, suggestions.length - 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        sugIdx = Math.max(sugIdx - 1, -1);
      } else if (e.key === "Enter" && sugIdx >= 0) {
        e.preventDefault();
        pickSug(sugIdx);
      } else if (e.key === "Escape") {
        sugOpen = false;
        suggestions = [];
      }
    } else if (e.key === "Enter") {
      onSearch();
    }
  }
</script>

<fieldset class="fs">
  <legend>{t("bottom.search_name")}</legend>
  <div class="adv-wrap">
    <input
      type="text"
      value={sv}
      oninput={onInput}
      onkeydown={onKeydown}
      onfocus={() => {
        if (sv) fetchSuggestions(sv.split(/\s+/).pop() || sv);
      }}
      onblur={() =>
        setTimeout(() => {
          sugOpen = false;
        }, 200)}
      placeholder={t("bottom.search_name") + "  e.g. gc=Lu AND script=Latin"}
    />
    <button class="adv-btn" onclick={onSearchPrev} title={t("find.search_prev")}>⬅</button>
    <button class="adv-btn" onclick={onSearchNext} title={t("find.search_next")}>➡</button>
    {#if sugOpen && suggestions.length > 0}
      <div class="adv-sug">
        {#each suggestions as s, i}
          <button class="adv-sug-item" class:active={i === sugIdx} onclick={() => pickSug(i)} onmousedown={(e) => e.preventDefault()}>
            <span class="sug-key">{s.key}</span>
            <span class="sug-label">{s.label}</span>
            <span class="sug-desc">{s.desc || (s.values ? s.values.slice(0, 5).join(", ") + "…" : "")}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>
</fieldset>

<style>
  .fs {
    flex: 2;
  }
  .adv-wrap {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  .adv-wrap input {
    flex: 1;
    min-width: 0;
  }
  .adv-btn {
    flex-shrink: 0;
    height: 26px;
    width: 26px;
    padding: 0;
    font-size: 14px;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg3);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 6px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .adv-btn:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }

  .adv-sug {
    position: absolute;
    top: calc(100% + 3px);
    left: 0;
    max-width: 340px;
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 8px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
    z-index: 100;
    padding: 3px;
  }
  .adv-sug-item {
    display: flex;
    align-items: baseline;
    gap: 8px;
    width: 100%;
    padding: 4px 8px;
    font-size: 12px;
    font-family: inherit;
    text-align: left;
    background: transparent;
    color: var(--fg);
    border: none;
    border-radius: 5px;
    cursor: pointer;
    height: auto;
  }
  .adv-sug-item:hover,
  .adv-sug-item.active {
    background: var(--ac);
    color: #fff;
  }
  .sug-key {
    font-weight: 700;
    font-family: monospace;
    font-size: 11px;
    min-width: 50px;
  }
  .sug-label {
    color: var(--fg2);
    font-size: 11px;
    min-width: 90px;
  }
  .adv-sug-item:hover .sug-label,
  .adv-sug-item.active .sug-label {
    color: rgba(255, 255, 255, 0.7);
  }
  .sug-desc {
    color: var(--fg3);
    font-size: 10px;
    margin-left: auto;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .adv-sug-item:hover .sug-desc,
  .adv-sug-item.active .sug-desc {
    color: rgba(255, 255, 255, 0.6);
  }
</style>
