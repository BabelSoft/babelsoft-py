# BabelMap --- Cross-Platform Unicode Character Map

Modern rebuild of the BabelSoft BabelMap tool using:

| Layer    | Technology            | Purpose                       |
| -------- | --------------------- | ----------------------------- |
| Shell    | Tauri 2 (Rust)        | Native window, lifecycle      |
| Frontend | Svelte 5 + TypeScript | UI components                 |
| Backend  | Python FastAPI        | Unicode data, glyph rendering |
| Data     | `src/` (existing)     | CJK, Unicode, Mappings, etc.  |

> This document inventories every feature currently exposed by the `babelmap/`
> frontend + backend, and marks whether it is actually implemented (✅), only
> partially wired (⚠️), or a menu placeholder with no backend/UI (🚫).

---

## Implementation Status

| Area                        | Status                                    |
| --------------------------- | ----------------------------------------- |
| Backend REST/SSE API        | ✅ Core complete                          |
| Character grid & navigation | ✅ Complete                               |
| Expression search engine    | ✅ Complete (AST parser + SSE streaming)  |
| Edit buffer (modes, RTF)    | ✅ Complete                               |
| Save dialog (encodings/BOM) | ✅ Complete                               |
| Context menu (text editing) | ✅ Complete                               |
| Menu bar                    | ⚠️ Menu structure complete, most items 🚫 |
| Plane tabs                  | ✅ Complete (7 fixed / 17 unfiltered)     |
| Block selector              | ✅ Complete                               |
| Localization                | ✅ 7 languages                            |
| Fonts toolbar               | ⚠️ Size only; font config is placeholder  |
| Tools menu dialogs          | 🚫 Not implemented                        |
| Options menu                | 🚫 Not implemented                        |
| Bookmarks                   | 🚫 Not implemented                        |
| Help / About                | 🚫 Not implemented                        |
| Zoom (View)                 | 🚫 Menu item only                         |
| Glyph rendering (PIL)       | ✅ `/api/glyph` available; grid uses text |

---

## Backend API --- `backend/server.py`

All endpoints implemented and working. Port **18080** (`http://127.0.0.1:18080`).

| Endpoint                                         | Description                              | Status |
| ------------------------------------------------ | ---------------------------------------- | ------ |
| `GET /api/health`                                | Health check                             | ✅     |
| `GET /api/planes`                                | List Unicode planes (0–16)               | ✅     |
| `GET /api/blocks`                                | All blocks (valid planes, no surrogates) | ✅     |
| `GET /api/blocks/{plane}`                        | Blocks for a plane                       | ✅     |
| `GET /api/grid/{plane}?scroll=&filter_no_block=` | Character grid page (8×16)               | ✅     |
| `GET /api/grid/{plane}/goto/{cp}`                | Jump to codepoint (+`filter_no_block`)   | ✅     |
| `GET /api/grid/{plane}/block/{name}`             | Jump to a block by name                  | ✅     |
| `GET /api/grid/{plane}/navigate`                 | Grid navigation (page/block/plane)       | ✅     |
| `GET /api/codepoint/{cp}`                        | Codepoint info (GC, script, pinyin...)   | ✅     |
| `GET /api/glyph/{cp}?font=&size=`                | Glyph PNG as base64 (Pillow)             | ✅     |
| `GET /api/search/name?q=`                        | Unified expression search                | ✅     |
| `GET /api/search/advanced?q=`                    | Alias of `/search/name`                  | ✅     |
| `GET /api/search/name/stream`                    | SSE streaming search                     | ✅     |
| `GET /api/search/han_source`                     | CJK IRG source-reference search          | ✅     |
| `GET /api/search/properties`                     | Property autocomplete list               | ✅     |
| `GET /api/fonts`                                 | List font names                          | ✅     |
| `GET /api/convert/edit?text=&mode=`              | NCR/HTML/UCN conversion helpers          | ✅     |

---

## Frontend Components --- `frontend/src/lib/components/`

