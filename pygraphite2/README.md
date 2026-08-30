# pygraphite2

**SIL Graphite 文本整形引擎的跨平台 Python 包（规划蓝图）**

把 SIL 的 [graphite2](https://github.com/silnrsi/graphite)（C++ 文本布局引擎）
编译成 Python 扩展，`pip install` 即可用，跨 Windows / macOS / Linux，
**不依赖系统或 vendored DLL**。目标发布到 PyPI，多平台 wheel 由 CI 构建。

> 本文件是**建仓库前的完整蓝图**（2026-08-30 调研与 PoC 结论），照此开工即可。
> 所有"已验证"结论均来自 babelsoft-py 项目在 Windows 上的实测。

---

## 1. 目标与范围

- `pygraphite2.shape(font_bytes, text, *, direction="ltr", script=0, features=None) -> list[Glyph]`
- `pygraphite2.is_graphite_font(font_bytes) -> bool`
- `Glyph` = `NamedTuple(gid, cluster, x_advance, y_advance, x_offset, y_offset)`
- 输入字体 bytes + Unicode 文本 → 输出 Graphite 布局后的 glyph 列表（font units）。
- 无图形/字体光栅化，只做布局（与 HarfBuzz 的 `hb_shape` 定位一致）。

## 2. 背景 / 动机

babelsoft-py 的 OpenType Test Framework 需要 Graphite engine 做 shaping 引擎对比。
此前 Graphite 走两条路都不理想：

1. **vendored `graphite2.dll`**（MSYS2 1.3.14 + MinGW runtime）：仅 Windows，跨平台受阻。
2. **`uharfbuzz shape(..., shapers=["graphite2"])`**：PyPI 的 uharfbuzz wheel **均未编译
   graphite2**（实测 0.51.2 / 0.56.0 都 `RuntimeError: All shapers failed`），PyPI 也无
   graphite2 独立包。

结论：**把 graphite2 源码直接编译进 Python 扩展**是唯一彻底的跨平台方案（本包即为此）。

## 3. 技术方案

- **构建系统**：`scikit-build-core`（官方支持 CMake，天然产出多平台 wheel）+ **CMake**。
- **封装层**：**Cython**（`_core.pyx` 直接 `cimport` graphite2 C API），或纯 CPython C
  扩展（见 §4 已验证的编译命令）。
- **graphite2 集成**：git submodule 指向 `silnrsi/graphite` tag `1.3.14`
  （`git ls-remote --tags` 确认 tag 名就是 `1.3.14`）。CMake `add_subdirectory`
  编译成**静态库**，与扩展链接，无运行时 DLL。
- **API 形状**：仿 `uharfbuzz`——`Font`/`Buffer` 概念可简化成单一 `shape()` 函数。

## 4. 已验证的技术结论（Windows 本机，2026-08-30）

### 4.1 MinGW 编译 CPython 3.13 扩展（决定性 PoC ✅）

**直接链接 MSVC 的 `python313.lib`**，不需要 gendef/dlltool 生成 `libpython313.a`：

```
gcc -shared -O2 -I <python>/include _mod.c -o _mod.pyd "<python>/libs/python313.lib"
```

- 工具链：MinGW-W64 gcc 13.1.0，位于 `C:\Softwares\miktex\perl\c\bin\gcc.exe`
  （真 `x86_64-w64-mingw32`，msvcrt/posix/seh）。cmake、ninja 可用。
- Python 3.13 dev 文件齐全：`C:\Softwares\Python\py313\Include\` + `libs\python313.lib`。
- 加 `-DMS_WIN64` 会触发头文件重复定义警告（去掉即可）。
- 坑：gendef/pexports 生成的 `libpython313.a` 符号名与代码不匹配
  （`PyArg_ParseTuple_SizeT` vs `PyArg_ParseTuple`），dlltool 对 pexports def 报语法错——
  **不要走这条路，直接用 `python313.lib`**。

### 4.2 跨平台构建注意

- graphite2 是 C++（依赖 libstdc++/libc++），扩展链接需 C++ 运行时。
- Windows：可用 MSVC 或 MinGW；macOS/Linux：clang/gcc，CMake 自动处理。
- 发布 wheel 时各平台在 CI 里各自编译（GitHub Actions 矩阵），不交叉。

## 5. graphite2 API 关键坑（ctypes 移植血泪，务必遵守）

> 全部来自对 MSYS2 `libgraphite2.dll` 1.3.14 + 官方 `gr2fonttest` 的实测。

1. **`gr_make_seg` 只有 8 参数**（不是网上某些旧示例的 10 参数）：

   ```c
   gr_segment* gr_make_seg(const gr_font *font, const gr_face *face, gr_uint32 script,
                           const gr_feature_val *pFeats, gr_encform enc,
                           const void *pStart, size_t nChars, int dir);
   ```

   `enc` = `gr_encform`（`gr_utf8=1, gr_utf16=2, gr_utf32=4`）。建议传 **UTF-32 码点
   数组**（`enc=4`），`pStart` 指向数组，`nChars` = 字符数。**旧 10 参数签名参数错位，
   会得到空 segment（slots=0）**。

2. **`gr_engine_version(int *major, int *minor, int *bugfix)` 带 3 个输出指针**，
   不是"无参返回 uint32"——按后者调用必崩（写入垃圾指针）。

3. **`gr_make_face(const void* appFaceHandle, gr_get_table_fn tablefn, unsigned int opts)`
   带 table 回调**，ctypes 下容易崩 → 优先用 **`gr_make_file_face(const char *filename,
unsigned int opts)`**（从文件读，最稳）；内存数据写临时文件即可。

4. **`gr_slot_advance_X/Y` 在本构建崩**（`gr2fonttest` 也不用它们）→ 改用
   `gr_slot_origin_X/Y`（简单 getter，读 slot 坐标）+ `gr_seg_advance_X`（总宽），
   每个 glyph 的 advance 用**相邻 origin 差值**（最后一个 = `seg_advance_X − 末 origin`）。

5. **font 的 size（ppm）传 upem**（如 2048 / 1024）→ origin/advance 是 **font units**
   （与 HarfBuzz 对比统一量纲）。

6. 字体必须有 **Silf 表**（Graphite 字体，如 SIL Padauk / Charis SIL）；否则
   `gr_make_file_face` 返回 NULL。非 Graphite 字体应报清晰错误而非崩溃。

## 6. 包结构蓝图

```
pygraphite2/
├── pyproject.toml          # scikit-build-core + cython
├── CMakeLists.txt          # add_subdirectory(graphite2) + _core 扩展
├── README.md
├── src/
│   └── pygraphite2/
│       ├── __init__.py     # 公共 API（纯 Python 壳，含 docstring/类型）
│       └── _core.pyx       # Cython 封装 graphite2 C API
├── vendor/
│   └── graphite2/          # git submodule: silnrsi/graphite @ 1.3.14
└── tests/
    └── test_shape.py       # 用 §7 回归基线做 golden 测试
```

## 7. 回归基线（验证必须一致）

用 `tests/fonts/Padauk-Regular.ttf`（SIL，含 Silf 表；也可先向 babelsoft-py
`vendor/fonts/` 借）做 golden 测试。upem=1024，size 传 upem：

| 文本     | 期望 glyph（gid）                | 说明               |
| -------- | -------------------------------- | ------------------ |
| `မြန်မာ` | `[423, 326, 308, 414, 326, 385]` | 6 glyph，总宽 4644 |
| `က္က`    | `[214, 217]`                     | 2 glyph            |
| `သာဓု`   | `[354, 385, 305, 395]`           | 4 glyph            |

（这些是 babelsoft-py 里 `gr_make_file_face` + 8 参数 `gr_make_seg` + origin 差值
方案实测的输出；若封装正确应逐位一致。）

## 8. 构建 / 发布步骤

1. 本地开发：`pip install -e .`（需 CMake + 编译器；Windows 用 MSVC 或 MinGW）。
2. 本地测试：跑 `tests/test_shape.py`，对照 §7 基线。
3. CI（GitHub Actions）矩阵 `windows-latest / macos-latest / ubuntu-latest`：
   `pip install build` → `python -m build` → 上传 `dist/*.whl` 到 PyPI（Trusted
   Publishing 或 twine）。scikit-build-core 自动打平台 tag。
4. 发布前检查：`pip install pygraphite2` 在三个平台均能 `import` + `shape`。

## 9. 后端接入（babelsoft-py）

- 过渡期：`graphite_shaper.py` 的加载顺序改为
  `import pygraphite2`（跨平台）→ 失败回退 vendored DLL（Windows）→ 再失败报错。
- 稳定后：删 `babelmap/backend/vendor/graphite2/`（DLL + MinGW runtime），Graphite
  engine 全平台可用；`vendor/` 只留 `fonts/` 测试字体。
- 该包只做布局，glyph 名仍由 babelsoft-py 后端用 fontTools 补（现有逻辑不变）。

## 10. 开放问题 / 待办

- [ ] 决定封装层：Cython（推荐）vs 纯 CPython C 扩展（样板多但依赖少）。
- [ ] graphite2 1.3.14 的 CMake 参数（静态库、关掉不必要工具）在目标平台验证。
- [ ] Windows 用 MinGW 还是 MSVC 构建 wheel（scikit-build-core 两者都支持）。
- [ ] 许可证：graphite2 为 LGPL-2.1+/MPL/GPL 多许可；本包发布前确认许可证元数据。
