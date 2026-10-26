# BabelMap --- Cross-Platform Unicode Character Map

Modern rebuild of the BabelSoft BabelMap tool using:

| Layer    | Technology                       | Purpose                       |
| -------- | -------------------------------- | ----------------------------- |
| Shell    | Tauri 2 (Rust)                   | Native window, lifecycle      |
| Frontend | Svelte 5 + TypeScript            | UI components                 |
| Backend  | Python FastAPI                   | Unicode data, glyph rendering |
| Data     | `babellib/babelsoft/` (existing) | CJK, Unicode, Mappings, etc.  |

> This document inventories every feature currently exposed by the `babelmap/`
> frontend + backend, and marks whether it is actually implemented (✅), only
> partially wired (⚠️), or a menu placeholder with no backend/UI (🚫).

---

## Implementation Status

| Area                        | Status                                                                                                                                                                                                                                |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend REST/SSE API        | ✅ Core complete                                                                                                                                                                                                                      |
| Character grid & navigation | ✅ Complete                                                                                                                                                                                                                           |
| Expression search engine    | ✅ Complete (AST parser + SSE streaming)                                                                                                                                                                                              |
| Edit buffer (modes, RTF)    | ✅ Complete                                                                                                                                                                                                                           |
| Save dialog (encodings/BOM) | ✅ Complete                                                                                                                                                                                                                           |
| Context menu (text editing) | ✅ Complete                                                                                                                                                                                                                           |
| Menu bar                    | ✅ Structure complete; every menu group (Fonts, Options, Bookmarks, Help) is fully wired                                                                                                                                              |
| Plane tabs                  | ✅ Complete (7 fixed / 17 unfiltered)                                                                                                                                                                                                 |
| Block selector              | ✅ Complete                                                                                                                                                                                                                           |
| Localization                | ✅ 7 languages                                                                                                                                                                                                                        |
| Fonts toolbar               | ✅ Overview / Composite Mappings / Quality / Export Glyphs wired; size via menu presets or Ctrl+wheel                                                                                                                                 |
| Tools menu dialogs          | ✅ Unicode / Char Properties (+Extended/Ideographic/History/IVS) / Emoji Lookup / OpenType Test / 5 lookup dialogs (Pinyin, Jyutping, Zhuang, Han radical, Yi radical)                                                                |
| Fonts Overview dialog       | ✅ Complete (families, scripts, coverage/analysis/info, axes, SSE, My fonts add/remove)                                                                                                                                               |
| Composite Font Mappings     | ✅ Complete (block coverage + Auto, entry appends with axes, generated read-only CSS)                                                                                                                                                 |
| Fonts menu (all 4 groups)   | ✅ Single/Composite mode, all-styles + legacy enumeration, symbol mappings, 5 size presets, 7 quality modes, Quality & Export dialogs — all persisted                                                                                 |
| Options menu                | ✅ All 15 entries wired: block order, aliases, goto base, alt representation, CJKV/Tangut readings, grid gestures, magnifier, 8 colour-coding modes, cut/copy defaults, 3 status-bar toggles, vertical rotation, colour editor, reset |
| Bookmarks                   | ✅ 4 commands + one dynamic menu entry per bookmark (max 32), manage dialog, persisted                                                                                                                                                |
| Help / About                | ✅ One window (F1): a version block from `/api/about` plus a shortcut reference generated from the menu bar                                                                                                                           |
| File menu                   | ✅ Close to System Tray + Exit, both forwarded to the Tauri window |
| Supplementary Information   | ✅ The original's CJKV / Tangut / hieroglyph dialogs are the **Supplementary** tab of Character Properties |
| UCD data generation         | ✅ Core UCD table (`/api/ucd/generate`) + full XML download (`/api/ucd/xml`) |
| Grid size (View/font)       | ✅ 5 menu presets × the two View size columns (`GridPointSize[][2]`) + Ctrl+wheel zoom, persisted                                                                                                                                     |
| Glyph rasteriser (FreeType) | ✅ `/api/glyphs/*` — 7 selectable quality modes; grid uses the system renderer                                                                                                                                                        |

---

## Backend API --- `backend/server.py`

All endpoints implemented and working. Port **18080** (`http://127.0.0.1:18080`).

| Endpoint                                                                       | Description                                                            | Status |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------- | ------ |
| `GET /api/health`                                                              | Health check                                                           | ✅     |
| `GET /api/about`                                                               | Version block for Help ▸ About                                         | ✅     |
| `GET /api/planes`                                                              | List Unicode planes (0–16)                                             | ✅     |
| `GET /api/blocks`                                                              | All blocks (valid planes, no surrogates)                               | ✅     |
| `GET /api/blocks/{plane}`                                                      | Blocks for a plane                                                     | ✅     |
| `GET /api/grid/{plane}?scroll=&filter_no_block=`                               | Character grid page (8×16)                                             | ✅     |
| `GET /api/grid/{plane}/goto/{cp}`                                              | Jump to codepoint (+`filter_no_block`)                                 | ✅     |
| `GET /api/grid/{plane}/block/{name}`                                           | Jump to a block by name                                                | ✅     |
| `GET /api/grid/{plane}/navigate`                                               | Grid navigation (page/block/plane)                                     | ✅     |
| `GET /api/codepoint/{cp}`                                                      | Codepoint info (GC, script, pinyin...)                                 | ✅     |
| `GET /api/lookup?kind=&q=`                                                     | Reverse lookups: pinyin / jyutping / zhuang / han_radical / yi_radical | ✅     |
| `GET /api/supplementary/{cp}` | CJKV / Tangut / hieroglyph section list for Tools ▸ Supplementary Information | ✅ |
| `GET /api/ucd/fields` | The 15 `Unicode::UCDFields` column titles | ✅ |
| `GET /api/ucd/generate?start=&end=` | UCD table rows for a range (CJK/Hangul runs abbreviated to First/Last) | ✅ |
| `GET /api/ucd/xml?start=&end=` | `ucd.nounihan.flat`-style XML for a range | ✅ |
| `GET /api/glyph/{cp}?font=&size=`                                              | Glyph PNG as base64 (Pillow)                                           | ✅     |
| `GET /api/search/name?q=`                                                      | Unified expression search                                              | ✅     |
| `GET /api/search/advanced?q=`                                                  | Alias of `/search/name`                                                | ✅     |
| `GET /api/search/name/stream`                                                  | SSE streaming search                                                   | ✅     |
| `GET /api/search/han_source`                                                   | CJK IRG source-reference search                                        | ✅     |
| `GET /api/search/properties`                                                   | Property autocomplete list                                             | ✅     |
| `GET /api/emoji/search?q=`                                                     | Emoji search by name/keyword/codepoint                                 | ✅     |
| `GET /api/emoji/list`                                                          | All RGI emoji in CLDR order (browse)                                   | ✅     |
| `GET /api/fonts`                                                               | List font names                                                        | ✅     |
| `GET /api/fonts/overview?dirs=`                                                | Full font scan (families, scripts, cov.)                               | ✅     |
| `GET /api/fonts/overview/stream?dirs=`                                         | SSE scan progress, then the full payload                               | ✅     |
| `GET /api/fonts/raw?path=`                                                     | Serve a font file (for `@font-face`)                                   | ✅     |
| `GET /api/fonts/user`                                                          | List user-added (uploaded) fonts                                       | ✅     |
| `POST /api/fonts/user`                                                         | Register an uploaded font                                              | ✅     |
| `POST /api/fonts/user/remove`                                                  | Unregister + delete a user font                                        | ✅     |
| `GET /api/fonts/user_file?id=`                                                 | Serve a user font (for `@font-face`)                                   | ✅     |
| `GET /api/fonts/user/analyze?id=`                                              | fontTools analysis of a user font                                      | ✅     |
| `POST /api/fonts/composite/validate`                                           | Compile-validate composite-font CSS                                    | ✅     |
| `GET /api/fonts/coverage?block=&dirs=&all_styles=`                             | Per-block font coverage (+Auto winner)                                 | ✅     |
| `GET /api/fonts/coverage/stream?block=&dirs=&all_styles=`                      | SSE scan progress, then the coverage table                             | ✅     |
| `GET /api/fonts/coverage/auto?dirs=&all_styles=`                               | Auto: best font for every block                                        | ✅     |
| `GET /api/fonts/coverage/chars?block=&dirs=&all_styles=`                       | Full character list of one block, per-font support                     | ✅     |
| `GET /api/glyphs/qualities`                                                    | The seven `lfQuality` modes                                            | ✅     |
| `GET /api/glyphs/preview?cp=&font=&size=&quality=&cell_w=&cell_h=&scale=&fmt=` | One glyph, rasterised at that quality, as an image                     | ✅     |
| `GET /api/glyphs/sample?text=&font=&size=&quality=&scale=`                     | A sample line at that quality (Font Quality dialog)                    | ✅     |
| `POST /api/glyphs/export`                                                      | Zip of one image per code point                                        | ✅     |
| `GET /api/convert/edit?text=&mode=`                                            | NCR/HTML/UCN conversion helpers                                        | ✅     |
| `GET /api/unicode/versions`                                                    | Unicode version history + block lists                                  | ✅     |
| `GET /api/unicode/scripts`                                                     | Script summary (code, name, chars)                                     | ✅     |
| `GET /api/unicode/scripts/blocks?code=`                                        | Per-block breakdown for one script                                     | ✅     |
| `GET /api/unicode/planes`                                                      | Per-plane stats (blocks/chars/unassigned)                              | ✅     |
| `GET /api/unicode/planes/{plane}/blocks`                                       | Blocks contained in one plane                                          | ✅     |
| `GET /api/unicode/blocks?version=`                                             | Block table for a Unicode version                                      | ✅     |
| `GET /api/unicode/blocks/{name}/characters`                                    | Assigned characters inside one block                                   | ✅     |
| `GET /api/unicode/blocks/{name}/unicodedata`                                   | UnicodeData rows for one block                                         | ✅     |
| `GET /api/unicode/diff?from=&to=`                                              | Block/character changes between versions                               | ✅     |
| `GET /api/unicode/history`                                                     | Per-version character history                                          | ✅     |

