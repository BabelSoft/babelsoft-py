# BabelSoft Python

Python port of the BabelSoft CJK data processing tools, derived from the C++ codebase (`c/`).

## Data Sources

| Directory | Source | Sync Method |
|---|---|---|
| `data/babelsoft/` | `c/CJKV/*.h`, `c/CJKV/*.cpp` | `python tools/export_*.py` |
| `data/ivd/` | <https://www.unicode.org/ivd/data/> | `python -m src.utils_.sync` → `sync_ivd()` |
| `data/ucd/` | UCD | `python -m src.utils_.sync` → `sync_ucd()` |
| `data/unihan/` | Unihan | `python -m src.utils_.sync` → `sync_unihan()` |
| `data/charts/` | Unicode charts | `python -m src.utils_.sync` → `sync_charts()` |
| `data/babelstone/` | BabelStone IDS | `python -m src.utils_.sync` → `sync_ids()` |

## IVD / IVS

The C++ functions `Unicode::GetIdeographicVariant` and `Unicode::GetStandardizedVariantsForIVS` from `c/Unicode/Unicode.cpp` have been ported to Python in `src/cjkv/cjk.py`:

- `CJK.ivs_sequences()` — returns all IVS sequences for a given CJK character
- `CJK.get_ideographic_variant(vs_cp)` — look up a specific IVS by variation selector
- `CJKLoader.load_ivd_sequences()` — load all IVD sequences from `data/ivd/IVD_Sequences.txt`
- `CJKLoader.load_ivs_chars()` — set of all base codepoints with IVS sequences

The IVS flag (previously in `cjk_flags.tsv`) is now computed from `IVD_Sequences.txt` at load time.

## TSV Files

All TSV files in `data/babelsoft/` have header comments explaining data format, generation time, and field descriptions. Run `python tools/add_tsv_headers.py` to regenerate headers.

## Tools

| Script | Purpose |
|---|---|
| `tools/export_cjk_flags.py` | Export `cjk_mappings.tsv` with direction column |
| `tools/export_cjk_readings.py` | Export `cjk_readings.tsv` |
| `tools/export_cjk_adjustments.py` | Export context-based simp/trad adjustments |
| `tools/export_cjk_irg.py` | Export IRG source references |
| `tools/export_cjk_radical.py` | Export radical data |
| `tools/add_tsv_headers.py` | Add/update header comments on all TSV files |
