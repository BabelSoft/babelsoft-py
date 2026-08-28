# babelsoft-py

Python port of the BabelSoft CJK/Unicode data processing tools, derived from the C++ codebase.
Each C++ header has been systematically mapped to its Python equivalent.

---

## Module Index

| C++ Directory | Python Package   | Status                         |
| ------------- | ---------------- | ------------------------------ |
| `CJKV/`       | `src/cjkv/`      | ✅ Complete                    |
| `Languages/`  | `src/languages/` | ✅ Complete                    |
| `Main/`       | `src/main_/`     | ✅ Logic complete; GUI skipped |
| `Mappings/`   | `src/mappings/`  | ✅ Complete                    |
| `Scripts/`    | `src/scripts/`   | ✅ Complete                    |
| `Sort/`       | `src/sort/`      | ✅ Complete                    |
| `Unicode/`    | `src/unicode/`   | ✅ Complete                    |
| `OpenType/`   | —                | 🚫 Not ported (font engine)    |
| `Dialogs/`    | —                | 🚫 Not ported (GUI)            |
| `res/`        | —                | 🚫 Not ported (resources)      |

---

## 1. CJKV Module — `CJKV/` → `src/cjkv/`

### Shared base: `Lookup.h` → `lookup.py`

| C++ Method                   | Python Method                    | Notes          |
| ---------------------------- | -------------------------------- | -------------- |
| `UseUpperCaseReadings(bool)` | `use_upper_case_readings(value)` | ✅ Classmethod |
| `IsUpperCaseReadings()`      | `is_upper_case_readings()`       | ✅             |
| `UseToneNumbers(bool)`       | `use_tone_numbers(value)`        | ✅             |
| `IsToneNumbers()`            | `is_tone_numbers()`              | ✅             |
| `ConvertTones(bool)`         | `convert_tones(value)`           | ✅             |
| `IsConvertTones()`           | `is_convert_tones()`             | ✅             |

### `CJK.h` → `cjk.py`

| C++ Method                                     | Python Method / Attribute                | Notes                                               |
| ---------------------------------------------- | ---------------------------------------- | --------------------------------------------------- |
| `HasIvs(ch32)`                                 | `CJK(cp).has_ivs()`                      | ✅ Instance method on `CJK` subclass of `CodePoint` |
| `IsCJKIdeograph(ch, compat)`                   | `CJK(cp).is_cjk_ideograph(compat)`       | ✅                                                  |
| `IsCJKUnifiedIdeograph(ch)`                    | `CJK(cp).is_cjk_ideograph()`             | ✅ `compat=False` default                           |
| `IsCJKCompatibilityIdeograph(ch)`              | `CJK(cp).is_cjk_ideograph(True)`         | ✅                                                  |
| `GetEquivalentIdeograph(block, ch)`            | `CJK(cp).to_equivalent()`                | ✅ Returns `CJK` or `None`                          |
| `ConvertToSimplified(ch32&)`                   | `CJK(cp).to_simplified()`                | ✅ Returns `CJK` or `None`                          |
| `ConvertToTraditional(ch32&)`                  | `CJK(cp).to_traditional()`               | ✅ Returns `CJK` or `None`                          |
| `FilterTraditionalChinese(ch32)`               | `CJK(cp).filter_traditional()`           | ✅                                                  |
| `FilterSimplifiedChinese(ch32)`                | `CJK(cp).filter_simplified()`            | ✅                                                  |
| `GetSimplifiedMapping(ch32)`                   | `CJK._get_simplified_mapping(cp)`        | ✅ Internal                                         |
| `GetTraditionalMapping(ch32)`                  | `CJK._get_traditional_mapping(cp)`       | ✅ Internal                                         |
| `IsSource(ch32, sources, match, inverse, ...)` | `CJK(cp).is_source(sources, ...)`        | ✅                                                  |
| `GetSourceRefs(ch32)`                          | `CJK(cp).source_refs()`                  | ✅                                                  |
| `FindSourceRef(str, exact)`                    | `CJK.find_source_ref(ref, exact)`        | ✅                                                  |
| `GetSourceRef(ch32, source)`                   | `CJK(cp).get_source_ref(source)`         | ✅                                                  |
| `GetIDS(ch32)`                                 | `CJK(cp).ids_babelsoft()`                | ✅ Returns `IDSInfo`                                |
| `GetRadicalForCodepoint(block, ch, bNext)`     | `CJK.get_radical_glyph(index)`           | ⚠️ Different signature; Python uses index-based     |
| `GetPrimaryRadicalStroke(ch32, ...)`           | `CJK(cp).primary_radical_stroke()`       | ✅ Returns `RS` object                              |
| `GetAllRadicalStrokes(ch32)`                   | `CJK(cp).radical_strokes()`              | ✅ Returns `list[RS]`                               |
| `GetCodepoint(block, ch16)`                    | `CJK.get_codepoint(block, ch16)`         | ✅                                                  |
| `FindIdeographsForRadical(rad, flag, n, ...)`  | `CJK.find_ideographs_for_radical(...)`   | ✅                                                  |
| `IsIVS(ch32)`                                  | `CJK(cp).has_ivs()`                      | ✅                                                  |
| `IsTraditional(ch32)`                          | `CJK(cp).is_traditional()`               | ✅                                                  |
| `IsSimplified(ch32)`                           | `CJK(cp).is_simplified()`                | ✅                                                  |
| `IsXinzixing(ch32)`                            | `CJK(cp).is_xinzixing()`                 | ✅                                                  |
| `IsJiuzixing(ch32)`                            | `CJK(cp).is_jiuzixing()`                 | ✅                                                  |
| `IsShinjitai(ch32)`                            | `CJK(cp).is_shinjitai()`                 | ✅                                                  |
| `IsKyujitai(ch32)`                             | `CJK(cp).is_kyujitai()`                  | ✅                                                  |
| `IsPinyin(ch32)`                               | `CJK(cp).is_pinyin()`                    | ✅                                                  |
| `IsJyutping(ch32)`                             | `CJK(cp).is_jyutping()`                  | ✅                                                  |
| `IsZhuang(ch32)`                               | `CJK(cp).is_zhuang()`                    | ✅                                                  |
| `IsYaleKorean(ch32)`                           | `CJK(cp).is_yale_korean()`               | ✅                                                  |
| `IsQuocNgu(ch32)`                              | `CJK(cp).is_quoc_ngu()`                  | ✅                                                  |
| `ConvertToShinjitai(ch32&)`                    | `CJK(cp).to_shinjitai()`                 | ✅ Returns `CJK` or `None`                          |
| `ConvertToKyujitai(ch32&)`                     | `CJK(cp).to_kyujitai()`                  | ✅ Returns `CJK` or `None`                          |
| `ConvertToXinzixing(ch32&)`                    | `CJK(cp).to_xinzixing()`                 | ✅ Returns `CJK` or `None`                          |
| `ConvertToJiuzixing(ch32&)`                    | `CJK(cp).to_jiuzixing()`                 | ✅ Returns `CJK` or `None`                          |
| `AdjustSimplified(chPrev, ch&, chNext)`        | `CJK(cp).adjust_simplified(prev, next)`  | ✅                                                  |
| `AdjustTraditional(chPrev, ch&, chNext)`       | `CJK(cp).adjust_traditional(prev, next)` | ✅                                                  |
| `GetMappings(ch, chTrad, chSimpCN, chSimpJP)`  | `CJK(cp).get_mappings()`                 | ✅ Returns `(trad, simp, jp)`                       |
| `GetXmlData(ch, indent)`                       | `CJK(cp).get_xml_data(indent)`           | ✅                                                  |
| `GetRadicalGlyph(index)`                       | `CJK.get_radical_glyph(index)`           | ✅                                                  |
| `GetRadicalNumber(index)`                      | `CJK.get_radical_number(index)`          | ✅                                                  |
| `GetRadicalFlag(index)`                        | `CJK.get_radical_flag(index)`            | ✅                                                  |

### `Jyutping.h` → `jyutping.py`

| C++ Method                              | Python Method                             | Notes |
| --------------------------------------- | ----------------------------------------- | ----- |
| `FindJyutping(nPinyin, nTone, nFilter)` | `find_jyutping(label, tone, filter_mode)` | ✅    |
| `GetJyutpingReading(str, index)`        | `get_reading_label(index)`                | ✅    |
| `GetJyutpingForChar(block, ch, ...)`    | `get_jyutping_for_char(cp, ...)`          | ✅    |

### `Korean.h` → `korean.py`

| C++ Method                                              | Python Method                        | Notes |
| ------------------------------------------------------- | ------------------------------------ | ----- |
| `GetKoreanForChar(block, ch, ...)`                      | `get_korean_for_char(cp)`            | ✅    |
| `GetHangulDecomposition(chSyl, chLead, chVow, chTrail)` | `get_hangul_decomposition(cp)`       | ✅    |
| `ComposeHangul(chLead, chVow, chTrail)`                 | `compose_hangul(lead, vowel, trail)` | ✅    |
| `GetHangulName(ch, fullName)`                           | `get_hangul_name(cp, full_name)`     | ✅    |
| `GetJamoShortName(ch)`                                  | `get_jamo_short_name(cp)`            | ✅    |
| `GetCharacterForShortName(str)`                         | `get_character_for_short_name(name)` | ✅    |
| `IsHangulOpenSyllable(ch)`                              | `is_hangul_open_syllable(cp)`        | ✅    |
| `GetFirstJamoForLetter(ch)`                             | `get_first_jamo_for_letter(cp)`      | ✅    |
| `GetLastJamoForLetter(ch)`                              | `get_last_jamo_for_letter(cp)`       | ✅    |
| `GetHangulSyllableType(block, ch)`                      | `get_hangul_syllable_type(cp)`       | ✅    |
| `IsLeadJamo(ch)`                                        | `is_lead_jamo(cp)`                   | ✅    |
| `IsVowelJamo(ch)`                                       | `is_vowel_jamo(cp)`                  | ✅    |
| `IsTrailJamo(ch)`                                       | `is_trail_jamo(cp)`                  | ✅    |

