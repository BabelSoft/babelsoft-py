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

| Area                        | Status                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| Backend REST/SSE API        | ✅ 35 routes implemented                                           |
| Character grid & navigation | ✅ Complete                                                        |
| Expression search engine    | ✅ Complete (AST parser + SSE streaming)                           |
| Edit buffer (modes, RTF)    | ✅ Complete                                                        |
| Save dialog (encodings/BOM) | ✅ Complete                                                        |
| Context menu (text editing) | ✅ Complete                                                        |
| Menu bar                    | ⚠️ Structure complete; Edit/Find/Tools\(3)/Fonts\(1)/View\(2) live |
| Plane tabs                  | ✅ Complete (7 fixed / 17 unfiltered)                              |
| Block selector              | ✅ Complete                                                        |
| Localization                | ✅ 7 languages                                                     |
| Fonts toolbar               | ⚠️ Size only; most Fonts-menu items 🚫                             |
| Tools menu dialogs          | ✅ Unicode / Emoji Lookup / Character Properties / OpenType Test   |
| OpenType Test Framework     | ✅ Full shaping debugger (`/api/opentype/*`, 9 engines)            |
| Emoji Lookup                | ✅ `/api/emoji/*` (search + browse by CLDR group)                  |
| Font Overview               | ✅ `/api/fonts/overview` + `/api/fonts/raw`                        |
| Unicode window (Unicode...) | ✅ Versions / Planes / Blocks / Scripts / Compare diff             |
| Options menu                | 🚫 Not implemented                                                 |
| Bookmarks                   | 🚫 Menu items only (no handler)                                    |
| Help / About                | 🚫 Not implemented                                                 |
| Glyph rendering (PIL)       | ✅ `/api/glyph` available; grid uses text                          |

---

## Backend API --- `backend/server.py`

All endpoints implemented and working. Port **18080** (`http://127.0.0.1:18080`).

| Endpoint                                         | Description                                              | Status |
| ------------------------------------------------ | -------------------------------------------------------- | ------ |
| `GET /api/health`                                | Health check                                             | ✅     |
| `GET /api/planes`                                | List Unicode planes (0–16)                               | ✅     |
| `GET /api/blocks`                                | All blocks (valid planes, no surrogates)                 | ✅     |
| `GET /api/blocks/{plane}`                        | Blocks for a plane                                       | ✅     |
| `GET /api/grid/{plane}?scroll=&filter_no_block=` | Character grid page (8×16)                               | ✅     |
| `GET /api/grid/{plane}/goto/{cp}`                | Jump to codepoint (+`filter_no_block`)                   | ✅     |
| `GET /api/grid/{plane}/block/{name}`             | Jump to a block by name                                  | ✅     |
| `GET /api/grid/{plane}/navigate`                 | Grid navigation (page/block/plane)                       | ✅     |
| `GET /api/codepoint/{cp}`                        | Codepoint info (GC, script, pinyin...)                   | ✅     |
| `GET /api/glyph/{cp}?font=&size=`                | Glyph PNG as base64 (Pillow)                             | ✅     |
| `GET /api/search/name?q=`                        | Unified expression search                                | ✅     |
| `GET /api/search/advanced?q=`                    | Alias of `/search/name`                                  | ✅     |
| `GET /api/search/name/stream`                    | SSE streaming search                                     | ✅     |
| `GET /api/search/han_source`                     | CJK IRG source-reference search                          | ✅     |
| `GET /api/search/properties`                     | Property autocomplete list                               | ✅     |
| `GET /api/fonts`                                 | List font names                                          | ✅     |
| `GET /api/fonts/overview?dirs=`                  | Full font inventory: families, faces, features, coverage | ✅     |
| `GET /api/fonts/raw?path=`                       | Raw font file bytes (Font Overview preview)              | ✅     |
| `GET /api/emoji/search?q=&limit=`                | Emoji name/keyword/codepoint search                      | ✅     |
| `GET /api/emoji/list?limit=`                     | Emoji browse list (CLDR groups)                          | ✅     |
| `GET /api/unicode/versions`                      | Unicode version list                                     | ✅     |
| `GET /api/unicode/scripts`                       | Script list with block counts                            | ✅     |
| `GET /api/unicode/scripts/blocks?code=`          | Blocks of a script                                       | ✅     |
| `GET /api/unicode/planes`                        | Plane stats (assigned/blocks/scripts)                    | ✅     |
| `GET /api/unicode/planes/{plane}/blocks`         | Blocks of a plane                                        | ✅     |
| `GET /api/unicode/blocks?version=`               | Blocks for a Unicode version                             | ✅     |
| `GET /api/unicode/blocks/{name}/characters`      | Characters of a block (+`version`)                       | ✅     |
| `GET /api/unicode/blocks/{name}/unicodedata`     | UnicodeData rows of a block (+`version`)                 | ✅     |
| `GET /api/unicode/diff?from=&to=`                | Two-version diff (chars/blocks added/removed)            | ✅     |
| `GET /api/unicode/history?cp=`                   | Character history across versions                        | ✅     |
| `GET /api/opentype/fonts`                        | Font list for the OpenType Test dialog                   | ✅     |
| `POST /api/opentype/font_faces`                  | Container/face enumeration (TTC/OTC/WOFF)                | ✅     |
| `GET /api/opentype/meta`                         | Engine list + capabilities                               | ✅     |
| `POST /api/opentype/shape`                       | Shape a run with a chosen engine                         | ✅     |
| `POST /api/opentype/render`                      | Render shaped glyphs to an image                         | ✅     |
| `GET /api/convert/edit?text=&mode=`              | NCR/HTML/UCN conversion helpers                          | ✅     |

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

