<script lang="ts">
  import { t } from "../i18n.svelte";

  let {
    show = false,
    buf = "",
    conv = () => "",
    fsize = 16,
    onClose = () => {},
    onSaved = () => {},
  }: {
    show: boolean;
    buf: string;
    conv: () => string;
    fsize: number;
    onClose: () => void;
    onSaved: () => void;
  } = $props();

  let encoding = $state("utf-8");
  let bom = $state(true);
  let newline = $state("crlf");
  let filename = $state("babelmap.txt");

  const ENCODINGS: { v: string; l: string }[] = [
    { v: "utf-8", l: "UTF-8" },
    { v: "utf-16le", l: "UTF-16 LE" },
    { v: "utf-16be", l: "UTF-16 BE" },
    { v: "utf-32le", l: "UTF-32 LE" },
    { v: "utf-32be", l: "UTF-32 BE" },
  ];

  const NEWLINES: { v: string; l: string }[] = [
    { v: "crlf", l: "CR+LF (\\r\\n)" },
    { v: "lf", l: "LF (\\n)" },
    { v: "cr", l: "CR (\\r)" },
    { v: "ls", l: "U+2028 Line Separator" },
    { v: "ps", l: "U+2029 Paragraph Separator" },
  ];

  function close() {
    onClose();
  }

  function save() {
    const text = conv();
    const nl = newline === "crlf" ? "\r\n" : newline === "lf" ? "\n" : newline === "cr" ? "\r" : newline === "ls" ? "\u2028" : "\u2029";
    const normalized = text.replace(/\r\n?|\n|\u2028|\u2029/g, nl);

    let uint8: Uint8Array;
    const encoder = new TextEncoder();
    const bomMap: Record<string, number[]> = {
      "utf-8": [0xef, 0xbb, 0xbf],
      "utf-16le": [0xff, 0xfe],
      "utf-16be": [0xfe, 0xff],
      "utf-32le": [0xff, 0xfe, 0x00, 0x00],
      "utf-32be": [0x00, 0x00, 0xfe, 0xff],
    };

    if (encoding === "utf-8") {
      const bytes = encoder.encode(normalized);
      if (bom) {
        const b = new Uint8Array(bomMap["utf-8"]);
        uint8 = new Uint8Array(b.length + bytes.length);
        uint8.set(b, 0);
        uint8.set(bytes, b.length);
      } else {
        uint8 = bytes;
      }
    } else {
      uint8 = encodeMultiByte(normalized, encoding, bom ? bomMap[encoding] : null);
    }

    triggerDownload(uint8, filename);
    onSaved();
  }

  function encodeMultiByte(text: string, enc: string, bomBytes: number[] | null): Uint8Array {
    const isLE = enc.endsWith("le");
    const is32 = enc.startsWith("utf-32");
    const parts: number[] = [];
    if (bomBytes) parts.push(...bomBytes);
    for (const ch of text) {
      let cp = ch.codePointAt(0) ?? 0xfffd;
      if (is32) {
        if (isLE) {
          parts.push(cp & 0xff, (cp >> 8) & 0xff, (cp >> 16) & 0xff, (cp >> 24) & 0xff);
        } else {
          parts.push((cp >> 24) & 0xff, (cp >> 16) & 0xff, (cp >> 8) & 0xff, cp & 0xff);
        }
      } else {
        if (cp > 0xffff) {
          cp -= 0x10000;
          const hi = 0xd800 | (cp >> 10);
          const lo = 0xdc00 | (cp & 0x3ff);
          if (isLE) {
            parts.push(hi & 0xff, (hi >> 8) & 0xff, lo & 0xff, (lo >> 8) & 0xff);
          } else {
            parts.push((hi >> 8) & 0xff, hi & 0xff, (lo >> 8) & 0xff, lo & 0xff);
          }
        } else {
          if (isLE) {
            parts.push(cp & 0xff, (cp >> 8) & 0xff);
          } else {
            parts.push((cp >> 8) & 0xff, cp & 0xff);
          }
        }
      }
    }
    return new Uint8Array(parts);
  }

  function triggerDownload(data: Uint8Array, name: string) {
    const blob = new Blob([data as BlobPart], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>

{#if show}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-mask" onclick={close} onkeydown={(e) => e.key === "Escape" && close()}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal-dlg" onclick={(e) => e.stopPropagation()}>
      <h3 class="modal-title">{t("save.title")}</h3>
      <div class="modal-body">
        <label class="sfl">
          <span>{t("save.encoding")}</span>
          <select bind:value={encoding}>
            {#each ENCODINGS as e}<option value={e.v}>{e.l}</option>{/each}
          </select>
        </label>
        <label class="sfl">
          <span>{t("save.byte_order")}</span>
          <select bind:value={bom}>
            <option value={true}>{t("save.bom")}</option>
            <option value={false}>{t("save.no_bom")}</option>
          </select>
        </label>
        <label class="sfl">
          <span>{t("save.newline")}</span>
          <select bind:value={newline}>
            {#each NEWLINES as n}<option value={n.v}>{n.l}</option>{/each}
          </select>
        </label>
        <label class="sfl">
          <span>{t("save.filename")}</span>
          <input type="text" bind:value={filename} />
        </label>
      </div>
      <div class="modal-ft">
        <button class="sb" onclick={save}>{t("save.save_btn")}</button>
        <button class="sb" onclick={close}>{t("save.cancel")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 500;
  }
  .modal-dlg {
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 14px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
    padding: 20px 24px;
    min-width: 380px;
    max-width: 440px;
  }
  .modal-title {
    margin: 0 0 16px;
    font-size: 14px;
    color: var(--fg);
    font-weight: 700;
  }
  .modal-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }
  .sfl {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .sfl span {
    font-size: 11px;
    color: var(--fg3);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .sfl select,
  .sfl input {
    width: 100%;
  }
  .modal-ft {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .sb {
    height: 26px;
    padding: 0 10px;
    font-size: 11px;
    font-weight: 600;
    background: var(--bg3);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    cursor: pointer;
    font-family: inherit;
  }
  .sb:hover {
    background: var(--ac);
    color: #fff;
    border-color: var(--ac);
  }
  input,
  select {
    font-family: inherit;
    font-size: 12px;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 5px 8px;
    outline: none;
  }
</style>