### `Pinyin.h` → `pinyin.py`

| C++ Method                            | Python Method                           | Notes                           |
| ------------------------------------- | --------------------------------------- | ------------------------------- |
| `FindPinyin(nPinyin, nTone, nFilter)` | `find_pinyin(label, tone, filter_mode)` | ✅                              |
| `GetPinyinReading(str, index)`        | `get_reading_label(index)`              | ✅                              |
| `GetPinyinForChar(block, ch, ...)`    | `get_pinyin_for_char(cp, ...)`          | ✅                              |
| `Decomp(ch, ch1, ch2, ch3)`           | `decomp(ch)`                            | ✅ Returns `tuple[int,int,int]` |

### `Vietnamese.h` → `vietnamese.py`

| C++ Method                                    | Python Method                      | Notes                      |
| --------------------------------------------- | ---------------------------------- | -------------------------- |
| `IsVIQR(ch16)`                                | `is_viqr(ch)`                      | ✅                         |
| `GetVietnameseForChar(eCJKV, block, ch, ...)` | `get_vietnamese_for_char(cp, ...)` | ✅                         |
| `UnicodeToVIQR(ch, ch1, ch2, ch3)`            | `unicode_to_viqr(ch)`              | ✅ Returns 1–3 char string |
| `VIQRToUnicode(ch&, ch1, ch2, ch3)`           | `viqr_to_unicode(text)`            | ✅ Returns Unicode string  |

### `Zhuang.h` → `zhuang.py`

| C++ Method                            | Python Method              | Notes |
| ------------------------------------- | -------------------------- | ----- |
| `FindZhuang(nPinyin, nTone, nFilter)` | `find_zhuang(label, tone)` | ✅    |
| `GetZhuangReading(str, index)`        | `get_reading_label(index)` | ✅    |
| `GetZhuangForChar(block, ch, ...)`    | `get_zhuang_for_char(cp)`  | ✅    |

---

## 2. Languages Module — `Languages/` → `src/languages/`

### `Language.h` → `class_.py`

| C++ Method                                                                            | Python Method                                             | Notes                                |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------ |
| `Language(eBlock)`                                                                    | `__init__(block_start, block_end, unicode_block)`         | ✅                                   |
| `GetUnicode()`                                                                        | `unicode_block` attribute                                 | ✅                                   |
| `GetBlockStart()`                                                                     | `ch_block_start` attribute                                | ✅                                   |
| `GetBlockRange()`                                                                     | `ch_block_range` attribute                                | ✅                                   |
| `GetOutputString()`                                                                   | `get_output_string()`                                     | ✅                                   |
| `GetCharacter()`                                                                      | `get_character()`                                         | ✅                                   |
| `OnClear(reset)`                                                                      | `on_clear(reset)`                                         | ✅                                   |
| `OnChar(ch, hkl)`                                                                     | `on_char(ch)`                                             | ✅                                   |
| `OnText(str)`                                                                         | `on_text(text)`                                           | ✅                                   |
| `OnMenu(id, str)`                                                                     | —                                                         | 🚫 GUI                               |
| `DoConversion(id, pStrIn, pStrOut, nStart, nEnd, nCount1, nCount2, bNotConvertASCII)` | `do_conversion(menu_id, text_in, start, end, skip_ascii)` | ✅                                   |
| `OnInput(ch, hkl)`                                                                    | `on_input(code)`                                          | ✅ Abstract; subclass must implement |
| `OnBackspace(ch)`                                                                     | `_on_backspace(code)`                                     | ✅                                   |
| `OnNumber(ch)`                                                                        | `_on_number(code)`                                        | ✅                                   |
| `OnIgnorable(ch)`                                                                     | `_on_ignorable(code)`                                     | ✅                                   |
| `OnReturn()`                                                                          | `_on_return()`                                            | ✅                                   |
| `OnEscapeSequence(ch)`                                                                | `_on_escape_sequence(code)`                               | ✅                                   |
| `OnFinish()`                                                                          | `_on_finish()`                                            | ✅                                   |

### `LanguageDefault.h` → `default.py`

| C++ Method                                                               | Python Method                                             | Notes                                         |
| ------------------------------------------------------------------------ | --------------------------------------------------------- | --------------------------------------------- |
| `LanguageDefault()`                                                      | `Default()`                                               | ✅                                            |
| `ConfigureCaesar(nOffset, bForward)`                                     | —                                                         | 🚫 GUI config; pass params to `_apply_caesar` |
| `ConfigureTangut(eTangutReading, bTangutTones)`                          | —                                                         | 🚫 GUI config                                 |
| `ToSimplifiedChinese(str)`                                               | `to_simplified_chinese(text)`                             | ✅                                            |
| `ToTraditionalChinese(str)`                                              | `to_traditional_chinese(text)`                            | ✅                                            |
| `OnInput(ch, hkl)`                                                       | `on_input(code)`                                          | ✅                                            |
| `DoConversion(id, pStrIn, pStrOut, nStart, nEnd, nCount1, nCount2, ...)` | `do_conversion(menu_id, text_in, start, end, skip_ascii)` | ✅                                            |
| `ConvertHanToReading(pStrIn, pStrOut, nStart, nEnd, nCount, eCJKV, ...)` | `convert_han_to_reading(text, cjkv_type, all_readings)`   | ✅                                            |
| `ConvertTangutToReading(pStrIn, pStrOut, nStart, nEnd, nCount)`          | `convert_tangut_to_reading(text)`                         | ✅                                            |
| `ConvertToSimplified(pStrIn, pStrOut, nStart, nEnd, nCount)`             | (via `to_simplified_chinese`)                             | ✅                                            |
| `ConvertToTraditional(pStrIn, pStrOut, nStart, nEnd, nCount)`            | (via `to_traditional_chinese`)                            | ✅                                            |
| `ConvertToOldFormHanzi(pStrIn, pStrOut, nStart, nEnd, nCount)`           | (via `CJK.to_jiuzixing`)                                  | ✅                                            |
| `ConvertToNewFormHanzi(pStrIn, pStrOut, nStart, nEnd, nCount)`           | (via `CJK.to_xinzixing`)                                  | ✅                                            |
| `ConvertToOldFormKanji(pStrIn, pStrOut, nStart, nEnd, nCount)`           | (via `CJK.to_kyujitai`)                                   | ✅                                            |
| `ConvertToNewFormKanji(pStrIn, pStrOut, nStart, nEnd, nCount)`           | (via `CJK.to_shinjitai`)                                  | ✅                                            |
| `ConvertToVIQR(pStrIn, pStrOut, nStart, nEnd, nCount)`                   | `convert_to_viqr(text)`                                   | ✅                                            |
| `ConvertFromVIQR(pStrIn, pStrOut, nStart, nEnd, nCount)`                 | `convert_from_viqr(text)`                                 | ✅                                            |
| `ConvertToKatakana(pStrIn, pStrOut, nStart, nEnd, nCount)`               | `_convert_hiragana_to_katakana(text)`                     | ✅ Internal                                   |
| `ConvertToHiragana(pStrIn, pStrOut, nStart, nEnd, nCount)`               | `_convert_katakana_to_hiragana(text)`                     | ✅ Internal                                   |
| `ConvertFullHalfWidth(pStrIn, pStrOut, nStart, nEnd, nCount)`            | `_convert_fullwidth_halfwidth(text)`                      | ✅ Internal                                   |
| `ConvertHangulSyllablesToLetters(pStrIn, pStrOut, nStart, nEnd, nCount)` | `_convert_hangul_to_letters(text)`                        | ✅ Internal                                   |
| `ConvertHangulLettersToSyllables(pStrIn, pStrOut, nStart, nEnd, nCount)` | `_convert_letters_to_hangul(text)`                        | ✅ Internal                                   |
| `ConvertPUAtoHKSCS(pStrIn, pStrOut, nStart, nEnd, nCount)`               | `convert_pua_to_hkscs(text)`                              | ✅                                            |
| `ConvertTypographic(pStrIn, pStrOut, nStart, nEnd, nCount)`              | `_convert_typographic(text)`                              | ✅ Internal                                   |
| `ReverseLines(pStrIn, pStrOut, nStart, nEnd, nCount)`                    | `_reverse_lines(text)`                                    | ✅ Internal                                   |
| `ApplyCaesarCipher(pStrIn, pStrOut, nStart, nEnd, nCount)`               | `_apply_caesar(text, offset, forward)`                    | ✅ Internal                                   |

### `LanguageUnicode.h` → `unicode.py`