| Component                          | Purpose                                                     | Status       |
| ---------------------------------- | ----------------------------------------------------------- | ------------ |
| `App.svelte`                       | Root layout, state, menu actions, search glue               | ✅           |
| `MenuBar.svelte`                   | Dropdown menus, submenus, ✓ states, theme                   | ⚠️ see below |
| `PlaneTabs.svelte`                 | Plane tab bar                                               | ✅           |
| `CharacterGrid.svelte`             | 16-col grid, reserved/nonchar/highlight                     | ✅           |
| `GridHeader.svelte`                | Block title + column headers                                | ✅           |
| `NavPanel.svelte`                  | Vertical slider + nav buttons (IVS disabled)                | ✅           |
| `BottomPanel.svelte`               | Block selector, AdvSearch, goto, edit buffer                | ✅           |
| `AdvSearch.svelte`                 | Expression input + property autocomplete                    | ✅           |
| `SearchResultsWindow.svelte`       | Draggable/resizable results window                          | ✅           |
| `InfoBar.svelte`                   | U+XXXX char name + decimal                                  | ✅           |
| `StatusBar.svelte`                 | Status messages, plane/font/row info                        | ✅           |
| `SaveDialog.svelte`                | Save with encoding/BOM/newline                              | ✅           |
| `ContextMenu.svelte`               | Textarea edit menu (undo/case/normalize...)                 | ✅           |
| `LangSwitcher.svelte`              | Language picker                                             | ✅           |
| `UnicodeDialog.svelte`             | Unicode window: versions/planes/blocks/scripts/compare diff | ✅           |
| `CharacterPropertiesDialog.svelte` | C++-mirrored properties + history tab                       | ✅           |
| `EmojiLookupDialog.svelte`         | Emojipedia-style emoji browser/search                       | ✅           |
| `FontOverviewDialog.svelte`        | Installed-font inventory, features, coverage                | ✅           |
| `OpenTypeTestDialog.svelte`        | Crowbar-style shaping debugger (9 engines)                  | ✅           |

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
**8 top-level menus** + **2 right-side controls** (language switcher, theme
toggle). ✅ = handled in `App.onMenuAction()`, 🚫 = placeholder (no handler),
⚠️ = container/submenu only, functionality lives elsewhere.

### 1. Edit

