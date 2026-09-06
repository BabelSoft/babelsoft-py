# BabelSoft

Monorepo for the BabelSoft Unicode tooling — a Python port of the BabelMap /
BabelPad data-processing libraries, plus the cross-platform desktop apps.

## Layout

| Path                  | Contents                                                                             |
| --------------------- | ------------------------------------------------------------------------------------ |
| `babellib/`           | Shared Python library + data + tools + tests                                         |
| `babellib/babelsoft/` | The `babelsoft` package (cjkv, languages, mappings, scripts, sort, unicode, utils\_) |
| `babellib/data/`      | UCD, CJK, BabelStone, IVD, mappings, scripts data                                    |
| `babellib/tools/`     | Data export / processing scripts                                                     |
| `babellib/tests/`     | pytest suite                                                                         |
| `babelmap/`           | BabelMap app (Tauri 2 + Svelte 5 + Python FastAPI)                                   |
| `babelpad/`           | BabelPad app (skeleton)                                                              |
| `cpp-reference/`      | Original C++ BabelMap/BabelPad source (reference only)                               |

## Python package

The shared library is importable as `babelsoft.*` (code lives in
`babellib/babelsoft/`); data files resolve relative to `babellib/` through
`babelsoft.utils_.dirs.Dirs`.

## Commands

Run the test suite from the repo root:

```sh
uv run pytest
```

Run BabelMap:

```bat
babelmap\start.bat
```

Tools live under `babellib/tools/` and are run from the repo root, e.g.:

```sh
uv run python babellib/tools/export_blocks.py
```

## Platform notes

The backend is cross-platform. The OpenType Test Framework shapes with the
two Windows shaping APIs through a pair of purpose-built packages, each in a
**native** and a **Wine** flavour:

- **Uniscribe** (`uniscribe`) — native Microsoft `usp10`, via `pyusp`
  (`backend="usp10"`), Windows-only.
- **Uniscribe (Wine)** (`uniscribe_wine`) — Wine's open-source Uniscribe
  reimplementation, via `pyusp` (`backend="wineusp"`), **cross-platform** and
  with a real per-lookup trace.
- **DirectWrite (DWriteCore)** (`directwrite`) — native DWriteCore via
  `pydwshape` (`backend="dwcore"`), Windows-only (pydwshape is only shipped
  as a Windows wheel, marked `platform_system == 'Windows'` in
  `pyproject.toml`).
- **DirectWrite (Wine)** (`directwrite_wine`) — the Wine DWrite port via
  `pydwshape` (`backend="winedwrite"`). Bundled in every wheel since
  pydwshape 0.4.0 (so it runs on Windows too); `WDWRITE_LIB` overrides for
  manual builds.

`pyusp` has win/manylinux/macOS wheels so it installs everywhere; the
`/api/opentype/shape` endpoint rejects the two native (`uniscribe`,
`directwrite`) engines on non-Windows. HarfBuzz, HarfRust, BabelScript,
Graphite, ICU, FreeType and the two Wine engines run on every platform. See
`babelmap/README.md` → _Platform support — OpenType shaping engines_ for the
full table.
