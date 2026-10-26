<script lang="ts">
  // Lightweight inline-SVG icon system (24×24 viewBox, stroke-based,
  // currentColor). No external dependency — add new icons to ICONS below.
  const ICONS: Record<string, string> = {
    // transport / navigation
    "skip-start": '<path d="M5 6v12"/><path d="M19 6l-10 6 10 6z"/>',
    "skip-end": '<path d="M19 6v12"/><path d="M5 6l10 6-10 6z"/>',
    rewind: '<path d="M18 6l-7 6 7 6z"/><path d="M11 6l-7 6 7 6z"/>',
    "fast-forward": '<path d="M6 6l7 6-7 6z"/><path d="M13 6l7 6-7 6z"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="M19 12l-7 7-7-7"/>',
    "row-start":
      '<path d="M5 4h14"/><path d="M12 21V8"/><path d="M7 13l5-5 5 5"/>',
    "row-end":
      '<path d="M5 20h14"/><path d="M12 3v13"/><path d="M7 11l5 5 5-5"/>',
    wavy: '<path d="M3 12c2-2.5 4-2.5 6 0s4 2.5 6 0 4-2.5 6 0"/>',
    dice: '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8.5" cy="8.5" r="1.4" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/><circle cx="15.5" cy="15.5" r="1.4" fill="currentColor" stroke="none"/>',

    // theme
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',

    // directional chevrons / arrows
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "chevron-left": '<path d="m15 6-6 6 6 6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-up": '<path d="m6 15 6-6 6 6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',

    // actions
    check: '<path d="M20 6 9 17l-5-5"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    trash:
      '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/>',
  };

  let {
    name,
    size = 16,
    title,
  }: { name: string; size?: number; title?: string } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden={title ? undefined : "true"}
  role={title ? "img" : undefined}
  style="display:inline-block; vertical-align:middle; flex:none;"
>
  {#if title}<title>{title}</title>{/if}
  {@html ICONS[name] ?? ""}
</svg>