| C++ Method                                                                     | Python Method                                                                 | Notes                                  |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------- |
| `LanguageUnicode(Registry*)`                                                   | `Unicode()`                                                                   | ✅                                     |
| `SetCasingRules(...)`                                                          | —                                                                             | 🚫 GUI config                          |
| `ToNFD(str)`                                                                   | `to_nfd(text)`                                                                | ✅ Uses `unicodedata`                  |
| `ToNFC(str)`                                                                   | `to_nfc(text)`                                                                | ✅                                     |
| `ToNFKD(str)`                                                                  | `to_nfkd(text)`                                                               | ✅                                     |
| `ToNFKC(str)`                                                                  | `to_nfkc(text)`                                                               | ✅                                     |
| `ToUpper(str)`                                                                 | `to_upper(text)`                                                              | ✅                                     |
| `ToLower(str)`                                                                 | `to_lower(text)`                                                              | ✅                                     |
| `ToTitle(str)`                                                                 | `to_title(text)`                                                              | ✅                                     |
| `FoldCase(str)`                                                                | `fold_case(text)`                                                             | ✅                                     |
| `ToggleCase(str)`                                                              | `toggle_case(text)`                                                           | ✅                                     |
| `OnInput(ch, hkl)`                                                             | `on_input(code)`                                                              | ✅                                     |
| `DoConversion(id, pStrIn, pStrOut, nStart, nEnd, nCount1, nCount2, ...)`       | `do_conversion(menu_id, text_in, start, end, ...)`                            | ✅                                     |
| `ConvertFromUnicode(pStrIn, pStrOut, nStart, nEnd, nCount, nCharRef, ...)`     | (via `convert_to_ncr` / `convert_to_ucn`)                                     | ✅                                     |
| `ConvertUnicodeToEntities(pStrIn, pStrOut, nStart, nEnd, nCount)`              | `convert_to_ncr(text)`                                                        | ✅                                     |
| `ConvertEntitiesToUnicode(pStrIn, pStrOut, nStart, nEnd, nCount)`              | `convert_from_ncr(text)`                                                      | ✅                                     |
| `ConvertNcrToUnicode(pStrIn, pStrOut, nStart, nEnd, nCount)`                   | (via `convert_from_ncr`)                                                      | ✅                                     |
| `ConvertUcnToUnicode(pStrIn, pStrOut, nStart, nEnd, nCount)`                   | `convert_from_ucn(text)`                                                      | ✅                                     |
| `ConvertUPlusToUnicode(pStrIn, pStrOut, nStart, nEnd, nCount)`                 | `convert_from_uPlus(text)`                                                    | ✅                                     |
| `ConvertToUnicodeReference(pStrIn, pStrOut, nStart, nEnd, nCount, bName, ...)` | (via `convert_to_uPlus` / `convert_to_unicode_name`)                          | ✅                                     |
| `ConvertNameToCharacter(pStrIn, pStrOut, nStart, nEnd, nCount)`                | `convert_name_to_character(text)`                                             | ✅ `\N{...}` format                    |
| `ConvertToPerlSequences(pStrIn, pStrOut, nStart, nEnd, nCount, ...)`           | `convert_to_perl_sequences(text, skip_ascii)`                                 | ✅ `\x{XXXX}` format                   |
| `ConvertFromPerlSequences(pStrIn, pStrOut, nStart, nEnd, nCount)`              | `convert_from_perl_sequences(text)`                                           | ✅                                     |
| `ConvertToUtf(pStrIn, pStrOut, nStart, nEnd, nCount, nID)`                     | (via `convert_to_utf8_hex` / `convert_to_utf16_hex` / `convert_to_utf32_hex`) | ✅                                     |
| `ConvertFromUtf8(pStrIn, pStrOut, nStart, nEnd, nCount)`                       | `convert_from_utf8_bytes(text)`                                               | ✅                                     |
| `ConvertFromUtf16(pStrIn, pStrOut, nStart, nEnd, nCount)`                      | (via `text.encode('utf-16-be')`)                                              | ✅                                     |
| `ConvertFromUtf32(pStrIn, pStrOut, nStart, nEnd, nCount)`                      | (via `text.encode('utf-32-be')`)                                              | ✅                                     |
| `ConvertToUtf8ByteCodes(pStrIn, pStrOut, nStart, nEnd, nCount, bOctal, ...)`   | `convert_to_utf8_hex(text)`                                                   | ✅                                     |
| `ConvertControlCodes(pStrIn, pStrOut, nStart, nEnd, nCount)`                   | `convert_control_codes(text)`                                                 | ✅                                     |
| `ConvertHtmlToTagCharacters(pStrIn, pStrOut, nStart, nEnd, nCount)`            | `convert_html_to_tag_characters(text)`                                        | ✅                                     |
| `ConvertToTagCharacters(pStrIn, pStrOut, nStart, nEnd, nCount)`                | `convert_html_to_tag_characters(text)`                                        | ✅                                     |
| `ConvertFromTagCharacters(pStrIn, pStrOut, nStart, nEnd, nCount)`              | `convert_from_tag_characters(text)`                                           | ✅                                     |
| `StripDiacritics(pStrIn, pStrOut, nStart, nEnd, nCount)`                       | `strip_diacritics(text)`                                                      | ✅                                     |
| `StripIgnorables(pStrIn, pStrOut, nStart, nEnd, nCount)`                       | `strip_ignorables(text)`                                                      | ✅                                     |
| `ReplaceIterationMarks(pStrIn, pStrOut, nStart, nEnd, nCount)`                 | `replace_iteration_marks(text)`                                               | ✅                                     |
| `ConvertToRegular(pStrIn, pStrOut, nStart, nEnd, nCount)`                      | —                                                                             | 🚫 Part of UI conversion pipeline      |
| `ConvertToStyled(pStrIn, pStrOut, nStart, nEnd, nCount, nID)`                  | —                                                                             | 🚫 Part of UI conversion pipeline      |
| `ConvertFromSymbols(pStrIn, pStrOut, nStart, nEnd, nCount, nID)`               | —                                                                             | 🚫 Font-specific; use `SymbolMappings` |
| `ConvertCompatibilityToUnified(pStrIn, pStrOut, nStart, nEnd, nCount)`         | `convert_cjk_compat_to_unified(text)`                                         | ✅                                     |
| `ConvertUnifiedToCompatibility(pStrIn, pStrOut, nStart, nEnd, nCount)`         | —                                                                             | 🚫 Handled by CJK module               |

### Language-specific classes

| C++ Class           | Python Class | File           | Notes                  |
| ------------------- | ------------ | -------------- | ---------------------- |
| `LanguageManchu`    | `Manchu`     | `manchu.py`    | ✅ Full implementation |
| `LanguageMongolian` | `Mongolian`  | `mongolian.py` | ✅ Full implementation |
| `LanguagePhagsPa`   | `PhagsPa`    | `phagsPa.py`   | ✅ Full implementation |
| `LanguageTibetan`   | `Tibetan`    | `tibetan.py`   | ✅ Full implementation |
| `LanguageUyghur`    | `Uyghur`     | `uyghur.py`    | ✅ Full implementation |
| `LanguageYi`        | `Yi`         | `yi.py`        | ✅ Full implementation |

Each class provides: `OnInput(ch)`, `OnClear(reset)`, `OnReturn()`, `DoConversion(id, ...)`,
`GetOutputString()`, `GetCharacter()`, and transcription tables.

`LanguageYi` additionally provides:
`GetCharacterName(strName, ch, bAddSpace)`, `GetIPA(ch)`, `GetTone(ch)`,
`FindSyllablesForRadical(radical, strokes, bAll, bFuzzy)`,
`FindRadicalStrokeForSyllable(ch, nRadical, nStrokes)`,
`GetRadicalCodePoint(radical)`.

### `TextInput.h` → `input.py`

| C++ Method                                    | Python Method                      | Notes          |
| --------------------------------------------- | ---------------------------------- | -------------- |
| `TextInput(Registry*)`                        | `Input()`                          | ✅             |
| `GetStatus(index)`                            | `get_status(index)`                | ✅             |
| `GetName(index)`                              | `get_name(index)`                  | ✅             |
| `GetFilePath(index)`                          | `get_file_path(index)`             | ✅             |
| `GetFontName(index)`                          | —                                  | 🚫 UI deferred |
| `GetFontSize(index)`                          | —                                  | 🚫 UI deferred |
| `GetTextInputCount()`                         | `input_count` (property)           | ✅             |
| `IsLoaded(index)`                             | `is_loaded(index)`                 | ✅             |
| `IsSelected(index)`                           | `is_selected(index)`               | ✅             |
| `LoadTextInputMethods()`                      | `load_methods()`                   | ✅             |
| `ReloadTextInputMethods()`                    | `reload_methods()`                 | ✅             |
| `ReloadTextInputMethod(index)`                | `reload_method(index)`             | ✅             |
| `DeleteTextInputMethod(index)`                | `delete_method(index)`             | ✅             |
| `AddTextInputMethod(tim, bLoadTables)`        | `add_method(method, load_tables)`  | ✅             |
| `ModifyTextInputMethod(index, tim)`           | `modify_method(index, method)`     | ✅             |
| `MoveTextInputMethod(index, bUp)`             | `move_method(index, up)`           | ✅             |
| `GetTextInputMethod()`                        | `current_method` (property)        | ✅             |
| `SetTextInputMethod(index)`                   | `set_method(index)`                | ✅             |
| `OnClear()`                                   | `on_clear()`                       | ✅             |
| `OnCharacterInput(ch, bCtrlAlt, strResult)`   | `on_character_input(ch, ctrl_alt)` | ✅             |
| `IsEmpty()`                                   | `is_empty` (property)              | ✅             |
| `GetCandidateCount()`                         | `candidate_count` (property)       | ✅             |
| `GetCandidateList()`                          | `candidate_list` (property)        | ✅             |
| `SetCandidateOffset(offset)`                  | `set_candidate_offset(offset)`     | ✅             |
| `GetCandidateLabel(index, candidate, bWhole)` | —                                  | 🚫 UI deferred |
| `GetCandidateDetails(candidate)`              | —                                  | 🚫 UI deferred |
| `GetCandidateResult(candidate)`               | `get_candidate_result(n)`          | ✅             |
| `IsDeadkey()`                                 | `is_deadkey` (property)            | ✅             |
| `IsShiftkey()`                                | `is_shiftkey` (property)           | ✅             |
| `ClearDeadkey()`                              | `clear_deadkey()`                  | ✅             |
| `ClearShiftkey()`                             | `clear_shiftkey()`                 | ✅             |
| `GetStatusString(index)`                      | —                                  | 🚫 UI deferred |

---

## 3. Main Module — `Main/` → `src/main_/`

### `BabelString.h` → `babel_string.py`

