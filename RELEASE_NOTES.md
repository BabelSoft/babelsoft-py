# BabelMap 1.0.0-beta.1

First packaged **beta** of the BabelMap rebuild: a Tauri 2 + Svelte 5 desktop
front end over the Python `babelsoft` library.

## Install

Download **`BabelMap_1.0.0_x64-setup.exe`** (NSIS, 64-bit Windows, **136 MiB**)
and run it.  The installer is self-contained:

- the Python backend is frozen into a 35 MB sidecar executable
  (`babelmap-backend.exe`) — **no Python installation is required**;
- the whole Unicode data tree (Unicode 1.0 → 17.0.0; 853 MB on disk, 1971 files)
  is bundled as an application resource, so every feature works offline,
  including character history and version diffs;
- requires Windows 10/11 with the WebView2 runtime (preinstalled on Windows 11;
  the installer fetches it if missing).

The shell starts the backend on `127.0.0.1:18080`, waits for it to accept
connections, and shuts it down when the window closes.  Backend output goes to
`%LOCALAPPDATA%\com.babelstone.babelmap\logs\backend.log`.

## Beta notes

This is a beta: the installer was built locally with `babelmap\build.bat`, and CI
covers svelte-check, pytest and `cargo check` only — it does not build or run the
bundle.  BabelPad is not included and the `.tim` input-method tables are still
missing (see the limitations below).  Please report anything that breaks.

## What is in it

- Character grid over all 17 planes, 7 fixed / 17 unfiltered plane tabs, block
  selector, colour coding, glyph-mode rendering, magnifier (Ctrl+hover).
- Expression search engine (AST parser + SSE streaming), name/property/Han
  source/CJKV lookups, emoji lookup.
- Edit buffer, save dialog with encodings/BOM, context menu, bookmarks, system
  tray, full menu bar (Fonts / Options / Bookmarks / Help), 7 UI languages.
- Font tools: overview (families, scripts, coverage, axes), composite font
  mappings, font quality modes, glyph export.
- OpenType Test Framework: HarfBuzz, HarfRust, BabelScript, Graphite, ICU,
  FreeType, Yudit, and — on Windows — native Uniscribe/DWriteCore plus their
  Wine ports, with per-lookup traces.
- Unicode/character dialogs: properties (+ extended / ideographic / IVS /
  history), UCD table + UCD XML export, emoji, and five CJKV lookup dialogs.

## Known limitations

- **BabelPad is not part of this release** — `babelpad/` is still a skeleton.
- Library capabilities that are not exposed in the UI remain simplified ports:
  `.tim` input-method loading is a stub (the deadkey engine behind it is
  implemented but nothing feeds it tables). The UCA sorter now reads the bundled
  DUCET/CLDR collation tables from `babellib/data/scripts/`, and the Tibetan, Yi,
  Manchu, and Mongolian transcription tables have been ported; none of this
  makes the `.tim` input method available.
- `pyright` reports 56 warnings: all of them are missing attributes in the
  upstream type stubs of fontTools / freetype-py / uharfbuzz / Pillow, not code
  defects (see `pyrightconfig.json`).

## Building from source

```sh
uv sync
uv run python babellib/tools/sync_data.py --all    # ~850 MB, one time
uv run pytest
babelmap\build.bat                                  # sidecar + installer + launch
```

Without the data set the backend still starts and reports the problem:
`/api/health` returns `data.ok = false` with the command to run, and every data
endpoint answers `503` with the same hint.

## Verification for this release

| Check | Result |
| --- | --- |
| `pytest` | 1085 passed, 7 skipped |
| `ruff check` (E501 ignored) | clean |
| `pyright` | 0 errors, 56 stub warnings |
| `svelte-check` / `vite build` | 0 errors 0 warnings / ok |
| `cargo check` | ok |
| Packaged app | launches, spawns its sidecar, `/api/health`, `/api/blocks/0`, `/api/codepoint`, `/api/fonts/overview`, `/api/unicode/history` all `200` |
