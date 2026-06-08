<script lang="ts">
  import { get } from "svelte/store";
  import * as store from "../stores";
  import { jumpToBlock, jumpToCodepoint, navigateDirection, getGrid } from "../api";
  import type { BlockInfo } from "../types";

  interface Props {
    onRefocus?: () => void;
  }

  let { onRefocus = () => {} }: Props = $props();

  let showGoto = $state(false);
  let gotoValue = $state("");
  let selectedBlock = $state("");

  const menuItems = [
    {
      label: "File",
      items: ["Save Edit Buffer"],
    },
    {
      label: "Edit",
      items: ["Copy Glyph", "Copy Glyph Outline", "Copy as Plain Text", "Copy as RTF", "Cut Plain", "Cut RTF", "Paste", "Clear Edit Buffer"],
    },
    {
      label: "Find",
      items: ["Find Previous", "Find Next", "Find IRG Source", "Go to...\tCtrl+G"],
    },
    {
      label: "Tools",
      items: [
        "Character Search",
        "Han Ideograph Search",
        "Mandarin Lookup",
        "Cantonese Lookup",
        "Zhuang Lookup",
        "Han Radical Lookup",
        "Yi Radical Lookup",
        "Tangut References",
        "Emoji Data",
        "UCD Properties",
        "XML Properties",
        "History",
        "Fonts Overview",
        "Font Analysis",
        "Font Info",
        "Font Coverage",
        "Export Glyphs",
        "UVS Lookup",
      ],
    },
    {
      label: "Fonts",
      items: ["Add Fonts...", "Remove Fonts..."],
    },
    {
      label: "Options",
      items: [
        "Composite Font Configuration...",
        "Search Aliases",
        "Diacritics",
        "CJK Upper Case Readings",
        "Tone Numbers",
        "Tangut Tone Numbers",
        "Copy on Select",
        "Show Algorithmic Names",
        "Show CJK References",
        "Show Tangut References",
        "Convert Basic Latin",
        "Rotate Vertical Scripts",
        "Colour Coding",
        "Customize Colours...",
        "Font Configuration...",
        "Reset All Settings",
      ],
    },
    {
      label: "Bookmarks",
      items: ["Add Bookmark", "Manage Bookmarks...", "Delete Bookmark", "Delete All Bookmarks"],
    },
    {
      label: "View",
      items: ["Edit Buffer", "Size: Large", "Size: Medium", "Size: Small", "Stay on Top", "Show Reserved Planes", "Show Reserved Ranges"],
    },
    {
      label: "Help",
      items: ["BabelMap Help", "About BabelMap..."],
    },
  ];

  let openMenu = $state<number | null>(null);
  let activeSubItem = $state<number | null>(null);

  function handleMenuClick(idx: number) {
    openMenu = openMenu === idx ? null : idx;
    activeSubItem = null;
  }

  function handleSubItemClick(menuLabel: string, itemLabel: string) {
    openMenu = null;

    // Handle specific menu actions
    switch (itemLabel) {
      case "Go to...\tCtrl+G":
        showGoto = true;
        break;
      case "Copy Glyph":
      case "Copy Glyph Outline":
      case "Copy as Plain Text":
        store.statusMessage.set(`${itemLabel} - not yet implemented`);
        break;
      case "Clear Edit Buffer":
        store.editBuffer.set("");
        store.statusMessage.set("Edit buffer cleared");
        break;
      case "Save Edit Buffer":
        store.statusMessage.set("Save - not yet implemented");
        break;
      case "Composite Font Configuration...":
        store.statusMessage.set("Font config dialog - not yet implemented");
        break;
      default:
        store.statusMessage.set(`${itemLabel} - not yet implemented`);
    }
  }

  async function handleGotoSubmit(e: Event) {
    e.preventDefault();
    showGoto = false;
    if (!gotoValue) return;
    let cp: number;
    const v = gotoValue.trim();
    if (v.startsWith("0x") || v.startsWith("0X") || v.startsWith("U+") || v.startsWith("u+")) {
      cp = parseInt(v.replace(/^(0x|0X|U\+|u\+)/, ""), 16);
    } else if (v.startsWith("$")) {
      cp = parseInt(v.slice(1), 16);
    } else if (v.startsWith("#")) {
      cp = parseInt(v.slice(1), 10);
    } else if (/^[0-9A-Fa-f]+$/.test(v)) {
      cp = parseInt(v, 16);
    } else {
      cp = parseInt(v, 10);
    }
    if (isNaN(cp)) return;
    try {
      const page = await jumpToCodepoint(get(store.currentPlane), cp);
      store.gridPage.set(page);
      store.scrollPosition.set(page.scroll_position);
    } catch (e: any) {
      store.statusMessage.set(`Go to failed: ${e.message}`);
    }
  }

  async function handleBlockSelect() {
    if (!selectedBlock) return;
    try {
      const page = await jumpToBlock(get(store.currentPlane), selectedBlock);
      store.gridPage.set(page);
      store.scrollPosition.set(page.scroll_position);
      onRefocus?.();
    } catch (e: any) {
      store.statusMessage.set(`Block jump failed: ${e.message}`);
    }
  }
</script>

<nav class="menubar">
  {#each menuItems as menu, idx}
    <div class="menu-item-wrapper">
      <button class="menu-trigger" class:active={openMenu === idx} onclick={() => handleMenuClick(idx)}>
        {menu.label}
      </button>
      {#if openMenu === idx}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="menu-dropdown"
          onkeydown={(e) => {
            if (e.key === "Escape") openMenu = null;
          }}
        >
          {#each menu.items as item, jdx}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div class="menu-item" class:active={activeSubItem === jdx} onclick={() => handleSubItemClick(menu.label, item)} onmouseenter={() => (activeSubItem = jdx)}>
              {item}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/each}
</nav>

<!-- GoTo Popup -->
{#if showGoto}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="goto-overlay"
    onclick={() => (showGoto = false)}
    onkeydown={(e) => {
      if (e.key === "Escape") showGoto = false;
    }}
  >
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <form class="goto-form" onkeydown={(e) => e.stopPropagation()} onsubmit={handleGotoSubmit}>
      <label for="goto-input">Go to Codepoint:</label>
      <input id="goto-input" type="text" placeholder="e.g. U+4E2D or 0x4E2D" bind:value={gotoValue} />
      <div class="goto-actions">
        <button type="submit">Go</button>
        <button type="button" onclick={() => (showGoto = false)}>Cancel</button>
      </div>
    </form>
  </div>
{/if}

<style>
  .menubar {
    display: flex;
    align-items: center;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: 0 4px;
    height: 28px;
    flex-shrink: 0;
    z-index: 100;
  }

  .menu-item-wrapper {
    position: relative;
  }

  .menu-trigger {
    border: none;
    background: transparent;
    color: var(--text-primary);
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 12px;
  }
  .menu-trigger:hover,
  .menu-trigger.active {
    background: var(--bg-tertiary);
  }

  .menu-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 220px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    z-index: 200;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    padding: 4px 0;
  }

  .menu-item {
    padding: 5px 16px;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
  }
  .menu-item:hover,
  .menu-item.active {
    background: var(--accent);
  }

  /* GoTo overlay */
  .goto-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 500;
  }
  .goto-form {
    background: var(--bg-secondary);
    padding: 24px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 320px;
  }
  .goto-form label {
    font-size: 14px;
    color: var(--text-primary);
  }
  .goto-form input {
    font-size: 16px;
    padding: 8px 12px;
    font-family: var(--font-mono);
  }
  .goto-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
</style>