| C++ Method                                                                   | Python Method                                   | Notes                         |
| ---------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------- |
| `NumberOfCharacters(str, nStart, nEnd)`                                      | `number_of_characters(text)`                    | ✅                            |
| `Codepoints(str)`                                                            | `codepoints(text)` (returns list)               | ✅                            |
| `FromCodepoints(list)`                                                       | `from_codepoints(cps)`                          | ✅                            |
| `GoStartOfLine(str, pos)`                                                    | `go_start_of_line(text, pos)`                   | ✅                            |
| `GoEndOfLine(str, pos)`                                                      | `go_end_of_line(text, pos)`                     | ✅                            |
| `Goto(pStr, nGoto)`                                                          | —                                               | 🚫 Trivial index-based goto   |
| `Go(str, pos)`                                                               | —                                               | 🚫 Trivial; use pos directly  |
| `GoLeft(str, pos)`                                                           | `go_left(text, pos)`                            | ✅                            |
| `GoRight(str, pos)`                                                          | `go_right(text, pos)`                           | ✅                            |
| `GoUp(str, pos)`                                                             | `go_up(text, pos)`                              | ✅                            |
| `GoDown(str, pos)`                                                           | `go_down(text, pos)`                            | ✅                            |
| `IsLineBreak(str, pos, len, bBefore)`                                        | `is_line_break(cp)`                             | ✅                            |
| `DeleteLineBreak(str, pos, len, bBefore)`                                    | `delete_line_break(text, pos, before)`          | ✅                            |
| `GetScript(str)`                                                             | —                                               | 🚫 Use `Unicode.get_script()` |
| `GetNextWord(str, lineLen, pos, strWord, wordLen, eScript, nDigits, bMixed)` | `get_next_word(text, pos)`                      | ✅                            |
| `GotoNextWord(str, pos, nDefault)`                                           | `goto_next_word(text, pos)`                     | ✅                            |
| `GotoPrevWord(str, pos, nDefault)`                                           | `goto_prev_word(text, pos)`                     | ✅                            |
| `GotoStartOfGraphemeCluster(str, pos, nStartOfRun)`                          | `goto_start_of_grapheme_cluster(text, pos)`     | ✅                            |
| `GotoEndOfGraphemeCluster(str, len, pos, nEndOfRun)`                         | `goto_end_of_grapheme_cluster(text, pos)`       | ✅                            |
| `SelectWord(str, pos, nStartSel, nEndSel)`                                   | `select_word(text, pos)`                        | ✅                            |
| `NumberOfCharacters(str, nStart, nEnd)`                                      | `number_of_characters(text)`                    | ✅                            |
| `AdvanceCharacters(str, nStart, nEnd, nAdvance)`                             | `advance_characters(text, start, end, advance)` | ✅                            |
| `ExtractPara(strText, strPara, nStartPos, nEndPos, nParaLen)`                | `extract_para(text, start_pos)`                 | ✅                            |
| `ExtractRun(strPara, nParaLen, strRun, nRunStart, nRunLen, ss, ...)`         | —                                               | 🚫 GUI rendering              |
| `DoLineWrap(str, nStartPos, nRunLength, bStartOfLine)`                       | —                                               | 🚫 GUI rendering              |
| `FindTagSequence(pString, nLength, nStart)`                                  | —                                               | 🚫 OpenType tag processing    |
| `CPtoX(pSSA, pBabelScript, nCharacter, bTrailingEdge, bCodepoints)`          | —                                               | 🚫 GUI glyph positioning      |
| `XtoCP(pSSA, pBabelScript, nPosition, nTrailingEdge)`                        | —                                               | 🚫 GUI glyph positioning      |
| `GetBefore(pStr, ch32, pos)`                                                 | `get_before(text, index)`                       | ✅                            |
| `GetAfter(pStr, ch32, pos)`                                                  | `get_after(text, index)`                        | ✅                            |
| `PeekAt(str, nLength, nPos)`                                                 | `peek_at(text, pos)`                            | ✅                            |
| `GetSafeAt(str, nLength, nPos)`                                              | `get_safe_at(text, pos)`                        | ✅                            |
| `GetAt(pStr, ch32, nPos)`                                                    | `get_at(text, index)`                           | ✅                            |
| `GetAt(pStr, nLen, nPos)`                                                    | `get_at(text, index)`                           | ✅                            |
| `Get16At(str, nPos)`                                                         | `get16_at(text, pos)`                           | ✅                            |
| `Get32At(str, nPos)`                                                         | `get32_at(text, pos)`                           | ✅                            |
| `RemoveDuplicates(str)`                                                      | `remove_duplicates(text)`                       | ✅                            |
| `GetLength(str)`                                                             | `get_length(text)`                              | ✅                            |
| `GetLength(str, nPos)`                                                       | `get_length(text, pos)`                         | ✅                            |
| `GetCodepoints(str)`                                                         | `codepoints(text)` (returns list)               | ✅                            |
| `GetBytes(str)`                                                              | `get_bytes(text)`                               | ✅                            |
| `Left(str, nPos)`                                                            | `left(text, count)`                             | ✅                            |
| `Mid(pStr, nStart, nChars)`                                                  | `mid(text, start, count)`                       | ✅                            |
| `Right(pStr, nPos)`                                                          | `right(text, count)`                            | ✅                            |
| `ReplaceAt(pStr, nPos, chReplace1, chReplace2)`                              | `replace_at(text, pos, ch1, ch2)`               | ✅                            |
| `SetAt(pStr, nPos, ch32)`                                                    | `set_at(text, pos, ch)`                         | ✅                            |
| `Set16At(pStr, nPos, ch16)`                                                  | `set_at(text, pos, ch)`                         | ✅                            |
| `Set32At(pStr, nPos, ch32)`                                                  | `set_at(text, pos, ch)`                         | ✅                            |
| `InsertUniqueInOrder(pStr, ch16)`                                            | `insert_unique_in_order(text, ch)`              | ✅                            |
| `Insert16(pStr, nPos, ch16)`                                                 | `insert_at(text, pos, insert)`                  | ✅                            |
| `Insert32(pStr, nPos, ch32)`                                                 | `insert_at(text, pos, insert)`                  | ✅                            |
| `Insert(pStr, nPos, strInsert)`                                              | `insert_at(text, pos, insert)`                  | ✅                            |
| `Delete(pStr, nPos, nChars)`                                                 | `delete_at(text, pos, count)`                   | ✅                            |
| `Backspace(str, nPos)`                                                       | `backspace(text, pos)` (returns `(text, pos)`)  | ✅                            |
| `Assign16(str, ch16)`                                                        | `assign_scalar(ch)`                             | ✅                            |
| `Assign32(str, ch32)`                                                        | `assign_scalar(ch)`                             | ✅                            |
| `Assign(str, chHi, chLo)`                                                    | `assign_scalar(ch)`                             | ✅                            |
| `AssignScalar(str, ch32)`                                                    | `assign_scalar(ch)`                             | ✅                            |
| `Append8(str, ch16)`                                                         | `append(text, ch)`                              | ✅                            |
| `Append16(str, ch16)`                                                        | `append(text, ch)`                              | ✅                            |
| `Append32(str, ch32)`                                                        | `append(text, ch)`                              | ✅                            |
| `Append(str, chHi, chLo)`                                                    | `append(text, ch)`                              | ✅                            |
| `AppendString(str1, str2, bNewLine)`                                         | `append_string(text, other, newline)`           | ✅                            |
| `AppendScalar(str, ch32)`                                                    | `append(text, ch)`                              | ✅                            |
| `RemoveTrailingWhitespace(str)`                                              | `remove_trailing_whitespace(text)`              | ✅                            |
| `MakeReverse(str)`                                                           | `make_reverse(text)`                            | ✅                            |
| `MakeLower(str)`                                                             | `make_lower(text)`                              | ✅                            |
| `MakeUpper(str)`                                                             | `make_upper(text)`                              | ✅                            |
| `ToLower(str)`                                                               | `to_lower(text)`                                | ✅                            |
| `ToUpper(str)`                                                               | `to_upper(text)`                                | ✅                            |
| `Find(str, chFind, nStart, nEnd)`                                            | `find(text, needle, start)`                     | ✅                            |
| `FindString(pBuffer, nBufLen, strFind, nStart, nFind)`                       | `find_string(text, needle, start)`              | ✅                            |
| `FindString(strLine, strFind, nStart, nFind, nStrLen, nFindLen)`             | `find_string(text, needle, start)`              | ✅                            |
| `FindCaseFoldedString(strLine, strFind, nStart, nFind, ...)`                 | `find_case_folded_string(text, needle, start)`  | ✅                            |
| `FindStringReverse(pBuffer, nBufLen, strFind, nFind)`                        | `find_string_reverse(text, needle, start)`      | ✅                            |
| `FindStringReverse(strLine, strFind, nStart, nFind)`                         | `find_string_reverse(text, needle, start)`      | ✅                            |
| `IsStartofLine(pStrLine, strFind, nFindLen)`                                 | `is_start_of_line(text, needle, pos)`           | ✅                            |
| `IsSame(str1, str2)`                                                         | `is_same(a, b)`                                 | ✅                            |
| `IsSameWild(strTarget, strPattern, bMatchStart)`                             | `is_same_wild(target, pattern, match_start)`    | ✅                            |
| `IsMatch(pStr1, pStr2, nStart1, nStart2, nLen1, nLen2)`                      | `is_match(a, b, start1, start2, len1, len2)`    | ✅                            |
| `Compare(pStr1, pStr2, nStart1, nStart2, nLen1, nLen2)`                      | `compare(a, b)`                                 | ✅                            |
| `CompareGlyphs(pFontData, pStr1, pStr2, ...)`                                | —                                               | 🚫 Requires font data (GUI)   |
| `ReadNext(pBuffer, nPosition, nLength, bFoldCase)`                           | —                                               | 🚫 Internal to C++ iterator   |
| `Remove(strOriginal, chRemove)`                                              | `remove(text, remove_ch)`                       | ✅                            |
| `Replace(strOriginal, chOriginal, chReplace)`                                | `replace(text, old_ch, new_ch)`                 | ✅                            |
| `Count(strOriginal, chCount, nStart, nEnd)`                                  | `count(text, needle, start, end)`               | ✅                            |
| `Count(strOriginal, strCount, nStart, nEnd)`                                 | `count(text, needle, start, end)`               | ✅                            |
| `AddComma(nNumber)`                                                          | `add_comma(value)`                              | ✅                            |
| `AddComma(nNumber, nStringID)`                                               | `add_comma(value)`                              | ✅                            |
| `AddComma(strString)`                                                        | `add_comma(value)`                              | ✅                            |
| `FormatMessage(id, number)`                                                  | —                                               | 🚫 MFC resource strings       |
| `FormatMessage(strFormat, strNoun, strNouns, number)`                        | —                                               | 🚫 MFC resource strings       |
| `ConvertUCN(strOriginal)`                                                    | `convert_ucn(text)`                             | ✅                            |
| `ConvertNCR(strOriginal, bAddSpaceAfter, bDelete)`                           | `convert_ncr(text)`                             | ✅                            |
| `StringToInteger(strInteger)`                                                | `string_to_integer(text)`                       | ✅                            |
| `HexStringToUnicode(strHex)`                                                 | `hex_string_to_unicode(text)`                   | ✅                            |