### OpenType Test Framework endpoints

| Endpoint                        | Description                                       | Status |
| ------------------------------- | ------------------------------------------------- | ------ |
| `GET /api/opentype/fonts`       | System font list for the dialog                   | ✅     |
| `POST /api/opentype/font_faces` | Faces inside a TTC/OTC/WOFF container             | ✅     |
| `GET /api/opentype/meta`        | ISO 15924 scripts + OpenType language tags        | ✅     |
| `POST /api/opentype/shape`      | Shape text with a chosen engine, full trace + SVG | ✅     |
| `POST /api/opentype/render`     | Render an arbitrary glyph run as SVG              | ✅     |

---

## Platform support — OpenType shaping engines

`POST /api/opentype/shape` (the OpenType Test Framework dialog) can shape with
several engines. Most are **cross-platform** — HarfBuzz (`harfbuzz`),
HarfRust (`harfrust`), BabelScript (`babelscript`), Graphite (`graphite`),
Yudit (`yudit`), ICU (`icu`), FreeType (`freetype`) and HarfBuzz fallback
(`harfbuzz_fallback`).

`yudit` runs the shaping engine of the **Yudit** Unicode editor through the
`pyyudit` package; it derives script/direction from the text itself, so the
dialog's direction / script / language / feature options do not apply. What the
trace shows depends on the script, because the engine reports whatever Yudit's
pipeline emits: for **Arabic / Syriac / Latin** it is a real OpenType trace
(`input` → `split` → `join` → `gindex` → `rlig`/`calt`/`liga`/`kern`/`mark`/
`mkmk` with per-lookup rows → `reorder` → `shaped`) and **Arabic joining + RTL
ordering match HarfBuzz glyph-for-glyph**; for **Indic** it is Yudit's own
pipeline (`nukt`/`akhn`/`rphf`/`blwf`/`half`/`vatu`/`pres`/`abvs`/`blws`/`psts`/
`haln` → `clean` → `abvm`/`blwm`/`dist`/`gpos_final` → `shaped`), whose
substitutions require the font to carry the **first-version** script tag
(`deva`/`beng`/`taml`/…). A font that only registers the second-version tags
(`dev2`/`bng2`/`tml2`/… — Nirmala UI registers those plus `sinh`) matches no
feature for those scripts, so the glyphs come back unchanged and the trace shows
**0 `start lookup` rows** — correct behaviour, not an engine failure. Applying
the `…2` features is deliberately not done (their feature order differs, so it
would yield _wrong_ glyphs, not merely different ones). With a `deva` font such
as NotoSansDevanagari, Yudit shapes `नमस्ते` glyph-for-glyph like HarfBuzz. Note
that HarfBuzz reaches Indic through `dev2` while Yudit uses `deva`, so a
`dev2`-only font is not a meaningful Indic A/B against HarfBuzz.

