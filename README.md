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

The backend is cross-platform, but BabelMap's OpenType Test Framework has two
**Windows-only** shaping engines:

- **DirectWrite** (`directwrite`) — backed by `pydwshape`, a Windows-only
  package (bundled DWriteCore). It carries a `platform_system == 'Windows'`
  marker in `pyproject.toml`, so it is simply skipped during install on
  Linux/macOS.
- **Uniscribe** (`uniscribe`) — drives the Windows `usp10.dll` directly.

The `/api/opentype/shape` endpoint rejects those two engines on non-Windows;
HarfBuzz, HarfRust, BabelScript, Graphite, ICU and FreeType engines remain
available on every platform. See `babelmap/README.md` → _Platform support —
OpenType shaping engines_ for the full table.