### `CharList.h` → `char_list.py`

| C++ Method              | Python Method      | Notes                  |
| ----------------------- | ------------------ | ---------------------- |
| `CharList()`            | `CharList(items)`  | ✅                     |
| `Insert(ch32, bUnique)` | `insert(cp)`       | ✅ Always deduplicated |
| `Append(ch32)`          | `append(cp)`       | ✅                     |
| `Remove(ch32)`          | `remove(cp)`       | ✅                     |
| `IsInList(ch32)`        | `is_in_list(cp)`   | ✅                     |
| `Count()`               | `count` (property) | ✅                     |
| `GetAt(pos)`            | `get_at(index)`    | ✅                     |
| —                       | `to_list()`        | ✅ Python convenience  |
| —                       | `to_string()`      | ✅ Python convenience  |
| —                       | `__len__()`        | ✅ Python dunder       |
| —                       | `__contains__(cp)` | ✅ Python dunder       |
| —                       | `__iter__()`       | ✅ Python dunder       |

### `SCSU.h` → `scsu.py`

| C++ Method                       | Python Method     | Notes            |
| -------------------------------- | ----------------- | ---------------- |
| `SCSU(bStripBOM)`                | `SCSU(strip_bom)` | ✅               |
| `Encode(pGet, pPut, pCtx)`       | `encode(data)`    | ✅ Takes `bytes` |
| `Decode(pGet, pPut, pErr, pCtx)` | `decode(data)`    | ✅ Returns `str` |

### `SymbolMappings.h` → `symbol_mappings.py`

| C++ Method                     | Python Method                      | Notes |
| ------------------------------ | ---------------------------------- | ----- |
| `GetSymbolMappingForAscii(ch)` | `get_symbol_mapping_for_ascii(cp)` | ✅    |
| `GetAsciiMappingForSymbol(ch)` | `get_ascii_mapping_for_symbol(cp)` | ✅    |
| `GetSymbolFontMappingCount()`  | `get_symbol_font_mapping_count()`  | ✅    |
| `GetSymbolFontMapping(m)`      | `get_symbol_font_mapping(index)`   | ✅    |

### `PostScriptNames.h` → `postscript_names.py`

| C++ Method (Conceptual)        | Python Method                          | Notes |
| ------------------------------ | -------------------------------------- | ----- |
| (StandardNames[] table lookup) | `get_name_for_codepoint(cp)`           | ✅    |
| (Reverse lookup)               | `get_codepoint_for_name(name)`         | ✅    |
| (By glyph ID)                  | `get_name_for_glyph_id(glyph_id)`      | ✅    |
| (By glyph ID)                  | `get_codepoint_for_glyph_id(glyph_id)` | ✅    |
| (Table size)                   | `get_standard_names_count()`           | ✅    |
| (Full table)                   | `all_names()`                          | ✅    |

### GUI-Only Main Files (Not Ported)

These `Main/` files are exclusively GUI and have no Python equivalent:

`BabelRun`, `BabelScript`, `BabelDoc`, `BabelView`, `BabelCell`, `BabelPad`, `BabelMap`,
`Clipboard`, `ComboBoxPlus`, `DocData`, `DocMgrEx`, `DragButton`, `FontData`, `FontEnum`,
`HtmlViewEx`, `InputLocale`, `ListCtrlPlus`, `MainFrm`, `OleDataSourceEx`, `PlaneInfo`,
`Registry`, `RTF`, `ScreenLine`, `StaticLink`, `Toolbars`, `ToolTipCtrlEx`, `UndoRedo`,
`UniscribeEdit`, `UniScript`, `VersionInfo`, `Colours`, `File`, `ArchiveEx`, `Structures`,
`Enumerations`, `Babel`.

---

## 4. Mappings Module — `c/Mappings/` → `src/mappings/`

The C++ has 24 individual header files with hardcoded encoding tables.
Python uses a unified `Mapper` class with a `Mapper.to_unicode()` / `Mapper.from_unicode()` API and an `Encoding` enum, falling back to Python's built-in `codecs` module.

All 24 C++ headers are covered. Python additionally provides convenience wrapper classes for encodings that have no dedicated C++ header (`CP950`, `GB2312`, `GBK`, `ISO8859_2`–`ISO8859_16`).

### Direct C++ → Python mapping

| C++ Header             | Python Wrapper Class                 | Notes                                   |
| ---------------------- | ------------------------------------ | --------------------------------------- |
| `ARMSCII.h`            | `ARMSCII8`                           | ✅                                      |
| `ASCII.h`              | `ASCII`                              | ✅                                      |
| `Big5.h`               | `Big5`                               | ✅                                      |
| `BrdaRten.h`           | `BrdaRten`                           | ✅                                      |
| `ChineseSimplified.h`  | —                                    | ✅ Built-in; CJK module handles mapping |
| `ChineseTraditional.h` | —                                    | ✅ Built-in; CJK module handles mapping |
| `CP932.h`              | `CP932`                              | ✅                                      |
| `CP936.h`              | `CP936`                              | ✅                                      |
| `CP949.h`              | `CP949`                              | ✅                                      |
| `DOS.h`                | `DOSCP437`–`DOSCP869` (13 classes)   | ✅                                      |
| `EBCDIC.h`             | `EBCDIC`                             | ✅                                      |
| `GB18030.h`            | `GB18030`                            | ✅                                      |
| `HKSCS.h`              | `HKSCS`                              | ✅                                      |
| `Japanese.h`           | `EUCJP`, `ShiftJIS`                  | ✅                                      |
| `JIS.h`                | `JIS`                                | ✅                                      |
| `JIS0212.h`            | `JIS0212`                            | ✅                                      |
| `KOI8.h`               | `KOI8R`, `KOI8U`                     | ✅                                      |
| `Korean.h` (Mappings)  | `EUCKR`                              | ✅                                      |
| `KPS9566.h`            | `KPS9566`                            | ✅                                      |
| `Lao.h`                | `LaoMuleLao1`                        | ✅                                      |
| `Tamil.h`              | `TamilTAB`, `TamilTAM`, `TamilTSCII` | ✅                                      |
| `ThaiLao.h`            | `TIS620`, `Windows874`               | ✅                                      |
| `VISCII.h`             | `VISCII`                             | ✅                                      |
| `WindowsCP.h`          | `Windows1250`–`Windows1258`          | ✅ All 9 Windows codepages              |

### Python-only convenience classes (no dedicated C++ header)

| Python Class | Encoding                    | Notes                    |
| ------------ | --------------------------- | ------------------------ |
| `CP950`      | Big5 (Microsoft variant)    | ✅                       |
| `GB2312`     | Chinese simplified          | ✅ Subset of GBK/GB18030 |
| `GBK`        | Extended GB2312             | ✅ Subset of GB18030     |
| `ISO8859_2`  | Latin-2 (Central European)  | ✅                       |
| `ISO8859_3`  | Latin-3 (South European)    | ✅                       |
| `ISO8859_4`  | Latin-4 (North European)    | ✅                       |
| `ISO8859_5`  | Cyrillic                    | ✅                       |
| `ISO8859_6`  | Arabic                      | ✅                       |
| `ISO8859_7`  | Greek                       | ✅                       |
| `ISO8859_8`  | Hebrew                      | ✅                       |
| `ISO8859_9`  | Latin-5 (Turkish)           | ✅                       |
| `ISO8859_10` | Latin-6 (Nordic)            | ✅                       |
| `ISO8859_11` | Thai                        | ✅                       |
| `ISO8859_13` | Latin-7 (Baltic Rim)        | ✅                       |
| `ISO8859_14` | Latin-8 (Celtic)            | ✅                       |
| `ISO8859_15` | Latin-9 (Euro)              | ✅                       |
| `ISO8859_16` | Latin-10 (Southeast Europe) | ✅                       |

### Core API

| API                                    | Description                            |
| -------------------------------------- | -------------------------------------- |
| `Mapper.to_unicode(data, encoding)`    | Convert `bytes` → `str`                |
| `Mapper.from_unicode(text, encoding)`  | Convert `str` → `bytes`                |
| `Mapper.get_unicode_for_byte(b, enc)`  | Single byte → codepoint lookup         |
| `Mapper.get_byte_for_unicode(cp, enc)` | Codepoint → byte lookup                |
| `Mapper.register_mapping(name, table)` | Register custom byte→Unicode mapping   |
| `Encoding` enum                        | All supported encodings as enum values |

Each wrapper class provides `to_unicode(data: bytes) -> str` and `from_unicode(text: str) -> bytes`.

---

## 5. Scripts Module — `Scripts/` → `src/scripts/`

### `Hieroglyphs.h` → `hieroglyphs.py`

