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
