<script lang="ts">
  import { t } from "../i18n.svelte";

  let {
    show = false,
    x = 0,
    y = 0,
    hasSel = false,
    buf = "",
    textarea = null as HTMLTextAreaElement | null,
    onClose = () => {},
    onBufChange = (_v: string) => {},
  }: {
    show: boolean;
    x: number;
    y: number;
    hasSel: boolean;
    buf: string;
    textarea: HTMLTextAreaElement | null;
    onClose: () => void;
    onBufChange: (v: string) => void;
  } = $props();

  let adjustedY = $state(0);

  $effect(() => {
    adjustedY = y;
    if (show) {
      requestAnimationFrame(() => {
        const el = document.querySelector(".ctx-menu") as HTMLElement | null;
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.bottom > window.innerHeight) {
            adjustedY = Math.max(0, y - rect.height - 4);
          }
        }
      });
    }
  });

  function close() {
    onClose();
  }

  function exec(cmd: string) {
    textarea?.focus();
    document.execCommand(cmd);
    close();
  }
  function ctxUndo() {
    exec("undo");
  }
  function ctxCut() {
    exec("cut");
  }
  function ctxCopy() {
    exec("copy");
  }
  function ctxPaste() {
    exec("paste");
  }
  function ctxDelete() {
    exec("delete");
  }
  function ctxSelectAll() {
    textarea?.focus();
    textarea?.select();
    close();
  }

  function ctxSetDir(dir: string) {
    if (textarea) textarea.dir = dir;
    close();
  }

  function ctxSetLineSp(sp: number) {
    if (textarea) textarea.style.lineHeight = String(sp);
    close();
  }

  function applyCaseTransform(transform: (s: string) => string) {
    const ta = textarea;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    if (start === end) {
      close();
      return;
    }
    const before = buf.slice(0, start);
    const sel = buf.slice(start, end);
    const after = buf.slice(end);
    const result = before + transform(sel) + after;
    onBufChange(result);
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(start, start + transform(sel).length);
    });
    close();
  }

  function ctxUpper() {
    applyCaseTransform((s) => s.toLocaleUpperCase());
  }
  function ctxLower() {
    applyCaseTransform((s) => s.toLocaleLowerCase());
  }
  function ctxTitle() {
    applyCaseTransform((s) => s.replace(/\S+/g, (w) => w.charAt(0).toLocaleUpperCase() + w.slice(1).toLocaleLowerCase()));
  }

  function applyNormalize(form: "NFD" | "NFC" | "NFKD" | "NFKC") {
    const ta = textarea;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    if (start === end) {
      close();
      return;
    }
    const before = buf.slice(0, start);
    const sel = buf.slice(start, end);
    const after = buf.slice(end);
    const normalized = sel.normalize(form);
    onBufChange(before + normalized + after);
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(start, start + normalized.length);
    });
    close();
  }
</script>