| C++ Method                 | Python Method                | Notes |
| -------------------------- | ---------------------------- | ----- |
| `IsEgyptianHieroglyph(ch)` | `is_egyptian_hieroglyph(ch)` | ✅    |
| `IndexForHieroglyph(ch)`   | (internal)                   | ✅    |
| `GetGardinerCatalog(ch)`   | `get_catalog(ch)`            | ✅    |
| `GetDescription(ch)`       | `get_description(ch)`        | ✅    |
| `GetCoreGlyph(ch)`         | `get_core(ch)`               | ✅    |
| `GetFunction(ch)`          | `get_function(ch)`           | ✅    |
| `GetFunctionValue(ch)`     | `get_function_value(ch)`     | ✅    |
| `GetUniKemet(ch)`          | `get_unikemet(ch)`           | ✅    |
| `GetJSesh(ch)`             | `get_jsesh(ch)`              | ✅    |
| `GetHieroglyphica(ch)`     | `get_hieroglyphica(ch)`      | ✅    |
| `GetIFAO(ch)`              | `get_ifao(ch)`               | ✅    |
| `IsNoMirror(ch)`           | `is_no_mirror(ch)`           | ✅    |
| `IsNoRotate(ch)`           | `is_no_rotate(ch)`           | ✅    |
| `GetAlternateSequence(ch)` | `get_alternate_sequence(ch)` | ✅    |

### `Khitan.h` → `khitan.py`

| C++ Method                       | Python Method                 | Notes |
| -------------------------------- | ----------------------------- | ----- |
| `IsKhitanSmallScript(ch)`        | `is_khitan_small_script(ch)`  | ✅    |
| `GetKhitanReading(ch)`           | `get_reading(ch)`             | ✅    |
| `GetKhitanMeaning(ch)`           | `get_meaning(ch)`             | ✅    |
| `GetKhitanReadingAndMeaning(ch)` | `get_reading_and_meaning(ch)` | ✅    |

### `Nushu.h` → `nushu.py`

| C++ Method                   | Python Method             | Notes |
| ---------------------------- | ------------------------- | ----- |
| `IsNushuCharacter(ch)`       | `is_nushu_character(ch)`  | ✅    |
| `GetNushuPrimaryReading(ch)` | `get_primary_reading(ch)` | ✅    |
| `GetNushuDubenReference(ch)` | `get_duben_reference(ch)` | ✅    |

### Tangut (8 headers → `tangut.py`)

#### `Tangut.h` → `Tangut` class

| C++ Method                                  | Python Method                                     | Notes |
| ------------------------------------------- | ------------------------------------------------- | ----- |
| `IsTangutIdeograph(ch)`                     | `Tangut.is_tangut_ideograph(ch)`                  | ✅    |
| `GetRadicalForCodepoint(block, ch, bNext)`  | `Tangut.get_radical_for_character(ch)`            | ✅    |
| `GetXmlData(ch, indent)`                    | `Tangut.get_xml_data(ch, indent)`                 | ✅    |
| `GetMergedSource(ch)`                       | `Tangut.get_merged_source(ch)`                    | ✅    |
| `GetRadicalStroke(ch)`                      | `Tangut.get_radical_stroke(ch)`                   | ✅    |
| `GetRadicalForCharacter(ch)`                | `Tangut.get_radical_for_character(ch)`            | ✅    |
| `GetRadicalNumber(ch)`                      | `Tangut.get_radical_number(ch)`                   | ✅    |
| `GetTotalStrokeCount(ch)`                   | `Tangut.get_total_stroke_count(ch)`               | ✅    |
| `GetAdditionalStrokeCount(ch)`              | `Tangut.get_additional_stroke_count(ch)`          | ✅    |
| `GetStrokeCountForComponent(ch)`            | `Tangut.get_stroke_count_for_component(ch)`       | ✅    |
| `GetStrokeCountForComponentNumber(nNumber)` | `Tangut.get_stroke_count_for_component_number(n)` | ✅    |
| `GetIDS(ch)`                                | `Tangut.get_ids(ch)`                              | ✅    |
| `HasVariants(ch)`                           | `Tangut.has_variants(ch)`                         | ✅    |
| `GetVariants(ch)`                           | `Tangut.get_variants(ch)`                         | ✅    |
| `GetVariant(ch, nVar)`                      | `Tangut.get_variant(ch, n_var)`                   | ✅    |
| `GetLiFanwen2008Number(ch)`                 | `Tangut.get_li_fanwen_number(ch)`                 | ✅    |
| `GetLiFanwen1997Number(ch)`                 | `Tangut.get_li_fanwen_1997_number(ch)`            | ✅    |
| `GetLiFanwenReading(ch, bTone)`             | `Tangut.get_li_fanwen_reading(ch, b_tone)`        | ✅    |
| `GetLiFanwenMeaning(ch)`                    | `Tangut.get_li_fanwen_meaning(ch)`                | ✅    |
| `GetKychanovNumber(ch)`                     | `Tangut.get_kychanov_number(ch)`                  | ✅    |
| `GetKychanovReading(ch, bTone)`             | `Tangut.get_kychanov_reading(ch, b_tone)`         | ✅    |
| `GetSofronovNumber(ch)`                     | `Tangut.get_sofronov_number(ch)`                  | ✅    |
| `GetSofronovReading(ch, bTone)`             | `Tangut.get_sofronov_reading(ch, b_tone)`         | ✅    |
| `GetNishidaNumber(ch)`                      | `Tangut.get_nishida_reference(ch)`                | ✅    |
| `GetNishidaReading(ch, bTone)`              | `Tangut.get_nishida_reading(ch, b_tone)`          | ✅    |
| `GetMiyakeReading(ch, bMiyake2012, bTone)`  | `Tangut.get_miyake_reading(ch, use_2012, b_tone)` | ✅    |
| `GetMiyakeInitial(ch)`                      | `Miyake` instance method                          | ✅    |
| `GetMiyakeTone(ch)`                         | `Miyake` instance method                          | ✅    |
| `GetMiyakeRime(ch)`                         | `Miyake` instance method                          | ✅    |
| `GetSourceName()` (virtual)                 | `get_source_name()` on each class                 | ✅    |
| `FindLiFanwen2008Ref(ref)`                  | `Tangut.find_li_fanwen_2008_ref(ref)`             | ✅    |
| `FindLiFanwen1997Ref(ref)`                  | `Tangut.find_li_fanwen_1997_ref(ref)`             | ✅    |
| `FindKychanov2006Ref(ref)`                  | `Tangut.find_kychanov_2006_ref(ref)`              | ✅    |
| `FindSofronov1968Ref(ref)`                  | `Tangut.find_sofronov_1968_ref(ref)`              | ✅    |
| `FindNishida1966Ref(ref)`                   | `Tangut.find_nishida_1966_ref(ref)`               | ✅    |

#### Source classes

Each source class (`LiFanwen`, `Kychanov`, `Sofronov`, `Nishida`, `Miyake`) provides:

| C++ Method              | Python Method           | Notes |
| ----------------------- | ----------------------- | ----- |
| `GetSourceName()`       | `get_source_name()`     | ✅    |
| `HasEntry(ch)`          | `has_entry(ch)`         | ✅    |
| `GetNumber(ch, ...)`    | `get_number(ch, ...)`   | ✅    |
| `GetReading(ch, bTone)` | `get_reading(ch, tone)` | ✅    |
| `GetToneRime(ch)`       | `get_tone_rime(ch)`     | ✅    |
| `FindReference(ref)`    | `find_reference(ref)`   | ✅    |

Additionally:

- `LiFanwen`: `get_meaning(ch)` ✅
- `Miyake`: `get_initial(ch)`, `get_tone(ch)`, `get_rime(ch)` ✅

---

## 6. Sort Module — `Sort/` → `src/sort/`

### Sorter classes

| C++ Class           | Python Class                       | Notes                                                                                                                                   |
| ------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `Sorter` (base)     | `Sorter` (ABC) + `SorterWithRange` | ✅ Base: `compare(a,b)`, `sort(items)`, `sort_key(text)`. Extended: `sort_range(items,first,last)`, `get_next_equal_range(items,start)` |
| `SorterUnicode`     | `SorterUnicode`                    | ✅                                                                                                                                      |
| `SorterHexadecimal` | `SorterHexadecimal`                | ✅                                                                                                                                      |
| `SorterLength`      | `SorterLength`                     | ✅                                                                                                                                      |
| `SorterNumeric`     | `SorterNumeric`                    | ✅                                                                                                                                      |
| `SorterGlyphs`      | `SorterGlyphs`                     | ✅                                                                                                                                      |
| `SorterCustom`      | `SorterCustom`                     | ✅                                                                                                                                      |
| `SorterUCA`         | `SorterUCA`                        | ✅                                                                                                                                      |
| `SorterWindows`     | `SorterWindows`                    | ✅                                                                                                                                      |

### Additional features

| Python API                                          | Notes                                        |
| --------------------------------------------------- | -------------------------------------------- |
| `CompareStrings.unicode(a, b, config)`              | ✅ Static helper: codepoint comparison       |
| `CompareStrings.hexadecimal(a, b, config)`          | ✅ Static helper: hex comparison             |
| `CompareStrings.length(a, b, config)`               | ✅ Static helper: length comparison          |
| `CompareStrings.numeric(a, b, config)`              | ✅ Static helper: natural numeric comparison |
| `CompareStrings.glyphs(a, b, order, config)`        | ✅ Static helper: glyph order comparison     |
| `CompareStrings.custom(a, b, custom_order, config)` | ✅ Static helper: custom order comparison    |
| `CompareStrings.uca(a, b, sort_options, config)`    | ✅ Static helper: UCA comparison             |
| `CompareStrings.windows(a, b, locale, config)`      | ✅ Static helper: locale-aware comparison    |
| `create_sorter(type, **kw)`                         | ✅ Factory: `create_sorter("numeric")` etc.  |

**C++ APIs not ported (MFC/GUI integration):**

| C++ Feature                                     | Reason                                     |
| ----------------------------------------------- | ------------------------------------------ |
| `Sorter(CBabelView*, CPtrList*, SSortOptions*)` | Requires `CBabelView*` (GUI widget)        |
| `GetParameter(CString*, bool)`                  | MFC line-parameter lifecycle               |
| `DeleteParameter(void*, bool)`                  | MFC line-parameter lifecycle               |
| `Compare(void*, void*)`                         | Opaque void-pointer model                  |
| `Sort(int firstLine, int lastLine)`             | Replaced by `SorterWithRange.sort_range()` |

