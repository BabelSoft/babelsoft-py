# BabelSoft Python

Python port of the BabelSoft CJK data processing tools, derived from the C++ codebase (`c/`).

## Data Sources

| Directory          | Source                              | Sync Method                                    |
| ------------------ | ----------------------------------- | ---------------------------------------------- |
| `data/babelsoft/`  | `c/CJKV/*.h`, `c/CJKV/*.cpp`        | `python tools/export_*.py`                     |
| `data/ivd/`        | <https://www.unicode.org/ivd/data/> | `python -m src.utils_.sync` -> `sync_ivd()`    |
| `data/ucd/`        | UCD                                 | `python -m src.utils_.sync` -> `sync_ucd()`    |
| `data/unihan/`     | Unihan                              | `python -m src.utils_.sync` -> `sync_unihan()` |
| `data/charts/`     | Unicode charts                      | `python -m src.utils_.sync` -> `sync_charts()` |
| `data/babelstone/` | BabelStone IDS                      | `python -m src.utils_.sync` -> `sync_ids()`    |

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

| Script                            | Purpose                                         |
| --------------------------------- | ----------------------------------------------- |
| `tools/export_cjk_flags.py`       | Export `cjk_mappings.tsv` with direction column |
| `tools/export_cjk_readings.py`    | Export `cjk_readings.tsv`                       |
| `tools/export_cjk_adjustments.py` | Export context-based simp/trad adjustments      |
| `tools/export_cjk_irg.py`         | Export IRG source references                    |
| `tools/export_cjk_radical.py`     | Export radical data                             |
| `tools/add_tsv_headers.py`        | Add/update header comments on all TSV files     |

## Languages (`src/languages/`)

Python port of `c/Languages/`. See `src/languages/__init__.py` for the full module list.

### UI 层预留 (待对接)

`TextInput` 中以下 C++ 原始代码中的 GUI 相关属性和方法已暂缓实现，待 UI 层统一对接时补回：

| C++ 原始                                     | 说明                           | 对接时需补                                     |
| -------------------------------------------- | ------------------------------ | ---------------------------------------------- |
| `STextInputMethod::strFont` / `nFontSize`    | 输入法推荐字体/字号            | `TextInputMethod` 加 `font` / `font_size` 字段 |
| `TextInput::GetFontName()` / `GetFontSize()` | 查询字体名/字号                | `TextInput` 加对应 property                    |
| `TextInput::GetCandidateLabel()`             | 候选列表标签格式化（如 "1. "） | `TextInput` 加 `get_candidate_label()`         |
| `TextInput::GetCandidateDetails()`           | 候选详情格式化（如 "U+4E2D"）  | `TextInput` 加 `get_candidate_details()`       |
| `TextInput::GetStatusString()`               | 状态人类可读字符串             | `TextInput` 加 `get_status_string()`           |

这些均为纯展示/格式化逻辑，不影响 `TextInput` 的核心输入法引擎功能（表管理、字符映射、候选列表、死键处理）。