Positions are trustworthy since 0.3.0 — `dx` is a real x offset again and
Latin/Arabic runs match HarfBuzz glyph-for-glyph, rendered x positions included.
Rows before Yudit's cmap step (`input`/`split`/`join`/`decompose`, and the Indic
`reorder`) hold codepoints rather than glyph ids; they are flagged `cps` (the same
idea as Crowbar's `glyphs: false`) so the dialog labels them `U+XXXX` instead of a
glyph name — Arabic `join` usefully shows the presentation-form codepoints Yudit
picked, e.g. `U+FEE3`.

`pyyudit` ships per-platform wheels (`win_amd64` / `manylinux` / `macosx`) with
the matching native library bundled in `pyyudit/_lib/`; a `py3-none-any` install
(no bundled library) makes the engine raise a `LibraryNotFound` hint, and the
native library can be built with CMake from
[github.com/Kushim-Jiang/pyyudit](https://github.com/Kushim-Jiang/pyyudit).
The loader accepts single-face fonts only — TTC/OTC input is flattened by the
font-source layer before it reaches the engine (in `raw` delivery mode the
collection is handed over as-is and the engine rejects it with a clear
`FontError`).

The two Windows shaping APIs are provided by the `pyusp` and `pydwshape`
packages, each in a **native** and a **Wine** flavour:

| Engine             | Backend                          | Notes                                                                                                                                                                                                                 |
| ------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uniscribe`        | `pyusp` backend `usp10`          | Native Microsoft Uniscribe, **Windows-only**, single whole-run stage (no per-lookup callback). Drives the system `usp10.dll` (the published wheel bundles only `wineusp.dll`; a dev wheel may pin an app-local copy). |
| `uniscribe_wine`   | `pyusp` backend `wineusp`        | Wine's open-source Uniscribe (LGPL), **cross-platform**; `trace=True` returns a real cmap → per-GSUB-lookup → final timeline.                                                                                         |
| `directwrite`      | `pydwshape` backend `dwcore`     | Native **DWriteCore**, **Windows-only**; full per-lookup trace. `pydwshape` only ships Windows wheels (marked `platform_system == 'Windows'`).                                                                        |
| `directwrite_wine` | `pydwshape` backend `winedwrite` | Wine DWrite port, **cross-platform**; full per-lookup trace. Bundled in every wheel since pydwshape 0.4.0 (`winedwrite.dll` on Windows too); `WDWRITE_LIB` overrides for manual builds.                               |

Feature selection (`features` / the dialog's feature chips + feature string) is
**Uniscribe-specific** in two ways, both from system-usp10 semantics:

- it **replaces** the run's default GSUB feature set instead of adding to it, so
  `{liga: true}` applies exactly `liga`;
- it is only honoured by the **native** engine. `uniscribe_wine` has no feature
  support at all — the Wine port's `ScriptShapeOpenType` logs
  `FIXME("Ranges not supported yet")` and drops the records, so `pyusp` raises
  (the dialog then shows `Shaping failed: features … cannot be applied by the
loaded Wine Uniscribe port …`) rather than shaping with the toggles silently
  ignored.

Before pyusp 0.6.0 every tag was packed byte-reversed, so feature toggles had no
effect on _either_ engine — if a toggle looks dead, check `pyusp.__version__`.

`pyusp` ships win/manylinux/macOS wheels, so it installs everywhere; the API
rejects the two native engines (`uniscribe`, `directwrite`) on non-Windows
with a `"… engine is Windows-only"` error (see `backend/server.py`), while the
two Wine engines run on every platform.

### Font source — containers, faces, delivery

Handling _collections_ is BabelMap's job, not the engines': `backend/font_source.py`
turns whatever the user supplied (`.ttf` / `.otf` / **`.ttc` / `.otc`** /
**`.woff` / `.woff2`**) into a single-face sfnt before the engines see it.

| Layer                      | What happens                                                                                                                                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/api/opentype/font_faces` | `POST {font_b64?\|font_path?}` → container, face count and one entry per face (`label`, family, subfamily, glyph count, `glyf`/`CFF`). Drives the dialog's face picker.       |
| `font_delivery=auto`       | **Default.** A plain sfnt is passed through untouched; a collection / WOFF / WOFF2 is flattened to the chosen face. Every engine then behaves identically.                    |
| `font_delivery=flatten`    | Always hand over a standalone single-face sfnt.                                                                                                                               |
| `font_delivery=raw`        | Hand over the original bytes **plus** `font_face` — only HarfBuzz/HarfRust honour a face index; useful to compare an engine's own collection handling against our extraction. |
| `font_face=N`              | Face index inside a collection (`0` for single-face fonts). Out of range → a 400 `Face selection failed: face N does not exist — 6 face(s) available (0-5)`.                  |

Flattening is a **byte-level sfnt slice** (table directory + tables copied
verbatim, offsets rebased, `head.checkSumAdjustment` recomputed) — never a
fontTools re-serialisation, so glyph data cannot change. The `font_source` object
in the shape response reports `container`, `requested_face`, `delivery`,
`flattened` and the byte sizes, and the dialog shows it under the Face picker.
Metadata, glyph names and SVG outlines always come from the flattened face
(fontTools needs a single face), even in `raw` mode.

`babelmap/backend/shape_compare.py --face N` uses the same layer, so the CLI also
accepts collections/WOFF.

---

## Frontend Components --- `frontend/src/lib/components/`

| Component                          | Purpose                                                  | Status       |
| ---------------------------------- | -------------------------------------------------------- | ------------ |
| `App.svelte`                       | Root layout, state, menu actions, search glue            | ✅           |
| `MenuBar.svelte`                   | Dropdown menus, submenus, ✓ states, theme                | ⚠️ see below |
| `PlaneTabs.svelte`                 | Plane tab bar                                            | ✅           |
| `CharacterGrid.svelte`             | 16-col grid, reserved/nonchar/highlight                  | ✅           |
| `GridHeader.svelte`                | Block title + column headers                             | ✅           |
| `NavPanel.svelte`                  | Vertical slider + nav buttons (IVS opens Character Properties) | ✅           |
| `BottomPanel.svelte`               | Block selector, AdvSearch, goto, edit buffer             | ✅           |
| `AdvSearch.svelte`                 | Expression input + property autocomplete                 | ✅           |
| `SearchResultsWindow.svelte`       | Draggable/resizable results window                       | ✅           |
| `InfoBar.svelte`                   | U+XXXX char name + decimal                               | ✅           |
| `StatusBar.svelte`                 | Status messages, plane/font/row info                     | ✅           |
| `SaveDialog.svelte`                | Save with encoding/BOM/newline                           | ✅           |
| `ContextMenu.svelte`               | Textarea edit menu (undo/case/normalize...)              | ✅           |
| `LangSwitcher.svelte`              | Language picker                                          | ✅           |
| `UnicodeDialog.svelte`             | Version / Planes / Blocks / Scripts browser              | ✅           |
| `CharacterPropertiesDialog.svelte` | Unicode properties + History tab                         | ✅           |
| `EmojiLookupDialog.svelte`         | Emoji search, CLDR names, colored grid                   | ✅           |
| `OpenTypeTestDialog.svelte`        | Shaping engine picker, trace, SVG preview                | ✅           |
| `FontOverviewDialog.svelte`        | Font families, scripts, coverage, live preview           | ✅           |
| `CompositeFontDialog.svelte`       | Block coverage/Auto + font stack (entries / CSS / fonts) | ✅           |
| `CompositeFontDialog.svelte`       | Font stack (entries / CSS / added fonts)                 | ✅           |

---

## Fonts Overview — `FontOverviewDialog.svelte` + `backend/font_overview.py`

The **Fonts → Overview of All Fonts…** dialog (`backend/font_overview.py`)
enumerates every font face in the system + per-user font directories, groups them
by **hyper family → family → face**, and classifies each face by primary writing
system using the fonts' OpenType script/language tags and cmap coverage.

### Scanning with live progress

The scan is CPU-bound (a few hundred files), so the dialog subscribes to a
**Server-Sent Events** endpoint rather than a plain request:

1. `scan_fonts()` walks the font directories and calls a `progress` callback per
   file, which queues `{done, total, file, cached, pct}` events on a worker
   thread;
2. `GET /api/fonts/overview/stream` pumps those events onto the stream as
   `data: SCAN {…}`, then `data: RESULT {fonts, chapters}` and `data: [DONE]`;
3. the dialog renders a determinate progress bar with `done / total`, a
   percentage, the file currently being read, and a live elapsed-time readout
   (the bar falls back to indeterminate while the directories are still being
   enumerated).

The non-streaming `GET /api/fonts/overview` returns the same payload in one
shot.

### What each face exposes

| Group           | Contents                                                                                                                                   |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity        | `family`, `hyper_family`, `subfamily`, `full_name`, `ps_name`, `version`                                                                   |
| Legal / credits | `copyright`, `manufacturer`, `designer`, `designer_url`, `license`, `license_url`, `trademark` (localized name-table rows in `meta_langs`) |
| Metrics         | `weight`, `width`, `italic`, `symbol`, `fs_type`, `panose`, `upem`, `glyph_count`, `file_size`                                             |
| Variable fonts  | `variable` + `axes: [{tag, min, default, max, step}]` — the preview exposes one draggable slider per axis                                  |
| Writing systems | `main_script` / `main_label`, `tags` (each with its Core-Spec `chapter` for chip colour)                                                   |
| Coverage        | `coverage` / `coverage_pct` plus `scripts: [{tag, label, covered, total, ratio, blocks: [{name, start, end, covered, total}]}]`            |
| OpenType        | `ot_langs` (language-system tags) and `ot_features` (GSUB/GPOS feature tags, each toggled On / Off / Default in the preview)               |

### Preview

- A face's sample text defaults to its primary script (`defaultPreview`) and can
  be typed freely; `sampleChar` supplies the two-letter fallback in lists.
- OpenType features declared in the font become click-to-cycle chips; the
  preview applies them via `font-feature-settings`.
- Variable fonts are **downloaded from `/api/fonts/raw` and declared as a web
  `@font-face`** — unlike an OS-installed variable font, a web-loaded one
  interpolates smoothly, so the axis sliders (`font-weight`, `font-stretch`,
  `font-style`, `font-variation-settings`) animate properly.
- `/api/fonts/raw` only serves files inside the known font directories, so the
  endpoint cannot be used as a general file reader.

The dialog supports search, a writing-system filter, group sorting (name / face
count), expand-all / collapse-all, and a face list toggle.

### Added fonts (outside the system font folders)

The Overview toolbar also carries **Added fonts** / **+ Add font…** — this is
where fonts the user brings in from _outside_ the system font directories are
registered, and where their font analysis lives next to the installed-font
analysis. See the next section.

---

## Composite Font Mappings — `CompositeFontDialog.svelte` + `backend/font_registry.py`

The **Fonts → Composite Font Mappings…** dialog (also reachable from the bottom
panel's **Configure…** button) owns the font stack that the **character grid and
the edit buffer share**. Modern CSS makes the whole thing declarative: a font
stack _is_ a list of `@font-face` rules, resolved **front to back** — the
browser walks the stack and uses the first face whose `unicode-range` covers the
character. Appending an entry therefore means “use this as a later fallback”.

### Three things the dialog edits

| Surface     | What it is                                                                                                                                                            |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blocks**  | Per-block font coverage, in two columns: **blocks on the left**, the complete font list for the selected block on the right — plus the **Auto** best-font assignment. |
| **Entries** | Point-and-click rows built from _font + style + weight + characters/range_, appended in order.                                                                        |
| **CSS**     | Read-only view of the CSS generated from Blocks + Entries, with per-line error/warning markers from the backend validator.                                            |
| **Fonts**   | The registry of uploaded fonts (add / remove / analyze).                                                                                                              |

### Blocks — coverage and Auto (`backend/font_coverage.py`)

The **Blocks** tab is the modern port of the original `CDialogConfig`
(`Dialogs/DialogConfig.cpp`) — the block list it fills in `OnInitDialog`, the
per-block font list from `OnNewBlock`, and the **Auto** button's scoring walk
from `OnConfigButtonAuto`.

One row per Unicode block on the **left**, with the fonts covering the selected
block listed in full on the **right** (there is no colour bar and no cap — every
font that covers the block is listed, in coverage order, down to a single
character).

The left column shows, per block:

- the block's **real** character count — graphic + format only, because counting
  control characters would make a block like Basic Latin report 128 characters
  that no font can ever map (it is 95);
- the **best font** (`best_font`) — the Auto winner once Auto has run;
- the covered/total count.

The right column shows the selected block's name and range, a **preview**, and
the complete font list:

- the **preview** renders the block's **entire** character set — not a sample —
  **one character per box**, because a continuous string would let cursive /
  connected scripts like Arabic or N'Ko join the run together. Clicking a font
  in the right-hand list re-renders the grid in _that_ font, and characters it
  does not map are **greyed out** (dashed, dimmed), so a font's real coverage of
  the block is visible at a glance;
- the preview grid scrolls inside itself (a block can hold 20 000+ characters),
  and the font list below scrolls independently;
- clicking any font in the list switches the preview; its `+` button appends a
  stack entry mapping that block's range to _that_ font, so a better candidate
  than the Auto pick can be chosen by hand.

The whole dialog **never scrolls as one surface**: the two columns scroll
separately (the body uses `overflow: hidden` on this tab), so the block list and
the font list keep their own positions.

Private Use Area blocks are marked and excluded from the summary, exactly as the
original does.

The scan is **started at app launch** (`App.svelte` → `startCoverageScan()`), so
the CPU-heavy analysis overlaps with the user's first interactions instead of
blocking the dialog; its progress bar lives in the main window's status bar at
the bottom.

**Auto** assigns a font to every block. The scoring is inherited from
`OnConfigButtonAuto`, in priority order:

1. **characters covered in this block** — capped to the block total, because a
   font that maps more than the block holds is usually unreliable;
2. **weight** closest to Regular (`CFontData::IsMostRegularFont`);
3. **distinct blocks covered**;
4. **total characters covered**.

A **preferred font** (`Unicode::PreferredFontPerBlock` — the Windows font the
original assigns to that script, ported verbatim into
`PREFERRED_FONT_PER_BLOCK`) overrides the winner when it covers at least as much.

Two modern refinements, both compensating for the fact that today's scan sees
far more fonts than the original's GDI enumeration did:

- **primary style only** — one face per family (closest to Regular), which is
  what `IsPrimaryStyle()` actually means; otherwise every Bold/Light companion
  would compete on identical coverage;
- **script affinity** — among fonts that cover essentially the whole block
  (within 16 characters), one whose _primary writing system_ is the block's own
  script wins. Without it, a Tai Tham font that happens to map all of Basic
  Latin would be chosen over the Latin fonts. The block → script map is derived
  from the UCD, not hand-maintained.

The endpoints are `GET /api/fonts/coverage` (one row, or all), its SSE twin
`/api/fonts/coverage/stream` (same progress shape as the font scan),
`GET /api/fonts/coverage/auto` for the assignment pass, and
`GET /api/fonts/coverage/chars?block=` — the block's **full** character list,
each character tagged with the face indices that map it (what the preview grid
uses to grey out unsupported cells).

### Entries → CSS

A “character”, a “character range” and a “code point range” are the same thing:
the range box accepts a literal character (`你`), hex (`4E00`), a range
(`4E00-9FFF`), a wildcard (`U+4E??`) or a comma/space separated list, and always
normalizes to a CSS `unicode-range`.

`compileItems()` turns each entry into exactly one `@font-face` rule. The rule's
family name is made **unique per entry** (`<base>__<id>`), so several entries
using the same physical font with different ranges or styles never merge into a
single face — that uniqueness is what makes front-to-back ordering reliable. The
`font-family` handed to the grid / buffer is the ordered list of those unique
names, ending in `serif`.

Because the stack resolves front to back, entries are **only ever appended**
(the move up/down buttons reorder an existing list, but the editor cannot insert
in the middle) — inserting would silently change which face wins for an
overlapping range.

### Uploaded fonts — `backend/font_registry.py`

The browser already resolves installed fonts through `local("Name")`, but a font
the user downloads or points at elsewhere is unreachable. Those files are
uploaded to the backend, copied into a managed folder and served back so a
`@font-face` can carry a real `src: url(…)`:

```
babelmap/backend/var/user_fonts/<id>/<original-file-name>
```

| Method                         | What it does                                                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `GET  /api/fonts/user`         | List every added font (newest first), with family / faces / glyphs.                                                 |
| `POST /api/fonts/user`         | Register a font — `{file_name, data_b64}` or `{file_name, path}`.                                                   |
| `POST /api/fonts/user/remove`  | Unregister and delete a font (the inverse of the above).                                                            |
| `GET  /api/fonts/user_file`    | Serve a registered font back for `@font-face` (`?id=`).                                                             |
| `GET  /api/fonts/user/analyze` | fontTools analysis: identity, UPEM, glyphs, cmap coverage, block histogram, variable axes, OpenType langs/features. |

Accepted extensions: `.ttf` `.otf` `.ttc` `.otc` `.woff` `.woff2`, up to 48 MB.

### CSS compile check — `POST /api/fonts/composite/validate`

`validate_css()` reports whether the CSS is **valid and takes effect**, and is
what drives the dialog's 编译通过 / 失败 indicator:

- balanced braces, unterminated strings and comments (syntax);
- every `@font-face` has both a `font-family` and a `src`;
- `src: local(…)` names a font that actually exists on this system (warning);
- `src: url(…)` pointing at `/api/fonts/user_file?id=…` references a registered
  font id (error) — other relative paths are warned about;
- `unicode-range` parses as `U+X` / `U+X-Y` / `U+XX??` with sane bounds
  (`U+0000`–`U+10FFFF`, start ≤ end, no surrogates);
- `font-weight` / `font-style` / `font-stretch` carry legal values.

It returns `{ok, errors, warnings, families, stats}`, where `ok` (no errors) is
the “takes effect” signal. The check is performed on a **comment/string-masked**
copy for structure (so braces inside strings cannot confuse it) but reads
declaration values from the original CSS, so quoted font names survive.

### Injection and separate sizes

The dialog compiles the entries + the user CSS into one `<style>` element in
`<head>` (`#babelmap-font-stack`), which is what actually restyles the surfaces.
**The grid and the edit buffer share that stack but keep separate font sizes**
(`Grid size` / `Buffer size` in the dialog footer, or the two numeric boxes in
the bottom panel).

---

## Unicode Browser — `UnicodeDialog.svelte` + `backend/version.py` / `scripts.py` / `planes.py`

**Tools → Unicode…** opens a single unified window that replaces the original
per-topic Unicode dialogs. A version selector (backed by
`/api/unicode/versions`) drives four views:

| View        | Backed by                                                              | Contents                                                       |
| ----------- | ---------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Planes**  | `GET /api/unicode/planes`, `/planes/{plane}/blocks`                    | Plane / name / abbrev / block / character / unassigned stats   |
| **Blocks**  | `GET /api/unicode/blocks`, `/{name}/characters`, `/{name}/unicodedata` | Block table + assigned characters, with full UnicodeData rows  |
| **Scripts** | `GET /api/unicode/scripts`, `/scripts/blocks?code=`                    | Script summary + per-block breakdown for one script            |
| **Compare** | `GET /api/unicode/diff?from=&to=`                                      | Blocks added/removed and character deltas between two versions |

`GET /api/unicode/history` supplies the per-character history used by the
Character Properties dialog's History tab. Clicking a character in any view
jumps the main grid to that codepoint.

---

## Emoji Lookup — `EmojiLookupDialog.svelte` + `babellib/babelsoft/unicode/emoji.py`

**Tools → Emoji Lookup…** (Shift+F8) is an Emojipedia-style browser:

- `GET /api/emoji/search?q=` — live search over CLDR names, keywords and
  codepoints;
- `GET /api/emoji/list` — every RGI emoji in CLDR order, for the browse grid
  (rendered in color, with group names and the emoji version each one appeared).

---

## Expression Search --- `backend/adv_search.py`

AST parser with tokenizer, `AND / OR / NOT`, parentheses, comparison ops
(`= != >= <= > < :`), comma lists, `|` pipe boundaries (names **and**
Tangut reference fields), and `|cc|` / `cc|` / `|cc` / `cc` wildcard
semantics. Space-separated conditions (`a=1 b=2`) imply `AND`.

### Searchable properties

| Property              | Key              | Status | Notes                                   |
| --------------------- | ---------------- | ------ | --------------------------------------- |
| Character Name        | `name`           | ✅     | wildcards, `\|` boundaries              |
| Formal Alias          | `formalalias`    | ✅     | from `NameAliases.txt`                  |
| Unicode 1.0           | `unicode1name`   | ✅     | from `UnicodeData.txt`                  |
| All aliases           | `aliases`        | ✅     | name + uni1 + formal                    |
| Whole words           | `wholewords`     | ✅     | meta-flag                               |
| General Category      | `gc`             | ✅     | Lu, Ll, Lo, ...                         |
| Combining Class       | `ccc`            | ✅     | 0–240                                   |
| Bidi Class            | `bc`             | ✅     | L, R, AL, ...                           |
| Bidi Mirrored         | `bm`             | ✅     | bool                                    |
| Decomposition Type    | `dt`             | ✅     | canonical, compat, ...                  |
| Numeric Type          | `nt`             | ✅     | Decimal, Digit, Numeric                 |
| Line Break            | `lb`             | ✅     | AK, AL, BB, ...                         |
| Binary Property       | `binary`         | ✅     | Dash, Math, Emoji, ...                  |
| Script                | `script`         | ✅     | ISO 15924                               |
| Block                 | `block`          | ✅     | name **or** CJK shortcut                |
| Plane                 | `plane`          | ✅     | 0–16                                    |
| Unicode version / age | `unicode`        | ✅     | `>=6.0`, `=5.0`                         |
| Exclude CJK UI        | `nocjkui`        | ✅     | bool                                    |
| Exclude PUA           | `nopua`          | ✅     | incl. SPUA                              |
| IRG submitter         | `submitter`      | ✅     | G,H,J,K,KP,M,MY,SAT,SG,T,UK,UTC,V       |
| IRG source ref        | `ref`            | ✅     | `*G0-*`, `G0-`                          |
| Exclude CJK Compat    | `nocomp`         | ✅     | bool                                    |
| Pinyin                | `pinyin`         | ✅     | reading + optional tone 1–5 (a, a1)     |
| Cantonese (Jyutping)  | `cantonese`      | ✅     | reading + optional tone 1–6 (aan, aan3) |
| CJK radical           | `cjkradical`     | ✅     | radical number 1–214 (e.g. 154)         |
| Residual stroke       | `residualstroke` | ✅     | CJK/Yi count; `= != > < >= <=`          |
| Yi radical            | `yiradical`      | ✅     | Yi radical glyph (e.g. ꓆)              |
| Li Fanwen 2008        | `lifanwen2008`   | ✅     | `\|22\|` exact / `22` contains          |
| Li Fanwen 1997        | `lifanwen1997`   | ✅     | `\|22\|` exact / `22` contains          |
| Kychanov 2006         | `kychanov2006`   | ✅     | `\|22\|` exact / `22` contains          |
| Sofronov 1968         | `sofronov1968`   | ✅     | `\|22\|` exact / `22` contains          |
| Nishida 1966          | `nishida1966`    | ✅     | `\|22\|` exact / `22` contains          |

**CJK block shortcuts** for `block=`:
`URO, A, B, C, D, E, F, G, H, I, Comp, CompSup`.

**IRG submitter mapping**:

- `G` → all G-source except `GS-`/`SG-` (69511 chars)
- `SG` → `GS-` (current) + `SG-` (future) (226 chars)
- `H J K KP M T UK V` → direct Unihan source
- `SAT` → S source · `UTC` → U source · `MY` → N/A (no Unihan property)

### Search pipeline

| Stage                | Status | Notes                                   |
| -------------------- | ------ | --------------------------------------- |
| Fast name-index path | ✅     | pre-built `(cp, name)` index            |
| Full-scan path       | ✅     | evaluates AST per codepoint             |
| SSE streaming        | ✅     | `QUERY / PROGRESS / results / [DONE]`   |
| Progress reporting   | ✅     | wrap-around aware                       |
| `limit=0` (all)      | ✅     |                                         |
| `filter_no_block`    | ✅     | skips codepoints with no assigned block |

---

## Menu Bar --- complete inventory

The menu **structure** mirrors the original BabelMap. The top bar contains
**9 top-level menus** + **2 right-side controls** (language switcher, theme
toggle).

Legend for the Status column:

- ✅ — the action is reachable: either handled in `App.onMenuAction()` **or**
  implemented in another window/dialog (the Notes column says where).
- ⚠️ — no handler on this item, but an equivalent capability exists elsewhere
  (Notes points to it); the menu entry itself does nothing.
- 🚫 — placeholder only: no handler and no equivalent capability anywhere.

### 0. File

The original's File menu only holds the two window-shell commands, so
this port keeps them in the same place rather than inventing new ones:

| Item                 | Keys | Status | Notes |
| -------------------- | ---- | ------ | ----- |
| Close to System Tray | ---  | ✅     | ✓ mirrors `closeToTray`; calls Tauri's `getCurrentWindow().hide()` (a browser tab only says it needs the desktop shell) |
| Exit                 | ---  | ✅     | Tauri `getCurrentWindow().close()` |

### 1. Edit

| Item               | Keys          | Status | Notes                                                                                                                                                                                                                      |
| ------------------ | ------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clear              | ---           | ✅     | clears edit buffer                                                                                                                                                                                                         |
| Cut (Plain)        | Shift+F4      | ✅     | copy then clear                                                                                                                                                                                                            |
| Cut (RTF)          | Ctrl+Shift+F4 | ✅     | RTF + plain clipboard                                                                                                                                                                                                      |
| Copy (Plain)       | F4            | ✅     | current-mode text                                                                                                                                                                                                          |
| Copy (RTF)         | Ctrl+F4       | ✅     | RTF + plain clipboard                                                                                                                                                                                                      |
| Paste              | ---           | ✅     | read clipboard                                                                                                                                                                                                             |
| Save...            | Shift+F5      | ✅     | opens SaveDialog (UTF-8/16/32 + BOM + newline)                                                                                                                                                                             |
| Copy Glyph         | F6            | ✅     | draws the selected character into a 10×-cell canvas (`m_nGlyphSize * 10`, the original's factor) using the same font stack as the grid and writes the PNG to the clipboard (`navigator.clipboard.write` + `ClipboardItem`) |
| Copy Glyph Outline | Shift+F6      | ✅     | the same canvas with `strokeText` instead of `fillText` — `CopyGlyph(true)`'s `RenderGlyphOutline`                                                                                                                         |
| Glyph Mode         | Ctrl+0        | ✅     | `DrawSimple`: every code point is measured on its own, padded to a cell (`cell = pad + ink + pad`, `pad = max(lsb, trailing)`, the GDI `GGO_METRICS` rule) and laid out left to right — no shaping, no kerning, no mark stacking, so combining marks and RTL letters each get their own cell. `GlyphText.svelte` draws that layout on a canvas over the (invisible) textarea, including its own caret and selection; **persisted** (`glyphMode`) |
| Text Mode          | Ctrl+9        | ✅     | `DrawComplex`: the plain textarea with the browser's own shaping engine, same font size — the two items are one radio in the menu, persisted |
| Colour Glyphs      | Ctrl+7        | ✅     | prefers the font's own colour glyphs (`bColour && IsColourFont() && IsColourGlyph()`): `font-variant-emoji` in text mode, `U+FE0E` suppression in glyph mode; **persisted** (`colourGlyphs`) |
| ▸ Character Mode   | ---           | ✅     | container; the active mode carries a checkmark                                                                                                                                                                             |
| ├ Char             | ---           | ✅     | `changeMode("char")` — **persisted** (`editMode`, the original's `Map Mode`)                                                                                                                                               |
| ├ NCR Hex          | ---           | ✅     | persisted                                                                                                                                                                                                                  |
| ├ NCR Decimal      | ---           | ✅     | persisted                                                                                                                                                                                                                  |
| ├ HTML             | ---           | ✅     | persisted                                                                                                                                                                                                                  |
| └ UCN              | ---           | ✅     | persisted                                                                                                                                                                                                                  |

> These four (Glyph/Text, Colour Glyphs, Character Mode, and the buffer's
> visibility) are the only _state_ in the Edit menu — everything else is an
> action. They live in `settings.svelte.ts` next to the Fonts preferences, so one
> `localStorage` key holds the whole session state, and both the Edit menu and the
> bottom-panel radios read/write the same values.

### 2. Find

| Item                 | Keys     | Status |
| -------------------- | -------- | ------ |
| Search Previous Char | Shift+F3 | ✅     |
| Search Next Char     | F3       | ✅     |
| Go to Han Ideograph  | Shift+F2 | ✅     |
| Go to Code Point     | Ctrl+G   | ✅     |
| Locate Character     | F2       | ✅     |

### 3. Tools

> **Note:** _Advanced Character Search_ and _Han Ideograph Search_ need no
> separate menu dialog — both are already implemented by the **Expression
> Search** box in the bottom panel (`pinyin=`, `cjkradical=`,
> `residualstroke=` … reach the same tables).

| Item                             | Keys      | Status | Notes                                                                                                                                                                                                 |
| -------------------------------- | --------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unicode...                       | ---       | ✅     | unified window: version selector + Planes/Blocks/Scripts/Compare views + character grid (click → main grid)                                                                                           |
| Mandarin (Pinyin) Lookup...      | F12       | ✅     | `LookupDialog` in `pinyin` mode — syllable + tone (any/1–5), one row per character, click to jump                                                                                                     |
| Cantonese (Jyutping) Lookup...   | Shift+F12 | ✅     | same window, `jyutping` mode                                                                                                                                                                          |
| Zhuang Lookup...                 | ---       | ✅     | same window, `zhuang` mode                                                                                                                                                                            |
| Han Radical Lookup...            | F11       | ✅     | same window, `han_radical` mode — a radical character (`水`) or its IRG number (`85`) plus an extra-stroke count                                                                                      |
| Yi Radical Lookup...             | Shift+F11 | ✅     | same window, `yi_radical` mode — a Liangshan radical character or its number                                                                                                                          |
| Emoji Lookup...                  | Shift+F8  | ✅     | Emojipedia-style: live search by name/keyword/codepoint; colored grid with CLDR names, groups & emoji version                                                                                         |
| Character Properties...          | F9        | ✅     | C++-mirrored: summary bar + grouped Unicode properties (identity, block/script/version, general, decomposition/numeric, joining, case mappings, encodings) + Copy + per-version Character History tab |
| Supplementary Information        | ---       | ✅     | opens **Character Properties** on its **Supplementary** tab — `OnToolsSupplementaryInformation`'s CJKV (`CDialogCJKV`) / Tangut (`CDialogTangut`) / hieroglyph (`CDialogHieroglyph`) data from `GET /api/supplementary/{cp}` |
| Extended Character Properties... | Shift+F9  | ✅     | lives inside Character Properties as the **Extended Properties** tab (`view="extended"`)                                                                                                              |
| Ideographic Properties...        | Ctrl+F9   | ✅     | lives inside Character Properties as the **Ideographic Properties** tab (shown when the char has ideographic data)                                                                                    |
| Character History...             | ---       | ✅     | inside Character Properties (F9 / double-click a cell)                                                                                                                                                |
| Unicode Variation Sequences...   | ---       | ✅     | every IVS / emoji / standardized sequence is listed in Character Properties (**Unicode Properties** page); the nav panel's **IVS** button opens that dialog (`OnButtonUnicodeVariationSequences` → `CDialogUVS`), and clicking a sequence inserts base + VS into the edit buffer |
| Generate Core UCD Data...        | ---       | ✅     | `UcdDialog` — block picker + hex range + the two algorithmic-run checkboxes, over the 15 `Unicode::UCDFields` columns; Generate / Copy (TSV) / Save, rows from `GET /api/ucd/generate` |
| Generate Full UCD XML Data...    | ---       | ✅     | downloads `ucd.nounihan.flat.babelmap.xml` from `GET /api/ucd/xml` — `OnToolsXMLData`'s own file name |
| OpenType Test Framework...       | ---       | ✅     | engine picker (HarfBuzz / HarfRust / BabelScript / Graphite / Yudit / Uniscribe / DirectWrite / ICU / FreeType), face picker, per-lookup trace, SVG preview (see the shaping-engine section)          |

### 4. Fonts --- ✅ implemented

All three surfaces the original had are now wired, and the menu mirrors the
persisted settings (a checkmark/radio dot per item, exactly like
`OnUpdateOptionsFonts`). Preferences live in
`frontend/src/lib/settings.svelte.ts` and are mirrored to `localStorage`
(`babelmap.settings.v1`), so they survive a reload.

| Item                                                                                      | Keys     | Status | Notes                                                                                                                                                                                             |
| ----------------------------------------------------------------------------------------- | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Single Font                                                                               | Ctrl+1   | ✅     | one family for everything: the grid / buffer use `fontStack.singleFamily` (picker in the edit buffer), nothing is injected as `@font-face`. `Alt+1` also works — a tabbed browser swallows Ctrl+1 |
| Composite Font                                                                            | Ctrl+2   | ✅     | back to block assignments + the point-and-click stack; an empty stack leaves `font-family` untouched                                                                                              |
| List All Font Styles                                                                      | ---      | ✅     | off (default) keeps one primary face per family, on enumerates every face — both in the Overview list and in the coverage/Auto analysis (`?all_styles=true`)                                      |
| Legacy Font Enum                                                                          | ---      | ✅     | shows the GDI names (name ID 1/2, e.g. `Alegreya Black` / `Regular`) instead of the typographic ones (ID 16/17). Both sets are stored by the scan, so toggling never re-scans                     |
| Show Symbol Mappings                                                                      | ---      | ✅     | U+F020–U+F0FF (a symbol font's real `cmap` range) is displayed as the ASCII/CP1252 character it stands for: `U+F080 → €`; the cell is tinted and the tooltip shows both code points               |
| ▸ Grid Font Size                                                                          | ---      | ✅     | the five presets set the grid size directly (Ctrl+wheel still works and leaves every preset unchecked)                                                                                            |
| ├ Very Small / Small / Medium / Large / Very Large                                        | ---      | ✅     | 12 / 16 / 20 / 24 / 28 px — the original's `GridPointSize[][2]` table                                                                                                                             |
| ▸ Quality                                                                                 | ---      | ✅     | picks the rasterisation mode; a checkmark follows `settings.fontQuality`                                                                                                                          |
| ├ Default / Draft / Proof / Non-antialiased / Antialiased / ClearType / ClearType Natural | ---      | ✅     | the seven `LOGFONT.lfQuality` modes, implemented for real (see below)                                                                                                                             |
| Font Quality...                                                                           | ---      | ✅     | opens `FontQualityDialog` — a live seven-way comparison of the same sample                                                                                                                        |
| Fonts Overview                                                                            | ---      | ✅     | opens `FontOverviewDialog` (SSE scan progress, see below)                                                                                                                                         |
| Export Glyphs                                                                             | ---      | ✅     | opens `ExportGlyphsDialog` — a zip of one image per code point                                                                                                                                    |
| Composite Mapping                                                                         | Shift+F7 | ✅     | opens `CompositeFontDialog` (block coverage + Auto, entry appends with variable axes, generated CSS view)                                                                                         |

> Add / Remove Fonts, Font Analysis, Font Coverage and Font Information are **not
> menu entries** any more: clicking them could only close the menu, because the
> three-view detail panel they described lives inside **Fonts → Fonts Overview**
> (left column for add/remove, right column for analysis/coverage/metadata). The
> menu now lists only entries that do something.

#### Quality is real, and it is honest about its scope

`lfQuality` is a GDI concept: the application asks Windows _how_ to turn an
outline into pixels. A browser cannot be asked that — WebView2 owns the text
pipeline, so the character grid always uses the system's own rasterisation.
Rather than fake it, the quality modes are produced by rasterising ourselves in
`backend/glyph_render.py` with **FreeType** (the library GDI and Chrome both sit
on top of) and exposing the results:

| `lfQuality`         | FreeType settings                                  | `draft`/`non-aa` difference  |
| ------------------- | -------------------------------------------------- | ---------------------------- |
| 0 DEFAULT           | `FT_LOAD_TARGET_LIGHT` (light hinting + grayscale) | —                            |
| 1 DRAFT             | `TARGET_MONO` + `NO_HINTING` (1-bit, unhinted)     | 2 colours only               |
| 2 PROOF             | `TARGET_NORMAL` + `NO_HINTING` (exact outlines)    | —                            |
| 3 NONANTIALIASED    | `TARGET_MONO` (hinted 1-bit)                       | 2 colours only               |
| 4 ANTIALIASED       | `TARGET_NORMAL` (hinted grayscale)                 | —                            |
| 5 CLEARTYPE         | `TARGET_LCD` + `FT_LCD_FILTER_DEFAULT`             | RGB subpixel fringes         |
| 6 CLEARTYPE_NATURAL | `TARGET_LCD` + `FT_LCD_FILTER_NONE` + no hinting   | unfiltered, natural advances |

Measured on the same string: rows 1/3 come back with **2** distinct colours,
rows 5/6 with ~430 (per-channel subpixel coverage) — the modes genuinely differ.
The selection therefore governs the **Font Quality dialog** and **Export Font
Glyphs**; the grid keeps system rendering, and both the dialog and this table
say so instead of implying otherwise.

Endpoints: `GET /api/glyphs/qualities`, `GET /api/glyphs/preview?cp=&font=&size=&quality=&cell_w=&cell_h=&scale=`,
`GET /api/glyphs/sample?text=&font=&size=&quality=&scale=` (all return an image),
and `POST /api/glyphs/export` → `application/zip` with one `U+XXXX.png/bmp/gif/jpg`
per code point.

### 5. Options --- ✅ implemented

Every entry is wired, persisted in `settings.svelte.ts` (one `localStorage`
key for the whole app) and shows a radio dot / checkmark for its current value,
exactly like the original's `OnUpdateOptions*` handlers. Defaults follow the
original's `Main/Registry.cpp` tables.

| Item                                                 | Status | Effect / notes                                                                                                                                                                                                                                                     |
| ---------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Unicode Blocks ▸ Alphabetical / Code Point           | ✅     | sorts the block dropdown (alphabetical is the original's default)                                                                                                                                                                                                  |
| Name Search ▸ Match Aliases                          | ✅     | `/api/search/name?aliases=1` — searches also match the `NameAliases.txt` entries                                                                                                                                                                                   |
| Go To Code Points ▸ Hexadecimal / Decimal            | ✅     | the bottom-panel input parses in the chosen base (an explicit `$`/`0x`/`U+` or `#` still wins), and its placeholder follows the setting                                                                                                                            |
| Alt Representation (8)                               | ✅     | the info-bar field next to the character name — `Decimal N`, `\uXXXX`/`\UXXXXXXXX`, surrogate pairs, `&#xXXXX;`, `&#N;`, HTML entity, `\xXX` bytes, `\NNN` bytes. Shared with Edit ▸ Character Mode (`src/lib/altRepr.ts`)                                         |
| CJKV Readings (6) + Upper case + Tone numbers        | ✅     | appends `[reading]` to the description via `GET /api/readings/{cp}`; the flags are the same global switches the C++ uses (`Lookup::UseUpperCaseReadings`, `UseToneNumbers`)                                                                                        |
| Tangut Readings (6) + Tone numbers                   | ✅     | same endpoint; `gong2008` is published from the Li Fanwen 2008 table (the menu says so), and Miyake 2012/2015 select the two Miyake variants                                                                                                                       |
| Character Grid ▸ Single/Double click, Copy on select | ✅     | single-click mode selects + appends to the buffer; double-click mode requires a double click, so a stray click never changes the selection; copy-on-select puts the character on the clipboard                                                                     |
| Popup Magnification ▸ 36/72/108/144                  | ✅     | **Ctrl + hover** a cell → that glyph only, drawn at twice the chosen point size (72–288 px), floating above the grid and clamped to the viewport; a plain hover does nothing and the cells underneath keep their own hover state |
| Colour Coding (8)                                    | ✅     | paints every cell from the code point's General Category / Bidi Class / Bidi Mirroring / Decomposition Type / Numeric Type / Script / Unicode version. The grid endpoint computes those attributes on the page (`?attrs=1`), so nothing is paid when coding is off |
| Cut and Copy Button Defaults                         | ✅     | the edit buffer's **Copy** / **Cut** buttons produce plain text or RTF — the original's item is literally about those buttons                                                                                                                                      |
| Status Bar ▸ 3 toggles                               | ✅     | _Show algorithmic character names_ / _Show CJK source references_ / _Show Tangut source references_ are three independent checkboxes (not a radio): each one decides whether that piece appears in the description                                                 |
| Other ▸ Convert Basic Latin                          | ✅     | when on, printable ASCII is escaped too when the edit buffer converts; when off (default) it stays literal                                                                                                                                                         |
| Other ▸ Rotate Vertical Scripts                      | ✅     | Mongolian and Phags-pa glyphs are rendered with `writing-mode: vertical-lr` (`text-orientation: sideways`). Default is **off** here — the original defaults it on, but that would change the grid for those blocks out of the box                                  |
| Other ▸ Close to System Tray                         | ⚠️     | the flag is persisted but only a desktop shell can honour it; the browser build has no tray                                                                                                                                                                        |
| Font Configuration Options…                          | ✅     | opens the Composite Font dialog (the font stack _is_ the font configuration)                                                                                                                                                                                       |
| Customize Colours…                                   | ✅     | `ColourCodingDialog` — per-value background colour for every coding mode, stored as `colourOverrides[mode:value]`                                                                                                                                                  |
| Reset Options…                                       | ✅     | confirmation, then every preference returns to its default (the original's `m_pRegistry->Reset()`), with no reload needed                                                                                                                                          |

#### Colour coding: what is faithful and what is generated

The original keeps hand-tuned colour tables, one entry per value, including one
per **script** (≈170 of them). `src/lib/colourCoding.ts` reproduces that intent
in two layers:

- **curated** colours for the values people actually look at — all 30 General
  Categories, all 23 Bidi Classes, both Mirroring states, the 17 Decomposition
  Types, the 4 Numeric Types, the ~33 major scripts and a 17-step version
  gradient;
- **derived** colours for the long tail (mostly minor scripts), where the hue
  comes from a stable hash of the script name — so a script always gets the same
  colour, but it is not the original's hand-picked one.

Anything can then be overridden per value in **Customize Colours…**.

### 6. Bookmarks --- ✅ implemented

The original keeps a bookmark list in its registry (`Registry::AddBookmark`,
capped at `CDialogBookmarks::MaxBookmarks = 32`) and **rebuilds the menu from it**
so each bookmark becomes its own menu entry. `src/lib/bookmarks.svelte.ts`
reproduces that on top of the same persisted settings object.

| Item                | Keys        | Status | Notes                                                                                                                                                                                                          |
| ------------------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manage Bookmarks... | ---         | ✅     | `BookmarksDialog` — Code Point / Character Name list with sortable columns, Add / Remove / Remove All, double-click a row to jump. Removing or sorting writes the list back, exactly like `ReorderBookmarks()` |
| Add Bookmark        | Insert      | ✅     | bookmarks the selected character (silent when it is already bookmarked or the list is full)                                                                                                                    |
| Remove Bookmark     | Ctrl+Delete | ✅     | removes the selected character's bookmark                                                                                                                                                                      |
| Clear All Bookmarks | ---         | ✅     | empties the list (the dialog's _Remove All_ asks first, the menu item does not — same as the original)                                                                                                         |
| _(dynamic entries)_ | ---         | ✅     | one `U+XXXX NAME` entry per bookmark below the separator, clicking one jumps to that code point                                                                                                                |

> The dialog's **Add** resolves each typed code point's character name through
> `/api/codepoint/{cp}` so the menu can show `U+4E00 CJK UNIFIED IDEOGRAPH-4E00`
> without a lookup on every menu render.

### 7. View

| Item                   | Keys | Status | Notes                                                                                                                                                                                           |
| ---------------------- | ---- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Medium Size            | ---  | ✅     | radio dot; selects the **Medium** column of the original's `GridPointSize[][2]` table (10/12/16/20/24 px), **persisted** (`viewSize`) — it scales the grid, not the dialogs                     |
| Large Size             | ---  | ✅     | the **Large** column (12/16/20/24/28 px)                                                                                                                                                        |
| Hide Unassigned Ranges | ---  | ✅     | ✓ indicator; on = assigned blocks only, off = unassigned ranges too; **persisted** (`showReservedRanges`)                                                                                       |
| Hide Reserved Planes   | ---  | ✅     | ✓ indicator; off = the 7 assigned planes on the tab bar, on = all 17 (planes 4–13 as `Plane 4`…); falls back to the BMP when the current plane disappears; **persisted** (`showReservedPlanes`) |
| Show Edit Buffer       | ---  | ✅     | View ▸ Show Edit Buffer toggles the buffer (and the bottom panel's **Hide** button), checkmark reflects the state, **persisted** (`editBufferVisible`, the original's `Show Edit Buffer`)       |
| Keep on Top            | ---  | ✅     | ✓ indicator, **persisted** (`keepOnTop`); calls Tauri's `setAlwaysOnTop` in the desktop shell and only remembers the flag in a browser tab                                                      |

> Zoom-in / zoom-out and theme switching are **not** in this menu: the theme
> toggle is the ☀ / ☾ control on the right of the menu bar.

### 8. Help --- ✅ implemented

| Item              | Keys | Status | Notes                                                                                                                                                                                                                                                    |
| ----------------- | ---- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Online Help       | F1   | ✅     | `HelpDialog.svelte` — the shortcut reference is generated from `localizedMenus()`, so it always lists exactly the accelerators the menu bar advertises (every item that carries a `k`), grouped by menu                                                  |
| About BabelMap... | ---  | ✅     | same window — product version, the Unicode release the bundled data supports, how many Unicode versions are on disk, and the backend/Python versions from `GET /api/about` (the original's `CDialogAbout` reads these from the Windows version resource) |

> The original's About box also shows the IVD date, the Emoji version and the
> Uniscribe `usp10.dll` version. This port shows the first two when the data
> directory exposes them and `—` otherwise; Uniscribe is Windows-only and has no
> meaning for the browser/Svelte renderer.
>
> `F1` is also handled in `App.svelte`'s `onKey`, but a browser tab swallows the
> real key — in the Tauri window it works as advertised.

### Right-side controls

| Control              | Status | Notes          |
| -------------------- | ------ | -------------- |
| Language switcher    | ✅     | 7 languages    |
| Theme toggle (☀ / ☾) | ✅     | `onDarkToggle` |

---

## Keyboard shortcuts (implemented)

| Keys                         | Action                              |
| ---------------------------- | ----------------------------------- |
| `F4` / `Ctrl+F4`             | Copy plain / RTF                    |
| `Shift+F4` / `Ctrl+Shift+F4` | Cut plain / RTF                     |
| `Shift+F5`                   | Save                                |
| `F2` / `Ctrl+G` / `Shift+F2` | Locate / Goto CP / Han              |
| `F3` / `Shift+F3`            | Next / Prev search result           |
| `F9` / `Shift+F8`            | Character Properties / Emoji Lookup |
| `F6` / `Shift+F6`            | Copy Glyph / Copy Glyph Outline     |
| `F11` / `Shift+F11`          | Han / Yi radical lookup             |
| `F12` / `Shift+F12`          | Mandarin / Cantonese lookup         |
| `Insert` / `Ctrl+Delete`     | Add / remove bookmark               |
| `F1`                         | Online Help (Help + About window)   |
| `Arrow` / `PgUp` / `PgDn`    | Grid navigation                     |
| `Enter`                      | Add selected char to buffer         |

---

## Getting Started

### 1. Install frontend dependencies

```bash
cd babelmap/frontend
npm install
```

The frontend toolchain is **Vite 8** + `@sveltejs/vite-plugin-svelte` 7, with a
**TypeScript 6 + TypeScript 7** pair for type checking: `svelte-check` still
drives the classic TS 6 API for the Svelte language service, while
`@typescript/native` (an npm alias for `typescript@7`, the native compiler)
provides the `tsgo` engine:

```bash
npm run check     # svelte-check --tsgo  (TypeScript 7 native)
```

(Plain `svelte-check` runs against TS 6; the `--tsgo` flag is what selects the
native compiler, and it needs both packages installed.)

### 2. Install backend dependencies (uv)

Python libraries are managed in a single place with [uv](https://docs.astral.sh/uv/)
(`pyproject.toml` at the repo root — this supersedes the old `requirements.txt` files).

```bash
uv sync          # creates .venv + uv.lock, installs all deps (incl. dev/pytest)
```

### 3. Start the backend (terminal 1)

```bash
uv run python babelmap/backend/server.py
# → http://127.0.0.1:18080
```

### 4. Start the frontend dev server (terminal 2)

```bash
cd babelmap/frontend
npm run dev
# → http://localhost:18081
```

### 5. Run tests for backend

```bash
uv run python -m pytest tests/ -q
```

---

## Tauri Build (Windows/macOS/Linux)

```bash
# Prerequisites: Rust, Node.js, Python 3, uv
cd babelmap
npm run tauri dev    # Development with hot-reload
npm run tauri build  # Production installer
```