{#if show}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="ctx-mask" onclick={close} onkeydown={(e) => e.key === "Escape" && close()}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="ctx-menu" style="left:{x}px;top:{adjustedY}px" onclick={(e) => e.stopPropagation()}>
      <div class="cmi" onclick={ctxUndo}>{t("ctx.undo")}<span class="sk">Ctrl+Z</span></div>
      <div class="msep"></div>
      <div class="cmi" onclick={ctxCut}>{t("ctx.cut")}<span class="sk">Ctrl+X</span></div>
      <div class="cmi" onclick={ctxCopy}>{t("ctx.copy")}<span class="sk">Ctrl+C</span></div>
      <div class="cmi" onclick={ctxPaste}>{t("ctx.paste")}<span class="sk">Ctrl+V</span></div>
      <div class="cmi" onclick={ctxDelete}>{t("ctx.delete")}<span class="sk">Del</span></div>
      <div class="msep"></div>
      <div class="cmi" onclick={ctxSelectAll}>{t("ctx.select_all")}<span class="sk">Ctrl+A</span></div>
      <div class="msep"></div>
      <div class="cmi" onclick={() => ctxSetDir("ltr")}>{t("ctx.ltr")}</div>
      <div class="cmi" onclick={() => ctxSetDir("rtl")}>{t("ctx.rtl")}</div>
      <div class="msep"></div>
      <div class="msw">
        <div class="cmi cst">{t("ctx.line_spacing")}<span class="ar">▶</span></div>
        <div class="csub">
          {#each [1.0, 1.5, 2.0, 2.5, 3.0] as ls}
            <div class="cmi" onclick={() => ctxSetLineSp(ls)}>{ls.toFixed(1)}</div>
          {/each}
        </div>
      </div>
      <div class="msep"></div>
      <div class="msw">
        <div class="cmi cst" class:cmi-disabled={!hasSel}>
          {t("ctx.case_convert")}{#if hasSel}<span class="ar">▶</span>{/if}
        </div>
        {#if hasSel}
          <div class="csub">
            <div class="cmi" onclick={ctxUpper}>{t("ctx.upper_case")}<span class="sk">Ctrl+U</span></div>
            <div class="cmi" onclick={ctxLower}>{t("ctx.lower_case")}<span class="sk">Ctrl+L</span></div>
            <div class="cmi" onclick={ctxTitle}>{t("ctx.title_case")}<span class="sk">Ctrl+T</span></div>
          </div>
        {/if}
      </div>
      <div class="msw">
        <div class="cmi cst" class:cmi-disabled={!hasSel}>
          {t("ctx.normalize")}{#if hasSel}<span class="ar">▶</span>{/if}
        </div>
        {#if hasSel}
          <div class="csub">
            <div class="cmi" onclick={() => applyNormalize("NFD")}>{t("ctx.nfd")}</div>
            <div class="cmi" onclick={() => applyNormalize("NFC")}>{t("ctx.nfc")}</div>
            <div class="cmi" onclick={() => applyNormalize("NFKD")}>{t("ctx.nfkd")}</div>
            <div class="cmi" onclick={() => applyNormalize("NFKC")}>{t("ctx.nfkc")}</div>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .ctx-mask {
    position: fixed;
    inset: 0;
    z-index: 600;
  }
  .ctx-menu {
    position: fixed;
    min-width: 220px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
    padding: 6px;
    z-index: 601;
  }
  .cmi {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 12px;
    color: var(--fg);
    font-size: 12px;
    cursor: pointer;
    border-radius: 8px;
    white-space: nowrap;
  }
  .cmi.cmi-disabled {
    opacity: 0.4;
    cursor: default;
  }
  .cmi.cmi-disabled:hover {
    background: transparent;
    color: var(--fg);
  }
  .cmi.cmi-disabled:hover .ar,
  .cmi.cmi-disabled:hover .sk {
    color: var(--fg3);
  }
  .cmi:hover {
    background: var(--ac);
    color: #fff;
  }
  .cmi:hover .sk,
  .cmi:hover .ar {
    color: rgba(255, 255, 255, 0.7);
  }
  .cst {
    display: flex;
    justify-content: space-between;
  }
  .sk {
    color: var(--fg3);
    font-size: 10px;
    margin-left: 20px;
  }
  .ar {
    font-size: 10px;
    margin-left: 8px;
    color: var(--fg3);
  }
  .msep {
    height: 1px;
    background: var(--bd);
    margin: 4px 8px;
  }
  .csub {
    display: none;
    position: absolute;
    left: 100%;
    top: -6px;
    min-width: 200px;
    background: var(--bg2);
    border: 1px solid var(--bd);
    border-radius: 12px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
    padding: 6px;
    z-index: 602;
  }
  .msw:hover > .csub {
    display: block;
  }
  .msw::after {
    content: "";
    position: absolute;
    left: 100%;
    top: 0;
    width: 8px;
    height: 100%;
  }
  .msw {
    position: relative;
  }
</style>
