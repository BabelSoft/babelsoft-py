<script lang="ts">
  import { get } from "svelte/store";
  import "./app.css";
  import MenuBar from "./lib/components/MenuBar.svelte";
  import PlaneTabs from "./lib/components/PlaneTabs.svelte";
  import CharacterGrid from "./lib/components/CharacterGrid.svelte";
  import GridNav from "./lib/components/GridNav.svelte";
  import BottomPanel from "./lib/components/BottomPanel.svelte";
  import StatusBar from "./lib/components/StatusBar.svelte";
  import FontToolbar from "./lib/components/FontToolbar.svelte";
  import * as store from "./lib/stores";
  import type { GridPage, PlaneInfo, BlockInfo } from "./lib/types";
  import { getPlanes, getGrid, getAllBlocks } from "./lib/api";

  let gridError = $state("");
  // Native $state for reactive template data
  let gridPage = $state<GridPage | null>(null);
  let planes = $state<PlaneInfo[]>([]);
  let blocks = $state<BlockInfo[]>([]);

  async function refreshGrid() {
    store.isLoading.set(true);
    gridError = "";
    try {
      const data = await getGrid(get(store.currentPlane), get(store.scrollPosition), get(store.fontFamily), get(store.fontSize));
      gridPage = data;
      store.statusMessage.set(
        `Block: ${data.block_name} [U+${data.block_start.toString(16).toUpperCase().padStart(4, "0")}–U+${data.block_end.toString(16).toUpperCase().padStart(4, "0")}] (${data.block_count} chars)`,
      );
    } catch (e: any) {
      gridError = e.message || "Failed to load grid";
      store.statusMessage.set("Error loading character grid");
    } finally {
      store.isLoading.set(false);
    }
  }

  async function initialLoad() {
    try {
      const [planeList, blockList] = await Promise.all([getPlanes(), getAllBlocks()]);
      planes = planeList;
      blocks = blockList;
      store.planes.set(planeList); // keep store in sync for sub-components
      store.blocks.set(blockList);
    } catch (e) {
      console.error("Failed to load initial data:", e);
    }
    await refreshGrid();
  }

  // Startup
  queueMicrotask(() => initialLoad());

  /** Called by PlaneTabs and FontToolbar when plane/font changes */
  function onSettingsChange() {
    refreshGrid();
  }
</script>

<div class="babelmap-container">
  <!-- Menu Bar -->
  <MenuBar onRefocus={() => refreshGrid()} />

  <!-- Main Content Area -->
  <div class="main-content">
    <!-- Upper Section: Tabs + Grid + Navigation -->
    <div class="upper-section">
      <!-- Plane Tabs row -->
      <PlaneTabs onPlaneChange={onSettingsChange} />

      <!-- Font Toolbar -->
      <FontToolbar onRefresh={onSettingsChange} />

      <!-- Grid Area with side navigation -->
      <div class="grid-area">
        <div class="grid-container">
          {#if get(store.isLoading)}
            <div class="loading-overlay">Loading...</div>
          {/if}
          {#if gridError}
            <div class="error-overlay">
              <p>{gridError}</p>
              <button onclick={() => refreshGrid()}>Retry</button>
            </div>
          {/if}
          <CharacterGrid {gridPage} onRefresh={() => refreshGrid()} />
        </div>
        <GridNav onRefresh={() => refreshGrid()} />
      </div>
    </div>

    <!-- Lower Section: Search / GoTo / Font / Edit Buffer -->
    <BottomPanel onRefresh={() => refreshGrid()} />
  </div>

  <!-- Status Bar -->
  <StatusBar />
</div>

<style>
  .babelmap-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .main-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }

  .upper-section {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
    border-bottom: 2px solid var(--border-color);
  }

  .grid-area {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .grid-container {
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  .loading-overlay,
  .error-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(30, 30, 46, 0.85);
    z-index: 10;
    gap: 12px;
  }
  .error-overlay {
    color: var(--danger);
  }
</style>
