<script lang="ts">
  import Icon from "../icons/Icon.svelte";
  import { localizedMenus, type MenuItem } from "../i18n.svelte";
  import { settings } from "../settings.svelte";
  import LangSwitcher from "./LangSwitcher.svelte";

  type MI = MenuItem;

  interface Props {
    dark: boolean;
    showLang: boolean;
    onMenuAction: (label: string) => void;
    onDarkToggle: () => void;
    onToggleLang: () => void;
    onCloseLang: () => void;
  }

  let {
    dark,
    showLang,
    onMenuAction,
    onDarkToggle,
    onToggleLang,
    onCloseLang,
  }: Props = $props();

  // The menu mirrors the persisted settings (mode, toggles, sizes, quality,
  // and the edit-buffer state).  Reading the properties here inside `$derived`
  // keeps the checkmarks live.
  let _menus = $derived(localizedMenus(settings));
  let om = $state(-1);

  function mc(i: number) {
    om = om === i ? -1 : i;
  }
  function ma(item: MI) {
    if (item.disabled) return;
    om = -1;
    onMenuAction(item.l);
  }

  function onWindowClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (!t.closest(".mw")) om = -1;
    if (!t.closest(".lang-wrap")) onCloseLang();
  }
</script>

<svelte:window onclick={onWindowClick} />

<nav class="mb">
  {#each _menus as m, i}
    <div class="mw">
      <button class="mbtn" class:on={om === i} onclick={() => mc(i)}
        >{m.label}</button
      >
      {#if om === i}
        <div class="mdrop" role="menu">
          {#each m.items as it}
            {#if it.sep}
              <div class="msep"></div>
            {:else if it.sub}
              <div class="msw">
                <div class="mi mst" class:disabled={it.disabled}>
                  {it.l}<span class="ar"
                    ><Icon name="chevron-right" size={10} /></span
                  >
                </div>
                <div class="msub">
                  {#each it.sub as s}
                    {#if s.sep}
                      <div class="msep"></div>
                    {:else}
                      <div
                        class="mi"
                        class:disabled={s.disabled}
                        role="menuitem"
                        aria-disabled={s.disabled ? "true" : undefined}
                        onclick={() => ma(s)}
                        onkeydown={(e) => e.key === "Enter" && ma(s)}
                        tabindex={s.disabled ? -1 : 0}
                      >
                        {s.l}<span class="sk" class:checked={s.checked}>
                          {#if s.checked}<Icon
                              name="check"
                              size={11}
                            />{:else}{s.k || ""}{/if}
                        </span>
                      </div>
                    {/if}
                  {/each}
                </div>
              </div>
            {:else}
              <div
                class="mi"
                class:disabled={it.disabled}
                role="menuitem"
                aria-disabled={it.disabled ? "true" : undefined}
                onclick={() => ma(it)}
                onkeydown={(e) => e.key === "Enter" && ma(it)}
                tabindex={it.disabled ? -1 : 0}
              >
                {it.l}<span class="sk" class:checked={it.checked}>
                  {#if it.checked}<Icon name="check" size={11} />{:else}{it.k ||
                      ""}{/if}
                </span>
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  {/each}
  <span class="msp"></span>
  <LangSwitcher {showLang} {onToggleLang} {onCloseLang} />
  <button class="tbtn" onclick={onDarkToggle}
    ><Icon name={dark ? "sun" : "moon"} size={16} /></button
  >
</nav>

<style>
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
    cursor: pointer;
    font-family: inherit;
    border: none;
    transition: all 0.15s;
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
  /* Unavailable entries stay visible (so the menu shape never jumps) but are
     greyed out and inert — matches the original's Enable(FALSE) items. */
  .mi.disabled {
    opacity: 0.38;
    cursor: default;
  }
  .mi.disabled:hover {
    background: transparent;
    color: var(--fg);
  }
  .mi.disabled:hover .sk {
    color: var(--fg3);
  }
  .sk {
    color: var(--fg3);
    font-size: 10px;
    margin-left: 20px;
  }
  .sk.checked {
    color: var(--fg);
  }
  .mi:hover .sk {
    color: rgba(255, 255, 255, 0.6);
  }
  .mi:hover .sk.checked {
    color: #fff;
  }
  .msep {
    height: 1px;
    background: var(--bd);
    margin: 4px 8px;
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
    cursor: pointer;
    font-family: inherit;
    border: none;
    transition: all 0.15s;
  }
  .tbtn:hover {
    background: var(--bg3);
  }
</style>