| Item               | Keys          | Status | Notes                 |
| ------------------ | ------------- | ------ | --------------------- |
| Clear              | ---           | ✅     | clears edit buffer    |
| Cut (Plain)        | Shift+F4      | ✅     | copy then clear       |
| Cut (RTF)          | Ctrl+Shift+F4 | ✅     | RTF + plain clipboard |
| Copy (Plain)       | F4            | ✅     | current-mode text     |
| Copy (RTF)         | Ctrl+F4       | ✅     | RTF + plain clipboard |
| Paste              | ---           | ✅     | read clipboard        |
| Save...            | Shift+F5      | ✅     | opens SaveDialog      |
| Copy Glyph         | F6            | 🚫     | placeholder           |
| Copy Glyph Outline | Shift+F6      | 🚫     | placeholder           |
| Glyph Mode         | Ctrl+0        | ✅     | buffer glyph display  |
| Text Mode          | Ctrl+9        | ✅     | buffer text display   |
| Colour Glyphs      | Ctrl+7        | ✅     | toggles colour flag   |
| ▸ Character Mode   | ---           | ⚠️     | container             |
| ├ Char             | ---           | ✅     | `changeMode("char")`  |
| ├ NCR Hex          | ---           | ✅     |                       |
| ├ NCR Decimal      | ---           | ✅     |                       |
| ├ HTML             | ---           | ✅     |                       |
| └ UCN              | ---           | ✅     |                       |

### 2. Find

| Item                 | Keys     | Status |
| -------------------- | -------- | ------ |
| Search Previous Char | Shift+F3 | ✅     |
| Search Next Char     | F3       | ✅     |
| Go to Han Ideograph  | Shift+F2 | ✅     |
| Go to Code Point     | Ctrl+G   | ✅     |
| Locate Character     | F2       | ✅     |

### 3. Tools --- partial

> **Note:** _Advanced Character Search_ and _Han Ideograph Search_ need no
> separate menu dialog — both are already implemented by the **Expression
> Search** box in the bottom panel. The same box also replaces the
> Mandarin (Pinyin), Cantonese (Jyutping), Han Radical, Yi Radical and
> Tangut References lookups via `pinyin=`, `cantonese=`, `cjkradical=`,
> `residualstroke=`, `yiradical=` and the Tangut reference fields
> (`lifanwen2008=`, `lifanwen1997=`, `kychanov2006=`, `sofronov1968=`,
> `nishida1966=`).

| Item                             | Keys     | Status | Notes                                                                                                                                                                                                 |
| -------------------------------- | -------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unicode...                       | ---      | ✅     | unified window: version selector + Planes/Blocks/Scripts/Compare views + character grid (click → main grid)                                                                                           |
| Emoji Lookup...                  | Shift+F8 | ✅     | Emojipedia-style: live search by name/keyword/codepoint; colored grid with CLDR names, groups & emoji version                                                                                         |
| Character Properties...          | F9       | ✅     | C++-mirrored: summary bar + grouped Unicode properties (identity, block/script/version, general, decomposition/numeric, joining, case mappings, encodings) + Copy + per-version Character History tab |
| Extended Character Properties... | Shift+F9 | 🚫     |                                                                                                                                                                                                       |
| Ideographic Properties...        | Ctrl+F9  | 🚫     |                                                                                                                                                                                                       |
| Character History...             | ---      | ✅     | inside Character Properties (F9 / double-click a cell)                                                                                                                                                |
| Unicode Variation Sequences...   | ---      | 🚫     |                                                                                                                                                                                                       |
| Generate Core UCD Data...        | ---      | 🚫     |                                                                                                                                                                                                       |
| Generate Full UCD XML Data...    | ---      | 🚫     |                                                                                                                                                                                                       |
| OpenType Test Framework...       | ---      | ✅     | Crowbar-style shaping debugger: 9 engines, per-lookup trace, face picker, glyph render                                                                                                                |

### 4. Fonts --- ⚠️ partial

| Item                                                                                      | Keys     | Status | Notes                                                                          |
| ----------------------------------------------------------------------------------------- | -------- | ------ | ------------------------------------------------------------------------------ |
| Single Font                                                                               | Ctrl+1   | 🚫     |                                                                                |
| Composite Font                                                                            | Ctrl+2   | 🚫     |                                                                                |
| List All Font Styles                                                                      | ---      | 🚫     |                                                                                |
| Legacy Font Enum                                                                          | ---      | 🚫     |                                                                                |
| Show Symbol Mappings                                                                      | ---      | 🚫     |                                                                                |
| ▸ Grid Font Size                                                                          | ---      | ⚠️     | size works only via bottom-panel numeric input                                 |
| ├ Very Small / Small / Medium / Large / Very Large                                        | ---      | 🚫     |                                                                                |
| ▸ Quality                                                                                 | ---      | 🚫     |                                                                                |
| ├ Default / Draft / Proof / Non-antialiased / Antialiased / ClearType / ClearType Natural | ---      | 🚫     |                                                                                |
| Add Fonts                                                                                 | ---      | 🚫     |                                                                                |
| Remove Fonts                                                                              | ---      | 🚫     |                                                                                |
| Fonts Overview                                                                            | ---      | ✅     | installed-font inventory: families, faces, GSUB/GPOS features, script coverage |
| Font Analysis                                                                             | F7       | 🚫     |                                                                                |
| Font Coverage                                                                             | ---      | 🚫     | (coverage is shown inside Fonts Overview)                                      |
| Font Information                                                                          | Ctrl+F7  | 🚫     |                                                                                |
| Export Glyphs                                                                             | ---      | 🚫     |                                                                                |
| Composite Mapping                                                                         | Shift+F7 | 🚫     |                                                                                |