| Component                    | Purpose                                       | Status       |
| ---------------------------- | --------------------------------------------- | ------------ |
| `App.svelte`                 | Root layout, state, menu actions, search glue | ✅           |
| `MenuBar.svelte`             | Dropdown menus, submenus, ✓ states, theme     | ⚠️ see below |
| `PlaneTabs.svelte`           | Plane tab bar                                 | ✅           |
| `CharacterGrid.svelte`       | 16-col grid, reserved/nonchar/highlight       | ✅           |
| `GridHeader.svelte`          | Block title + column headers                  | ✅           |
| `NavPanel.svelte`            | Vertical slider + nav buttons (IVS disabled)  | ✅           |
| `BottomPanel.svelte`         | Block selector, AdvSearch, goto, edit buffer  | ✅           |
| `AdvSearch.svelte`           | Expression input + property autocomplete      | ✅           |
| `SearchResultsWindow.svelte` | Draggable/resizable results window            | ✅           |
| `InfoBar.svelte`             | U+XXXX char name + decimal                    | ✅           |
| `StatusBar.svelte`           | Status messages, plane/font/row info          | ✅           |
| `SaveDialog.svelte`          | Save with encoding/BOM/newline                | ✅           |
| `ContextMenu.svelte`         | Textarea edit menu (undo/case/normalize...)   | ✅           |
| `LangSwitcher.svelte`        | Language picker                               | ✅           |

---

## Expression Search --- `backend/adv_search.py`

AST parser with tokenizer, `AND / OR / NOT`, parentheses, comparison ops
(`= != >= <= > < :`), comma lists, `|` pipe boundaries for names, and
`|cc|` / `cc|` / `|cc` / `cc` wildcard semantics.

### Searchable properties

| Property              | Key            | Status | Notes                             |
| --------------------- | -------------- | ------ | --------------------------------- |
| Character Name        | `name`         | ✅     | wildcards, `\|` boundaries        |
| Formal Alias          | `formalalias`  | ✅     | from `NameAliases.txt`            |
| Unicode 1.0           | `unicode1name` | ✅     | from `UnicodeData.txt`            |
| All aliases           | `aliases`      | ✅     | name + uni1 + formal              |
| Whole words           | `wholewords`   | ✅     | meta-flag                         |
| General Category      | `gc`           | ✅     | Lu, Ll, Lo, ...                   |
| Combining Class       | `ccc`          | ✅     | 0–240                             |
| Bidi Class            | `bc`           | ✅     | L, R, AL, ...                     |
| Bidi Mirrored         | `bm`           | ✅     | bool                              |
| Decomposition Type    | `dt`           | ✅     | canonical, compat, ...            |
| Numeric Type          | `nt`           | ✅     | Decimal, Digit, Numeric           |
| Line Break            | `lb`           | ✅     | AK, AL, BB, ...                   |
| Binary Property       | `binary`       | ✅     | Dash, Math, Emoji, ...            |
| Script                | `script`       | ✅     | ISO 15924                         |
| Block                 | `block`        | ✅     | name **or** CJK shortcut          |
| Plane                 | `plane`        | ✅     | 0–16                              |
| Unicode version / age | `unicode`      | ✅     | `>=6.0`, `=5.0`                   |
| Exclude CJK UI        | `nocjkui`      | ✅     | bool                              |
| Exclude PUA           | `nopua`        | ✅     | incl. SPUA                        |
| IRG submitter         | `submitter`    | ✅     | G,H,J,K,KP,M,MY,SAT,SG,T,UK,UTC,V |
| IRG source ref        | `ref`          | ✅     | `*G0-*`, `G0-`                    |
| Exclude CJK Compat    | `nocomp`       | ✅     | bool                              |

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
> Search** box in the bottom panel.

| Item                             | Keys      | Status | Notes                                            |
| -------------------------------- | --------- | ------ | ------------------------------------------------ |
| Unicode Versions...              | ---       | ✅     | history + per-version blocks                     |
| Unicode Scripts...               | ---       | ✅     | per-script blocks (Show Blocks)                  |
| Unicode Planes...                | ---       | ✅     | per-plane stats + blocks (Show Blocks)           |
| Unicode Blocks...                | ---       | ✅     | latest blocks + assigned chars (Show Characters) |
| Mandarin (Pinyin) Lookup...      | F12       | 🚫     |                                                  |
| Cantonese (Jyutping) Lookup...   | Shift+F12 | 🚫     |                                                  |
| Han Radical Lookup...            | F11       | 🚫     |                                                  |
| Yi Radical Lookup...             | Shift+F11 | 🚫     |                                                  |
| Tangut References Lookup...      | ---       | 🚫     |                                                  |
| Emoji Lookup...                  | Shift+F8  | 🚫     |                                                  |
| Character Properties...          | F9        | 🚫     |                                                  |
| Extended Character Properties... | Shift+F9  | 🚫     |                                                  |
| Ideographic Properties...        | Ctrl+F9   | 🚫     |                                                  |
| Character History...             | ---       | 🚫     |                                                  |
| Unicode Variation Sequences...   | ---       | 🚫     |                                                  |
| Generate Core UCD Data...        | ---       | 🚫     |                                                  |
| Generate Full UCD XML Data...    | ---       | 🚫     |                                                  |
| OpenType Test Framework...       | ---       | 🚫     |                                                  |