---

## 7. Unicode Module — `Unicode/` → `src/unicode/`

### `core.py`

#### General properties

| C++ Method                                                                     | Python Method                       | Notes                             |
| ------------------------------------------------------------------------------ | ----------------------------------- | --------------------------------- |
| `GetCharacterName(block, ch, bAlias, bUIName, bDesignation, bAlgorithmicName)` | `get_character_name(cp)`            | ✅                                |
| `GetUnicode1Name(cp)`                                                          | `get_unicode1_name(cp)`             | ✅                                |
| `GetGeneralCategory(block, ch, eGC)`                                           | `get_general_category(cp)`          | ✅ Returns `GeneralCategory` enum |
| `GetCanonicalCombiningClass(block, ch, nCCC, bConvert255)`                     | `get_canonical_combining_class(cp)` | ✅                                |
| `GetBidiClass(block, ch, eBidiClass)`                                          | `get_bidi_class(cp)`                | ✅ Returns `BidiClass` enum       |
| `GetDecompositionType(block, ch, eDT)`                                         | `get_decomposition_type(cp)`        | ✅                                |
| `GetDecomposition(block, ch, eDT, strDec, nLen, chDecOne, bSimple)`            | `get_decomposition_mapping(cp)`     | ✅                                |
| `GetNumericType(block, ch, eNT, bUndefined)`                                   | `get_numeric_type(cp)`              | ✅                                |
| `GetNumeric(block, ch, eNT, pStrNumeral, value, bUndefined)`                   | `get_numeric_value(cp)`             | ✅                                |
| `IsDecimalDigit(ch32)`                                                         | `is_decimal_digit(cp)`              | ✅                                |
| `GetScript(cp)`                                                                | `get_script(cp)`                    | ✅                                |
| `GetScriptExtensions(cp)`                                                      | `get_script_extensions(cp)`         | ✅                                |
| `GetBlockName(cp)`                                                             | `get_block_name(cp)`                | ✅                                |
| `GetBlockRange(cp)`                                                            | `get_block_range(cp)`               | ✅                                |
| `GetEastAsianWidth(cp)`                                                        | `get_east_asian_width(cp)`          | ✅                                |
| `GetLineBreak(cp)`                                                             | `get_line_break(cp)`                | ✅                                |
| `GetVerticalOrientation(cp)`                                                   | `get_vertical_orientation(cp)`      | ✅                                |
| `GetJoiningType(cp)`                                                           | `get_joining_type(cp)`              | ✅                                |
| `GetJoiningGroup(cp)`                                                          | `get_joining_group(cp)`             | ✅                                |
| `GetBidiMirrored(cp)`                                                          | `get_bidi_mirrored(cp)`             | ✅                                |
| `GetBidiMirroringGlyph(cp)`                                                    | `get_bidi_mirroring_glyph(cp)`      | ✅                                |
| `GetBidiPairedBracket(cp)`                                                     | `get_bidi_paired_bracket(cp)`       | ✅                                |
| `GetBidiBracketType(cp)`                                                       | `get_bidi_bracket_type(cp)`         | ✅                                |

#### Case mapping

| C++ Method               | Python Method              | Notes |
| ------------------------ | -------------------------- | ----- |
| `GetSimpleUppercase(cp)` | `get_simple_uppercase(cp)` | ✅    |
| `GetSimpleLowercase(cp)` | `get_simple_lowercase(cp)` | ✅    |
| `GetSimpleTitlecase(cp)` | `get_simple_titlecase(cp)` | ✅    |
| `GetCaseFolding(cp)`     | `get_case_folding(cp)`     | ✅    |

#### Binary properties (PropList / DerivedCoreProperties)

| C++ Method                    | Python Method                    | Notes |
| ----------------------------- | -------------------------------- | ----- |
| `IsWhitespace(cp)`            | `is_whitespace(cp)`              | ✅    |
| `IsDefaultIgnorable(cp)`      | `is_default_ignorable(cp)`       | ✅    |
| `IsMath(cp)`                  | `is_math(cp)`                    | ✅    |
| `IsAlphabetic(cp)`            | `is_alphabetic(cp)`              | ✅    |
| `IsLowercase(cp)`             | `is_lowercase(cp)`               | ✅    |
| `IsUppercase(cp)`             | `is_uppercase(cp)`               | ✅    |
| `IsCaseIgnorable(cp)`         | `is_case_ignorable(cp)`          | ✅    |
| `IsCased(cp)`                 | `is_cased(cp)`                   | ✅    |
| `IsChangesWhenCasefolded(cp)` | `is_changes_when_casefolded(cp)` | ✅    |
| `IsIDStart(cp)`               | `is_id_start(cp)`                | ✅    |
| `IsIDContinue(cp)`            | `is_id_continue(cp)`             | ✅    |
| `IsXIDStart(cp)`              | `is_xid_start(cp)`               | ✅    |
| `IsXIDContinue(cp)`           | `is_xid_continue(cp)`            | ✅    |
| `IsPatternWhitespace(cp)`     | `is_pattern_whitespace(cp)`      | ✅    |
| `IsPatternSyntax(cp)`         | `is_pattern_syntax(cp)`          | ✅    |
| `IsEmoji(cp)`                 | `is_emoji(cp)`                   | ✅    |
| `IsEmojiPresentation(cp)`     | `is_emoji_presentation(cp)`      | ✅    |
| `IsEmojiModifier(cp)`         | `is_emoji_modifier(cp)`          | ✅    |
| `IsEmojiModifierBase(cp)`     | `is_emoji_modifier_base(cp)`     | ✅    |
| `IsEmojiComponent(cp)`        | `is_emoji_component(cp)`         | ✅    |
| `IsExtendedPictographic(cp)`  | `is_extended_pictographic(cp)`   | ✅    |
| `IsDash(cp)`                  | `is_dash(cp)`                    | ✅    |
| `IsDiacritic(cp)`             | `is_diacritic(cp)`               | ✅    |
| `IsExtender(cp)`              | `is_extender(cp)`                | ✅    |
| `IsHexDigit(cp)`              | `is_hex_digit(cp)`               | ✅    |
| `IsTerminalPunctuation(cp)`   | `is_terminal_punctuation(cp)`    | ✅    |
| `IsQuotationMark(cp)`         | `is_quotation_mark(cp)`          | ✅    |
| `IsSoftDotted(cp)`            | `is_soft_dotted(cp)`             | ✅    |
| `IsBidiControl(cp)`           | `is_bidi_control(cp)`            | ✅    |
| `IsJoinControl(cp)`           | `is_join_control(cp)`            | ✅    |
| `IsRegionalIndicator(cp)`     | `is_regional_indicator(cp)`      | ✅    |
| `IsLogicalOrderException(cp)` | `is_logical_order_exception(cp)` | ✅    |
| `IsNoncharacterCodePoint(cp)` | `is_noncharacter_code_point(cp)` | ✅    |
| `IsVariationSelector(cp)`     | `is_variation_selector(cp)`      | ✅    |
| `IsDeprecated(cp)`            | `is_deprecated(cp)`              | ✅    |
| `IsIDSBinaryOperator(cp)`     | `is_ids_binary_operator(cp)`     | ✅    |
| `IsIDSTrinaryOperator(cp)`    | `is_ids_trinary_operator(cp)`    | ✅    |

#### Script-specific helpers

| C++ Method                | Python Method              | Notes |
| ------------------------- | -------------------------- | ----- |
| `IsLatinLetter(ch32)`     | `is_latin_letter(cp)`      | ✅    |
| `IsGreekLetter(ch32)`     | `is_greek_letter(cp)`      | ✅    |
| `IsCyrillicLetter(ch32)`  | `is_cyrillic_letter(cp)`   | ✅    |
| `IsHebrewLetter(ch32)`    | `is_hebrew_letter(cp)`     | ✅    |
| `IsArmenianLetter(ch32)`  | `is_armenian_letter(cp)`   | ✅    |
| `IsGeorgianLetter(ch32)`  | `is_georgian_letter(cp)`   | ✅    |
| `IsBasicAlphabetic(ch32)` | `is_basic_alphabetic(cp)`  | ✅    |
| `IsArabicDigit(ch32)`     | `is_arabic_digit(cp)`      | ✅    |
| `IsFullWidthLetter(ch32)` | `is_full_width_letter(cp)` | ✅    |
| `IsFullWidthDigit(ch32)`  | `is_full_width_digit(cp)`  | ✅    |

#### CJK / IDC / Word boundary helpers

| C++ Method                              | Python Method                              | Notes                     |
| --------------------------------------- | ------------------------------------------ | ------------------------- |
| `IsCJKIdeograph(block, ch32)`           | `is_cjk_ideograph_static(cp)`              | ✅ New: static version    |
| `IsWordStarter(ch32)`                   | `is_word_starter(cp)`                      | ✅                        |
| `IsWordBoundary(chBefore, ch, chAfter)` | `is_word_boundary(before, current, after)` | ✅                        |
| `IsIdcOperand(ch)`                      | `is_idc_operand(cp)`                       | ✅ Checks GeneralCategory |
| `IsGraphemeLink(ch32)`                  | `is_grapheme_link(cp)`                     | ✅ Checks CCC + GC        |
| `IsHexDigit(ch)`                        | `is_hex_digit_char(ch)`                    | ✅                        |
| `IsDecDigit(ch)`                        | `is_dec_digit_char(ch)`                    | ✅                        |
| `IsAlphaNumeric(ch)`                    | `is_alpha_numeric(ch)`                     | ✅                        |
| `GetHexValue(nibble)`                   | `get_hex_value(nibble)`                    | ✅                        |

#### Surrogates, UTF-8, planes, blocks