### 5. Options --- 🚫 all placeholders

| Item                | Status |
| ------------------- | ------ |
| Unicode Blocks      | 🚫     |
| Name Search         | 🚫     |
| Go To Code Points   | 🚫     |
| Alt Representation  | 🚫     |
| CJKV Readings       | 🚫     |
| Tangut Readings     | 🚫     |
| Character Grid      | 🚫     |
| Popup Magnification | 🚫     |
| Colour Coding       | 🚫     |
| Cut/Copy Defaults   | 🚫     |
| Status Bar          | 🚫     |
| Other               | 🚫     |
| Font Config         | 🚫     |
| Customize Colours   | 🚫     |
| Reset               | 🚫     |

### 6. Bookmarks --- 🚫 placeholders

| Item            | Keys        | Status |
| --------------- | ----------- | ------ |
| Manage          | ---         | 🚫     |
| Add Bookmark    | Insert      | 🚫     |
| Remove Bookmark | Ctrl+Delete | 🚫     |
| Clear           | ---         | 🚫     |

### 7. View

| Item                     | Keys | Status | Notes                                                       |
| ------------------------ | ---- | ------ | ----------------------------------------------------------- |
| Medium Size              | ---  | 🚫     | placeholder                                                 |
| Large Size               | ---  | 🚫     | placeholder                                                 |
| Filter Unassigned Blocks | ---  | ✅     | ✓ indicator; on = assigned blocks only, off = all 17 planes |
| Hide Reserved Planes     | ---  | 🚫     | placeholder                                                 |
| Show Edit Buffer         | ---  | 🚫     | placeholder                                                 |
| Keep On Top              | ---  | 🚫     | placeholder                                                 |

> The **Toggle Theme** control lives on the right side of the menu bar, not in
> the View menu.

### 8. Help --- 🚫 placeholders

| Item          | Keys | Status |
| ------------- | ---- | ------ |
| BabelMap Help | F1   | 🚫     |
| About         | ---  | 🚫     |

### Right-side controls

| Control              | Status | Notes          |
| -------------------- | ------ | -------------- |
| Language switcher    | ✅     | 7 languages    |
| Theme toggle (☀ / ☾) | ✅     | `onDarkToggle` |

---

## Keyboard shortcuts

Only the keys below are actually bound by the global `onKey` handler in
`App.svelte` — the shortcut hints shown beside menu items are **display labels
only** and are not wired to key events.

| Keys                                                                                                                                                                                                                              | Action                      | Status |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------ |
| `F4` / `Ctrl+F4`                                                                                                                                                                                                                  | Copy plain / RTF            | ✅     |
| `Shift+F4` / `Ctrl+Shift+F4`                                                                                                                                                                                                      | Cut plain / RTF             | ✅     |
| `F9`                                                                                                                                                                                                                              | Character Properties        | ✅     |
| `Shift+F8`                                                                                                                                                                                                                        | Emoji Lookup                | ✅     |
| `Arrow` / `PgUp` / `PgDn`                                                                                                                                                                                                         | Grid navigation             | ✅     |
| `Enter`                                                                                                                                                                                                                           | Add selected char to buffer | ✅     |
| `Shift+F5` Save, `F2` / `Ctrl+G` / `Shift+F2` / `F3` / `Shift+F3` search, `F1` Help, `F6` / `Shift+F6` glyph copy, `Ctrl+0` / `Ctrl+9` / `Ctrl+7` modes, `Ctrl+1` / `Ctrl+2` fonts, `F7` / `Ctrl+F7` / `Shift+F7` — **not bound** | 🚫                          |

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