### 4. Fonts --- ⚠️ partial

| Item                                                                                      | Keys     | Status | Notes                                          |
| ----------------------------------------------------------------------------------------- | -------- | ------ | ---------------------------------------------- |
| Single Font                                                                               | Ctrl+1   | 🚫     |                                                |
| Composite Font                                                                            | Ctrl+2   | 🚫     |                                                |
| List All Font Styles                                                                      | ---      | 🚫     |                                                |
| Legacy Font Enum                                                                          | ---      | 🚫     |                                                |
| Show Symbol Mappings                                                                      | ---      | 🚫     |                                                |
| ▸ Grid Font Size                                                                          | ---      | ⚠️     | size works only via bottom-panel numeric input |
| ├ Very Small / Small / Medium / Large / Very Large                                        | ---      | 🚫     |                                                |
| ▸ Quality                                                                                 | ---      | 🚫     |                                                |
| ├ Default / Draft / Proof / Non-antialiased / Antialiased / ClearType / ClearType Natural | ---      | 🚫     |                                                |
| Add Fonts                                                                                 | ---      | 🚫     |                                                |
| Remove Fonts                                                                              | ---      | 🚫     |                                                |
| Fonts Overview                                                                            | ---      | 🚫     |                                                |
| Font Analysis                                                                             | F7       | 🚫     |                                                |
| Font Coverage                                                                             | ---      | 🚫     |                                                |
| Font Information                                                                          | Ctrl+F7  | 🚫     |                                                |
| Export Glyphs                                                                             | ---      | 🚫     |                                                |
| Composite Mapping                                                                         | Shift+F7 | 🚫     |                                                |

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

| Item         | Status |
| ------------ | ------ |
| Add Bookmark | 🚫     |
| Manage       | 🚫     |

### 7. View

| Item                     | Keys   | Status | Notes                                                       |
| ------------------------ | ------ | ------ | ----------------------------------------------------------- |
| Zoom In                  | Ctrl++ | 🚫     | placeholder                                                 |
| Zoom Out                 | Ctrl+- | 🚫     | placeholder                                                 |
| Filter Unassigned Blocks | ---    | ✅     | ✓ indicator; on = assigned blocks only, off = all 17 planes |
| Toggle Theme             | ---    | ✅     | light/dark                                                  |

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

## Keyboard shortcuts (implemented)

| Keys                         | Action                      |
| ---------------------------- | --------------------------- |
| `F4` / `Ctrl+F4`             | Copy plain / RTF            |
| `Shift+F4` / `Ctrl+Shift+F4` | Cut plain / RTF             |
| `Shift+F5`                   | Save                        |
| `F2` / `Ctrl+G` / `Shift+F2` | Locate / Goto CP / Han      |
| `F3` / `Shift+F3`            | Next / Prev search result   |
| `Arrow` / `PgUp` / `PgDn`    | Grid navigation             |
| `Enter`                      | Add selected char to buffer |

---

## Getting Started

### 1. Install frontend dependencies

```bash
cd babelmap/frontend
npm install
```

### 2. Install backend dependencies

```bash
cd babelmap/backend
pip install -r requirements.txt
```

### 3. Start the backend (terminal 1)

```bash
python babelmap/backend/server.py
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
python -m pytest babelsoft-py/tests/ -x -q
```

---

## Tauri Build (Windows/macOS/Linux)

```bash
# Prerequisites: Rust, Node.js, Python 3
cd babelmap
npm run tauri dev    # Development with hot-reload
npm run tauri build  # Production installer
```
