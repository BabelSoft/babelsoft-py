<script lang="ts">
  import { t, lang, langList, type LangDef } from "../i18n.svelte";

  interface Props {
    showLang: boolean;
    onToggleLang: () => void;
    onCloseLang: () => void;
  }

  let { showLang, onToggleLang, onCloseLang }: Props = $props();
</script>

<div class="lang-wrap">
  <button class="lang-btn" onclick={onToggleLang} title={t("lang.title")}>
    {langList.find((l: LangDef) => l.code === lang.v)?.nativeName || "English"}
  </button>
  {#if showLang}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="lang-drop" onkeydown={(e) => e.key === "Escape" && onCloseLang()}>
      {#each langList as l}
        <div
          class="lang-item"
          class:active={lang.v === l.code}
          onclick={() => {
            lang.v = l.code;
            onCloseLang();
          }}
          onkeydown={(e) => e.key === "Enter" && ((lang.v = l.code), onCloseLang())}
          role="menuitem"
          tabindex="0"
        >
          {l.nativeName}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
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
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
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
</style>
