# Third-party notices

`babelsoft-py` itself is released under the MIT license (see `LICENSE`).  It
contains, links against, or redistributes the following third-party work.

## Original BabelMap / BabelPad source

The Python port in `babellib/` is derived from the C++ source of **BabelMap and
BabelPad** by Andrew West (BabelStone), <https://babelstone.co.uk/Software/>.
The C++ source is *not* redistributed here; the `cpp-reference/` directory it was
ported from is not part of this repository.

## Unicode data

The application downloads and redistributes data published by the Unicode
Consortium, including the Unicode Character Database, Unihan, CLDR, the emoji
data files, the Ideographic Variation Database, and the character charts:

> Copyright © 1991-2026 Unicode, Inc. All rights reserved.
> Distributed under the Terms of Use in <https://www.unicode.org/copyright.html>.

The collation tables in `babellib/data/scripts/uca.tsv` are transcribed from
DUCET and CLDR, which are distributed under the same terms.

## BabelStone data

`babellib/data/babelstone/` carries the IDS (Ideographic Description Sequence)
data published by Andrew West at <https://www.babelstone.co.uk/>, used with the
terms stated on that site.

The Tangut, Khitan, Nushu and Yi reference tables in `babellib/data/` were
transcribed from the BabelMap/BabelPad source by the same author.

## Python packages

| Package         | Version used | License                                        |
| --------------- | ------------ | ---------------------------------------------- |
| FastAPI         | 0.141.1      | MIT                                            |
| uvicorn         | 0.52.4       | BSD-3-Clause                                   |
| Pillow          | 12.3.0       | MIT-CMU (HPND)                                 |
| uharfbuzz       | 0.56.1       | Apache-2.0                                     |
| pyharfrust2     | 0.1.0        | MIT                                            |
| fontTools       | 4.65.0       | MIT                                            |
| freetype-py     | 2.5.1        | BSD (FreeType License)                         |
| arabic-reshaper | 3.0.1        | MIT                                            |
| pyusp           | 0.6.0        | MIT                                            |
| pydwshape       | 0.4.0        | MIT                                            |
| pygraphite2     | 0.4.0        | MIT OR MPL-2.0 OR GPL-2.0-or-later             |
| pyyudit         | 0.3.0        | GPL-2.0-or-later                               |

`freetype-py` ships the FreeType library, which is distributed under the
FreeType License (FTL) or GPLv2; the FTL option applies here.

## Frozen sidecar and installer

`babelmap/backend/build_sidecar.py` freezes the backend with **PyInstaller**
(GPL-2.0-or-later with the special exception that allows building and
distributing bundled applications) and collects `pyyudit`, which is
**GPL-2.0-or-later**.  The aggregate `babelmap-backend.exe` produced that way is
therefore distributed under **GPL-2.0-or-later**; the corresponding source is
this repository plus <https://github.com/Kushim-Jiang/pyyudit>.  Everything else
in this repository, and the source tree as a whole, remains MIT.

The installer bundles the Unicode data tree described above and the WebView2
runtime is provided by Microsoft under its own terms.

## Rust and front end

| Component                     | License            |
| ----------------------------- | ------------------ |
| Tauri 2 (`@tauri-apps/*`, Rust crates) | MIT or Apache-2.0 |
| WebView2 (Microsoft)          | Microsoft terms    |
| Svelte 5                      | MIT                |
| Vite                          | MIT                |
| TypeScript                    | Apache-2.0         |

Full license texts for these packages are available from their respective
publishers; they are not reproduced here.