| C++ Method                                                                               | Python Method                                                  | Notes                                 |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------- |
| `IsSurrogate(ch)`                                                                        | `is_surrogate(ch)`                                             | ✅                                    |
| `IsHighSurrogate(ch)`                                                                    | `is_high_surrogate(ch)`                                        | ✅                                    |
| `IsLowSurrogate(ch)`                                                                     | `is_low_surrogate(ch)`                                         | ✅                                    |
| `IsValidCodePoint(ch32)`                                                                 | `is_valid_code_point(cp)`                                      | ✅                                    |
| `CharLength(ch)`                                                                         | `char_length(ch)`                                              | ✅                                    |
| `IsNewLine(ch32)`                                                                        | `is_new_line(cp)`                                              | ✅                                    |
| `GetUTF8(ch32, bEscaped, bOctal)`                                                        | `get_utf8(cp, escaped, octal)`                                 | ✅                                    |
| `GetUnicode32FromSurrogates(chHigh, chLow)`                                              | `get_unicode32_from_surrogates(hi, lo)`                        | ✅                                    |
| `GetSurrogatesFromUnicode32(ch32, chHigh, chLow)`                                        | `get_surrogates_from_unicode32(cp)`                            | ✅                                    |
| `GetPlaneName(nPlane, bWithAbbreviation)`                                                | `get_plane_name(plane)`                                        | ✅                                    |
| `GetPlaneAbbreviation(nPlane)`                                                           | `get_plane_abbreviation(plane)`                                | ✅                                    |
| `GetPlaneStart(nPlane)`                                                                  | `get_plane_start(plane)`                                       | ✅                                    |
| `GetPlaneEnd(nPlane)`                                                                    | `get_plane_end(plane)`                                         | ✅                                    |
| `GetCharactersPerPlane(nPlane)`                                                          | `get_characters_per_plane(plane)`                              | ✅                                    |
| `GetBlocksPerPlane(nPlane)`                                                              | `get_blocks_per_plane(plane)`                                  | ✅                                    |
| `GetPlaneFromBlock(nBlock)`                                                              | `get_plane_from_block(block_name)`                             | ✅                                    |
| `IsPlaneReserved(nPlane)`                                                                | `is_plane_reserved(plane)`                                     | ✅                                    |
| `GetFirstBlockInPlane(nPlane)`                                                           | `get_first_block_in_plane(plane)`                              | ✅                                    |
| `GetLastBlockInPlane(nPlane)`                                                            | `get_last_block_in_plane(plane)`                               | ✅                                    |
| `GetNextPlane(nPlane)`                                                                   | `get_next_plane(plane)`                                        | ✅                                    |
| `GetPrevPlane(nPlane)`                                                                   | `get_prev_plane(plane)`                                        | ✅                                    |
| `GetBlockName(nBlock)`                                                                   | `get_block_name(cp)`                                           | ✅                                    |
| `GetBlockRange(nBlock, chStart, chEnd)`                                                  | `get_block_range(cp)`                                          | ✅                                    |
| `GetBlockRangeForCharacter(ch, chStart, chEnd)`                                          | `get_block_range_for_character(cp)`                            | ✅                                    |
| `GetBlockStart(nBlock)`                                                                  | `get_block_start(block_name)`                                  | ✅                                    |
| `GetBlockEnd(nBlock)`                                                                    | `get_block_end(block_name)`                                    | ✅                                    |
| `GetBlockFromName(strBlock)`                                                             | `get_block_from_name(name)`                                    | ✅                                    |
| `GetCharactersPerBlock(nBlock)`                                                          | `get_characters_per_block(block_name)`                         | ✅                                    |
| `ParseCodePoint(strCodePoint)`                                                           | `parse_code_point(text)`                                       | ✅                                    |
| `GetCharacterFromName(strName)`                                                          | `get_character_from_name(name)`                                | ✅                                    |
| `FindCharacterName(nBlock, chStart, strSearch, bForwards, bSOL, bEOL, bWholeWords, ...)` | `find_character_name(search, start_cp, forwards, whole_words)` | ✅                                    |
| `GetScriptName(nScript)`                                                                 | `get_script_name(script_idx)`                                  | ✅                                    |
| `GetScriptCode(nScript)`                                                                 | `get_script_code(script_idx)`                                  | ✅                                    |
| `GetScriptForCharacter(block, ch)`                                                       | `get_script_for_character(cp)`                                 | ✅                                    |
| `GetMajorVersionString(nVersion)`                                                        | —                                                              | 🚫 GUI; version tracked in data files |
| `GetMinorVersionString(nVersion)`                                                        | —                                                              | 🚫 GUI                                |
| `GetVersionDate(nVersion)`                                                               | —                                                              | 🚫 GUI                                |
| `GetVersionStatistics(nVersion)`                                                         | —                                                              | 🚫 GUI                                |
| `GetSampleText(block, pFontData, nMaxChars)`                                             | —                                                              | 🚫 Requires `CFontData*`              |
| `GetNamesListAlias(ch, strAlias, nIndex)`                                                | —                                                              | 🚫 Requires custom parser             |
| `GetNamesListNote(ch, strNote, nIndex)`                                                  | —                                                              | 🚫 Requires custom parser             |
| `GetNamesListXRef(ch, strXRef, nIndex)`                                                  | —                                                              | 🚫 Requires custom parser             |

#### Normalization

| C++ Method      | Python Method    | Notes |
| --------------- | ---------------- | ----- |
| `GetNFD(text)`  | `get_nfd(text)`  | ✅    |
| `GetNFC(text)`  | `get_nfc(text)`  | ✅    |
| `GetNFKD(text)` | `get_nfkd(text)` | ✅    |
| `GetNFKC(text)` | `get_nfkc(text)` | ✅    |
| `IsNFC_QC(cp)`  | `is_nfc_qc(cp)`  | ✅    |
| `IsNFD_QC(cp)`  | `is_nfd_qc(cp)`  | ✅    |
| `IsNFKC_QC(cp)` | `is_nfkc_qc(cp)` | ✅    |
| `IsNFKD_QC(cp)` | `is_nfkd_qc(cp)` | ✅    |

### `uca.py`

| C++ Struct/Function                            | Python Equivalent                | Notes |
| ---------------------------------------------- | -------------------------------- | ----- |
| `CollationEntry`                               | `CollationEntry` dataclass       | ✅    |
| `ContractionEntry`                             | `ContractionEntry` dataclass     | ✅    |
| `ContractionBase`                              | `ContractionBase` dataclass      | ✅    |
| `SortOptions`                                  | `SortOptions` dataclass          | ✅    |
| `UCA` class                                    | `UCA` class                      | ✅    |
| `collation_sort_key(text, opts)`               | `collation_sort_key(text, opts)` | ✅    |
| `collation_compare(a, b, opts)`                | `collation_compare(a, b, opts)`  | ✅    |
| `COLLATE_LESS_THAN` / `GREATER_THAN` / `EQUAL` | Constants                        | ✅    |
| `VariableWeighting` enum                       | `VariableWeighting` enum         | ✅    |
| `Locale` tailoring enum                        | `Locale` enum                    | ✅    |

### `enums.py`

| C++ Enum              | Python Enum                    | Notes |
| --------------------- | ------------------------------ | ----- |
| `EGeneralCategory`    | `GeneralCategory` (IntEnum)    | ✅    |
| `EBidiClass`          | `BidiClass` (IntEnum)          | ✅    |
| `EDecompositionType`  | `DecompositionType` (IntEnum)  | ✅    |
| `EEastAsianWidth`     | `EastAsianWidth` (IntEnum)     | ✅    |
| `ELineBreak`          | `LineBreak` (IntEnum)          | ✅    |
| `EJoiningType`        | `JoiningType` (IntEnum)        | ✅    |
| `ENumericType`        | (via `get_numeric_type`)       | ✅    |
| `EHangulSyllableType` | `HangulSyllableType` (IntEnum) | ✅    |

---

## 8. OpenType Module — `OpenType/`

**NOT ported.** 82 files implementing full OpenType font parsing (SFNT, CMAP, GLYF, GPOS, GSUB, COLR, CPAL, HEAD, HHEA, HMTX, LOCA, MAXP, NAME, OS_2, META, FontFile, FontTable, CoverageTable, ClassDefinition, and all substitution/positioning lookup types). Tightly coupled to Windows GDI/Uniscribe rendering. Not needed for Python data processing.

---

## 9. Data Sources

| Directory          | Source                                                               | Sync                                                     |
| ------------------ | -------------------------------------------------------------------- | -------------------------------------------------------- |
| `data/babelsoft/`  | Exported from `CJKV/*.h`, `CJKV/*.cpp`                               | `python tools/export_*.py`                               |
| `data/ivd/`        | <https://www.unicode.org/ivd/data/>                                  | `python -m src.utils_.sync` → `sync_ivd()`               |
| `data/unicode/`    | unicode.org/Public data (per-folder mirror, incl. UCD/Unihan/charts) | `python -m src.utils_.sync` → `sync_unicode('<folder>')` |
| `data/babelstone/` | BabelStone IDS data                                                  | `python -m src.utils_.sync` → `sync_ids()`               |
| `data/scripts/`    | Script/character data (TSV)                                          | Exported from C++ / hand-maintained                      |

`sync_unicode` takes the remote folder path (e.g. `17.0.0/ucd`, `17.0.0/ucd/unihan`,
`17.0.0/charts`, `1.1-Update`, `reconstructed/1.0.0`), downloads every file under it
into `data/unicode/<folder>/`, and skips archives/derived docs (zip / jar / gz / pdf).

The current release is selected by `Dirs.CURRENT` (default `17.0.0`, overridable
with the `UNICODE_VERSION` environment variable, e.g. `UNICODE_VERSION=18.0.0`).

The historical 1.0.0 / 1.0.1 block boundaries (they predate `DerivedAge.txt`
and carry no block info in the reconstructed `UnicodeData.txt`) live in
`data/scripts/unicode_1_0_blocks.tsv`; character counts are computed from the
reconstructed repertoire at load time.

---

## 10. Running Tests

```bash
python -m pytest tests/ -x -q
```
