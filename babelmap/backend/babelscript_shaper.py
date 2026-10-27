"""BabelScript — BabelMap 自研 OpenType shaping 引擎的 Python 重写。

复刻 BabelSoft 源码里 ``BabelScript`` 的流程：
CMAP → GSUB（按 LookupList 顺序应用**每个** lookup）→ GPOS，并像 BabelMap 的
OpenType Test 对话框那样按 lookup 逐步输出。输出格式与 ``opentype.shape_trace``
（HarfBuzz）一致 —— ``stages: [{m, glyphs, depth, effective}]`` —— 前端
Shaping Trace 表格可直接渲染。

注意：BabelMap 引擎应用字体里**所有** lookup（不做 feature 过滤，等同全部 feature
开启），与 HarfBuzz 默认只激活脚本相关 feature 不同——这正是它作为对比引擎的价值。

参考源码：
- ``Main/BabelScript.cpp``：RenderGlyphsInBox / DoGlyphSubstitutions / 主循环
- ``Main/FontData.cpp``：StartSubstitution / SubstituteGlyphs / GetPositionGlyphs
- ``OpenType/GSUB.cpp`` / ``OpenType/GPOS.cpp`` / ``OpenType/GSUB_GPOS.cpp``：lookup 应用
"""

from __future__ import annotations

import io

from babelmap.backend.errors import PROBE_ERRORS

# GSUB / GPOS lookup types (OpenType spec)
GSUB_SINGLE, GSUB_MULTIPLE, GSUB_ALTERNATE, GSUB_LIGATURE = 1, 2, 3, 4
GSUB_CONTEXT, GSUB_CHAINING, GSUB_EXTENSION, GSUB_REVERSE = 5, 6, 7, 8
GPOS_SINGLE, GPOS_PAIR, GPOS_CURSIVE, GPOS_MARKBASE = 1, 2, 3, 4
GPOS_MARKLIG, GPOS_MARKMARK, GPOS_CONTEXT, GPOS_CHAIN = 5, 6, 7, 8


def _glyph(gid: int, cl: int, dx=0, dy=0, ax=0, ay=0) -> dict:
    return {"g": gid, "cl": cl, "dx": dx, "dy": dy, "ax": ax, "ay": ay, "flags": 0}


def _value(v) -> tuple:
    """GPOS ValueRecord -> (x_advance, y_advance, x_offset, y_offset) in font units."""
    if v is None:
        return (0, 0, 0, 0)
    return (
        int(getattr(v, "XAdvance", 0) or 0),
        int(getattr(v, "YAdvance", 0) or 0),
        int(getattr(v, "XPlaement", 0) or getattr(v, "XPlacement", 0) or 0),
        int(getattr(v, "YPlaement", 0) or getattr(v, "YPlacement", 0) or 0),
    )


class BabelScript:
    """Python re-implementation of BabelMap's BabelScript shaping engine."""

    def __init__(self, data: bytes, text: str, direction: str = "auto"):
        self.tt = __import__("fontTools.ttLib", fromlist=["TTFont"]).TTFont(io.BytesIO(data), lazy=False)
        self.upem = self.tt["head"].unitsPerEm or 2048
        self.order = self.tt.getGlyphOrder()
        self._gid = {name: i for i, name in enumerate(self.order)}
        self.gname = lambda g: self.order[g] if 0 <= g < len(self.order) else ".notdef"
        self.gid = lambda n: self._gid.get(n, 0)

        # CMAP: char -> gid
        self.hmtx = self.tt["hmtx"].metrics
        self.cmap = self.tt.getBestCmap()
        self.text = text
        self.direction = direction
        # glyph buffer: list of dict {g, cl, dx, dy, ax, ay}
        self.glyphs = [self._mk(self.gid(self.cmap.get(ord(ch), ".notdef")), i) for i, ch in enumerate(text)]
        self.stages: list[dict] = []
        self.feat_for_lookup: dict[int, str] = {}

    # ─────────────────────────── helpers ───────────────────────────

    def _snapshot(self):
        return [dict(g) for g in self.glyphs]

    def _stage(self, m: str, eff: bool = False, snap=None):
        self.stages.append(
            {"m": m, "glyphs": snap if snap is not None else self._snapshot(), "depth": 0, "effective": eff}
        )

    def _mk(self, gid: int, cl: int) -> dict:
        """New glyph with its hmtx advance (ax) pre-loaded."""
        name = self.gname(gid)
        adv = int(self.hmtx.get(name, (0, 0))[0] or 0)
        return _glyph(gid, cl, ax=adv)

    def _reset_advance(self, g: dict) -> None:
        """Refresh ax to the current glyph's hmtx advance (after a GSUB gid change)."""
        name = self.gname(g["g"])
        g["ax"] = int(self.hmtx.get(name, (0, 0))[0] or 0)

    def _build_feat_map(self):
        """LookupListIndex -> first feature tag (for display)."""
        self.feat_for_lookup = {}
        fl = getattr(self._gsub, "FeatureList", None)
        if fl:
            for rec in fl.FeatureRecord:
                for li in rec.Feature.LookupListIndex:
                    self.feat_for_lookup.setdefault(li, rec.FeatureTag)

    # ─────────────────────────── GSUB ───────────────────────────

    def _used_lookups(self, ot_table) -> set:
        """Lookup indices referenced by at least one feature (BabelMap walks the
        FeatureList and tags referenced lookups; orphan lookups are skipped)."""
        used: set = set()
        fl = getattr(ot_table, "FeatureList", None)
        if fl:
            for rec in fl.FeatureRecord:
                used.update(rec.Feature.LookupListIndex)
        return used

    def apply_gsub(self):
        self._gsub = self.tt["GSUB"].table
        self._build_feat_map()
        used = self._used_lookups(self._gsub)
        lookup_list = self._gsub.LookupList.Lookup
        self._stage(f"start table GSUB script tag '{self._script_tag()}'", snap=[])
        for i, lookup in enumerate(lookup_list):
            if i in used:
                self._apply_lookup(i, lookup)
        self._stage("end table GSUB", snap=[])

    def _script_tag(self):
        try:
            return self._gsub.ScriptList.ScriptRecord[0].ScriptTag
        except PROBE_ERRORS:
            return "DFLT"

    def _apply_lookup(self, index: int, lookup) -> bool:
        """Apply one lookup to the whole buffer (left to right). Emits start/end stages."""
        tag = self.feat_for_lookup.get(index, "")
        before = self._snapshot()
        self._stage(f"start lookup {index} feature '{tag}'", snap=before)
        t = lookup.LookupType
        changed = False
        # Handle extension lookups (GSUB 7 / GPOS 9): unwrap to real type
        if t == GSUB_EXTENSION:
            for st in lookup.SubTable:
                t = st.ExtensionLookupType
                changed = self._apply_gsub_subtable(t, [st.ExtSubTable]) or changed
        else:
            changed = self._apply_gsub_subtable(t, lookup.SubTable) or changed
        self._stage(f"end lookup {index}", eff=changed)
        return changed

    def _apply_gsub_subtable(self, t: int, subtables) -> bool:
        changed = False
        for st in subtables:
            if t == GSUB_SINGLE:
                changed = self._single_subst(st) or changed
            elif t == GSUB_MULTIPLE:
                changed = self._multiple_subst(st) or changed
            elif t == GSUB_ALTERNATE:
                changed = self._alternate_subst(st) or changed
            elif t == GSUB_LIGATURE:
                changed = self._ligature_subst(st) or changed
            elif t == GSUB_CONTEXT:
                changed = self._context_subst(st) or changed
            elif t == GSUB_CHAINING:
                changed = self._chaining_subst(st) or changed
            elif t == GSUB_REVERSE:
                changed = self._reverse_subst(st) or changed
        return changed

    # -- GSUB Type 1: Single substitution --
    def _single_subst(self, st) -> bool:
        changed = False
        for g in self.glyphs:
            name = self.gname(g["g"])
            if hasattr(st, "mapping") and name in st.mapping:
                g["g"] = self.gid(st.mapping[name])
                self._reset_advance(g)
                changed = True
            elif hasattr(st, "DeltaGlyphID"):
                g["g"] = self.gid(name) + st.DeltaGlyphID
                self._reset_advance(g)
                changed = True
        return changed

    # -- GSUB Type 2: Multiple substitution --
    def _multiple_subst(self, st) -> bool:
        changed = False
        out = []
        for g in self.glyphs:
            name = self.gname(g["g"])
            seq = getattr(st, "mapping", {}).get(name)
            if seq:
                for nm in seq:
                    out.append(self._mk(self.gid(nm), g["cl"]))
                changed = True
            else:
                out.append(g)
        self.glyphs = out
        return changed

    # -- GSUB Type 3: Alternate substitution (take first alternate) --
    def _alternate_subst(self, st) -> bool:
        changed = False
        for g in self.glyphs:
            name = self.gname(g["g"])
            alts = getattr(st, "alternates", {}).get(name)
            if alts:
                g["g"] = self.gid(alts[0])
                self._reset_advance(g)
                changed = True
        return changed

    # -- GSUB Type 4: Ligature substitution --
    def _ligature_subst(self, st) -> bool:
        changed = False
        out = []
        i = 0
        n = len(self.glyphs)
        while i < n:
            name = self.gname(self.glyphs[i]["g"])
            ligs = getattr(st, "ligatures", {}).get(name, [])
            matched = False
            for lig in ligs:
                comps = lig.Component
                if i + len(comps) < n and all(
                    self.gname(self.glyphs[i + k]["g"]) == comps[k] for k in range(len(comps))
                ):
                    out.append(self._mk(self.gid(lig.LigGlyph), self.glyphs[i]["cl"]))
                    i += len(comps)
                    matched = True
                    changed = True
                    break
            if not matched:
                out.append(self.glyphs[i])
                i += 1
        self.glyphs = out
        return changed

    # -- GSUB Type 5: Contextual substitution --
    def _context_subst(self, st) -> bool:
        if st.Format == 1:
            return self._ctx_run(st, "glyph", False)
        elif st.Format == 2:
            return self._ctx_run(st, "class", False)
        elif st.Format == 3:
            return self._ctx_run(st, "cov", False)
        return False

    # -- GSUB Type 6: Chaining contextual substitution --
    def _chaining_subst(self, st) -> bool:
        if st.Format == 1:
            return self._ctx_run(st, "glyph", True)
        elif st.Format == 2:
            return self._ctx_run(st, "class", True)
        elif st.Format == 3:
            return self._ctx_run(st, "cov", True)
        return False

    def _gname(self, g):
        return self.gname(g["g"])

    def _ctx_rules(self, st, kind, chain):
        """Collect rules: (backtrack, input, lookahead, subst_records, matcher, classdefs)."""
        rules = []
        if kind == "glyph":
            cov = st.Coverage.glyphs
            rset = st.ChainSubRuleSet if chain else st.SubRuleSet
            for ci, glyph in enumerate(cov):
                if ci >= len(rset) or rset[ci] is None:
                    continue
                rs = rset[ci]
                rl = rs.ChainSubRule if chain else rs.SubRule
                if not isinstance(rl, list):
                    rl = [rl]
                for rule in rl:
                    if rule is None:
                        continue
                    inp = [glyph] + list(getattr(rule, "Input", []))
                    if chain:
                        rules.append(
                            (
                                getattr(rule, "Backtrack", []),
                                inp,
                                getattr(rule, "LookAhead", []),
                                getattr(rule, "SubstLookupRecord", []),
                                "name",
                                None,
                            )
                        )
                    else:
                        rules.append(([], inp, [], getattr(rule, "SubstLookupRecord", []), "name", None))
        elif kind == "class":
            if chain:
                bcd = st.BacktrackClassDef.classDefs if hasattr(st, "BacktrackClassDef") else {}
                icd = st.InputClassDef.classDefs if hasattr(st, "InputClassDef") else {}
                lcd = st.LookAheadClassDef.classDefs if hasattr(st, "LookAheadClassDef") else {}
                for cls, sc in enumerate(st.ChainSubClassSet):
                    if sc is None:
                        continue
                    rl = sc.ChainSubClassRule
                    if not isinstance(rl, list):
                        rl = [rl]
                    for rule in rl:
                        if rule is None:
                            continue
                        inp = [cls] + list(getattr(rule, "Input", []))
                        rules.append(
                            (
                                getattr(rule, "Backtrack", []),
                                inp,
                                getattr(rule, "LookAhead", []),
                                getattr(rule, "SubstLookupRecord", []),
                                "class",
                                (bcd, icd, lcd),
                            )
                        )
            else:
                cd = st.ClassDef.classDefs
                for cls, sc in enumerate(st.SubClassSet):
                    if sc is None:
                        continue
                    rl = sc.SubClassRule
                    if not isinstance(rl, list):
                        rl = [rl]
                    for rule in rl:
                        if rule is None:
                            continue
                        inp = [cls] + list(getattr(rule, "Class", []))
                        rules.append(([], inp, [], getattr(rule, "SubstLookupRecord", []), "class", (cd,)))
        elif kind == "cov":
            if chain:
                back = [c.glyphs for c in st.BacktrackCoverage]
                inp = [c.glyphs for c in st.InputCoverage]
                look = [c.glyphs for c in st.LookAheadCoverage]
            else:
                back, inp, look = [], [c.glyphs for c in st.Coverage], []
            rules.append((back, inp, look, st.SubstLookupRecord, "cov", None))
        return rules

    def _ctx_run(self, st, kind, chain):
        rules = self._ctx_rules(st, kind, chain)
        changed = False
        i = 0
        guard = 0
        while i < len(self.glyphs) and guard < 100000:
            guard += 1
            # At each position, find the FIRST rule that matches (OpenType
            # semantics) — not "every rule scans the whole buffer".
            match = None
            for back, inp, look, recs, mkind, cds in rules:
                if self._match_ctx(i, back, inp, look, mkind, cds):
                    match = (len(inp), recs)
                    break
            if match is not None:
                inlen, recs = match
                start_len = len(self.glyphs)
                for rec in recs:
                    changed = self._nested_lookup(i + rec.SequenceIndex, rec) or changed
                end_len = len(self.glyphs)
                # Skip the whole matched segment (including any net growth from
                # nested substitutions) so freshly produced glyphs are not
                # re-scanned by the same rule — prevents runaway buffer growth.
                i += max(1, inlen + (end_len - start_len))
            else:
                i += 1
        return changed

    def _match_ctx(self, i, back, inp, look, mkind, cds):
        n = len(self.glyphs)
        if mkind == "name":
            for k, g in enumerate(inp):
                if i + k >= n or self._gname(self.glyphs[i + k]) != g:
                    return False
            for k, g in enumerate(reversed(back)):
                if i - 1 - k < 0 or self._gname(self.glyphs[i - 1 - k]) != g:
                    return False
            for k, g in enumerate(look):
                if i + len(inp) + k >= n or self._gname(self.glyphs[i + len(inp) + k]) != g:
                    return False
            return True
        if mkind == "class":
            if cds is None:
                return False
            if len(cds) == 1:
                cd = cds[0]
                for k, c in enumerate(inp):
                    if i + k >= n or cd.get(self._gname(self.glyphs[i + k]), 0) != c:
                        return False
                return True
            bcd, icd, lcd = cds
            for k, c in enumerate(inp):
                if i + k >= n or icd.get(self._gname(self.glyphs[i + k]), 0) != c:
                    return False
            for k, c in enumerate(reversed(back)):
                if i - 1 - k < 0 or bcd.get(self._gname(self.glyphs[i - 1 - k]), 0) != c:
                    return False
            for k, c in enumerate(look):
                if i + len(inp) + k >= n or lcd.get(self._gname(self.glyphs[i + len(inp) + k]), 0) != c:
                    return False
            return True
        if mkind == "cov":
            for k, cov in enumerate(inp):
                if i + k >= n or self._gname(self.glyphs[i + k]) not in cov:
                    return False
            for k, cov in enumerate(reversed(back)):
                if i - 1 - k < 0 or self._gname(self.glyphs[i - 1 - k]) not in cov:
                    return False
            for k, cov in enumerate(look):
                if i + len(inp) + k >= n or self._gname(self.glyphs[i + len(inp) + k]) not in cov:
                    return False
            return True
        return False

    # -- GSUB Type 8: Reverse chaining contextual single substitution --
    def _reverse_subst(self, st) -> bool:
        changed = False
        n = len(self.glyphs)
        for i, g in enumerate(self.glyphs):
            name = self.gname(g["g"])
            if name not in st.Substitute.glyphs:
                continue
            # backtrack
            ok = all(
                i - 1 - k >= 0 and self.gname(self.glyphs[i - 1 - k]["g"]) in cov.glyphs
                for k, cov in enumerate(st.BacktrackCoverage)
            )
            # lookahead
            ok = ok and all(
                i + 1 + k < n and self.gname(self.glyphs[i + 1 + k]["g"]) in cov.glyphs
                for k, cov in enumerate(st.LookAheadCoverage)
            )
            if ok:
                idx = st.Substitute.glyphs.index(name)
                g["g"] = self.gid(st.Substitute[idx])
                self._reset_advance(g)
                changed = True
        return changed

    def _nested_lookup(self, pos: int, rec) -> bool:
        """Apply a nested lookup (from SubstLookupRecord) starting at the given position."""
        li = rec.LookupListIndex
        if li >= len(self._gsub.LookupList.Lookup):
            return False
        nested = self._gsub.LookupList.Lookup[li]
        t = nested.LookupType
        # Contextual lookups must not recurse into other contextual lookups
        # (would loop forever). OpenType only nests non-contextual lookups here.
        if t in (GSUB_CONTEXT, GSUB_CHAINING):
            return False
        if t == GSUB_EXTENSION:
            changed = False
            for st in nested.SubTable:
                changed = self._apply_gsub_subtable(st.ExtensionLookupType, [st.ExtSubTable]) or changed
            return changed
        changed = False
        saved = self.glyphs
        if t == GSUB_MULTIPLE or t == GSUB_LIGATURE:
            name = self.gname(saved[pos]["g"])
            for st in nested.SubTable:
                if t == GSUB_MULTIPLE:
                    seq = getattr(st, "mapping", {}).get(name)
                    if seq:
                        new = [self._mk(self.gid(nm), saved[pos]["cl"]) for nm in seq]
                        self.glyphs = saved[:pos] + new + saved[pos + 1 :]
                        changed = True
                else:
                    for lig in getattr(st, "ligatures", {}).get(name, []):
                        comps = lig.Component
                        if pos + len(comps) < len(saved) and all(
                            self.gname(saved[pos + k]["g"]) == comps[k] for k in range(len(comps))
                        ):
                            self.glyphs = (
                                saved[:pos]
                                + [self._mk(self.gid(lig.LigGlyph), saved[pos]["cl"])]
                                + saved[pos + len(comps) :]
                            )
                            changed = True
                            break
        else:
            saved = self.glyphs
            res = None
            self.glyphs = [saved[pos]]
            try:
                changed = self._apply_gsub_subtable(t, nested.SubTable)
                if self.glyphs:
                    res = self.glyphs[0]
            finally:
                self.glyphs = saved
            if changed and res is not None:
                self.glyphs[pos] = res
        return changed

    # ─────────────────────────── GPOS ───────────────────────────

    def apply_gpos(self):
        if "GPOS" not in self.tt:
            return
        self._gpos = self.tt["GPOS"].table
        used = self._used_lookups(self._gpos)
        self._stage(f"start table GPOS script tag '{self._gpos_script_tag()}'", snap=[])
        for i, lookup in enumerate(self._gpos.LookupList.Lookup):
            if i not in used:
                continue
            before = self._snapshot()
            self._stage(f"start lookup {i} feature ''", snap=before)
            changed = self._apply_gpos_lookup(lookup)
            self._stage(f"end lookup {i}", eff=changed)
        self._stage("end table GPOS", snap=[])

    def _gpos_script_tag(self):
        try:
            return self._gpos.ScriptList.ScriptRecord[0].ScriptTag
        except PROBE_ERRORS:
            return "DFLT"

    def _apply_gpos_lookup(self, lookup) -> bool:
        changed = False
        t = lookup.LookupType
        for st in lookup.SubTable:
            if t == GPOS_SINGLE:
                changed = self._gpos_single(st) or changed
            elif t == GPOS_PAIR:
                changed = self._gpos_pair(st) or changed
            elif t == GPOS_MARKBASE:
                changed = self._gpos_markbase(st) or changed
            elif t == GPOS_MARKLIG:
                changed = self._gpos_marklig(st) or changed
            elif t == GPOS_MARKMARK:
                changed = self._gpos_markmark(st) or changed
            elif t in (GPOS_CONTEXT, GPOS_CHAIN):
                changed = self._gpos_context(st) or changed
        return changed

    def _apply_values(self, i: int, v) -> None:
        if v is None or i < 0 or i >= len(self.glyphs):
            return
        xa, ya, xo, yo = _value(v)
        g = self.glyphs[i]
        g["dx"] += xo
        g["dy"] += yo
        g["ax"] += xa
        g["ay"] += ya

    def _gpos_single(self, st) -> bool:
        changed = False
        if getattr(st, "Format", 1) == 1 and hasattr(st, "Value"):
            # format 1: one Value for every covered glyph
            for g in self.glyphs:
                if self.gname(g["g"]) in st.Coverage.glyphs:
                    xa, ya, xo, yo = _value(st.Value)
                    g["dx"] += xo
                    g["dy"] += yo
                    g["ax"] += xa
                    g["ay"] += ya
                    changed = True
        else:
            # format 2: per-glyph Value1/Value2 arrays (aligned with coverage)
            for g in self.glyphs:
                n = self.gname(g["g"])
                if n not in st.Coverage.glyphs:
                    continue
                idx = st.Coverage.glyphs.index(n)
                v = getattr(st, "Value", None)
                if v is None:
                    v1 = getattr(st, "Value1", []) or []
                    v = v1[idx] if idx < len(v1) else None
                xa, ya, xo, yo = _value(v)
                g["dx"] += xo
                g["dy"] += yo
                g["ax"] += xa
                g["ay"] += ya
                changed = True
        return changed

    def _gpos_pair(self, st) -> bool:
        changed = False
        if getattr(st, "Format", 1) == 1:
            # format 1: PairSet per covered first glyph
            for i in range(len(self.glyphs) - 1):
                first = self.gname(self.glyphs[i]["g"])
                if first not in st.Coverage.glyphs:
                    continue
                ci = st.Coverage.glyphs.index(first)
                if ci >= len(st.PairSet):
                    continue
                ps = st.PairSet[ci]
                if ps is None:
                    continue
                second = self.gname(self.glyphs[i + 1]["g"])
                for rec in ps.PairValueRecord:
                    if rec.SecondGlyph == second:
                        self._apply_values(i, rec.Value1)
                        self._apply_values(i + 1, rec.Value2)
                        changed = True
                        break
        else:
            # format 2: class-based Class1Record / Class2Record
            cd1 = st.ClassDef1.classDefs
            cd2 = st.ClassDef2.classDefs
            for i in range(len(self.glyphs) - 1):
                c1 = cd1.get(self.gname(self.glyphs[i]["g"]), 0)
                c2 = cd2.get(self.gname(self.glyphs[i + 1]["g"]), 0)
                if c1 >= len(st.Class1Record):
                    continue
                cr1 = st.Class1Record[c1]
                if cr1 is None or c2 >= len(cr1.Class2Record):
                    continue
                rec = cr1.Class2Record[c2]
                if rec is None:
                    continue
                self._apply_values(i, rec.Value1)
                self._apply_values(i + 1, rec.Value2)
                changed = True
        return changed

    def _gpos_markbase(self, st) -> bool:
        # mark-to-base: attach mark glyph to preceding base via anchors
        mark_names = st.MarkCoverage.glyphs
        base_names = st.BaseCoverage.glyphs
        changed = False
        for gi, g in enumerate(self.glyphs):
            name = self.gname(g["g"])
            if name not in mark_names:
                continue
            for bi in range(gi - 1, -1, -1):
                bname = self.gname(self.glyphs[bi]["g"])
                if bname in base_names:
                    mi = mark_names.index(name)
                    mr = st.MarkArray.MarkRecord[mi]
                    mcls = mr.Class
                    bi_ = base_names.index(bname)
                    anchors = st.BaseArray.BaseRecord[bi_].BaseAnchor
                    if mcls < len(anchors):
                        bx = int(getattr(anchors[mcls], "XCoordinate", 0) or 0)
                        by = int(getattr(anchors[mcls], "YCoordinate", 0) or 0)
                        mx = int(getattr(mr.MarkAnchor, "XCoordinate", 0) or 0)
                        my = int(getattr(mr.MarkAnchor, "YCoordinate", 0) or 0)
                        g["dx"] += bx - mx
                        g["dy"] += by - my
                    changed = True
                    break
        return changed

    def _gpos_marklig(self, st) -> bool:
        return False

    def _gpos_markmark(self, st) -> bool:
        # mark-to-mark: attach a mark glyph to a preceding mark via anchors
        changed = False
        mark1 = st.Mark1Coverage.glyphs
        mark2 = st.Mark2Coverage.glyphs
        for gi, g in enumerate(self.glyphs):
            name = self.gname(g["g"])
            if name not in mark1:
                continue
            for bi in range(gi - 1, -1, -1):
                bname = self.gname(self.glyphs[bi]["g"])
                if bname in mark2:
                    mi = mark1.index(name)
                    mr = st.Mark1Array.MarkRecord[mi]
                    mcls = mr.Class
                    bi_ = mark2.index(bname)
                    anchors = st.Mark2Array.Mark2Record[bi_].Mark2Anchor
                    if mcls < len(anchors):
                        bx = int(getattr(anchors[mcls], "XCoordinate", 0) or 0)
                        by = int(getattr(anchors[mcls], "YCoordinate", 0) or 0)
                        mx = int(getattr(mr.MarkAnchor, "XCoordinate", 0) or 0)
                        my = int(getattr(mr.MarkAnchor, "YCoordinate", 0) or 0)
                        g["dx"] += bx - mx
                        g["dy"] += by - my
                    changed = True
                    break
        return changed

    def _gpos_context(self, st) -> bool:
        return False

    # ─────────────────────────── run ───────────────────────────

    def run(self) -> dict:
        self._stage("Start of shaping")
        if "GSUB" in self.tt:
            self.apply_gsub()
        if "GPOS" in self.tt:
            self.apply_gpos()
        self._stage("End of shaping", eff=True)
        final = self.glyphs
        return {
            "upem": self.upem,
            "glyph_count": len(final),
            "stages": self.stages,
            "final": final,
            "messages": [s["m"] for s in self.stages],
        }


def shape_with_babelscript(
    data: bytes,
    text: str,
    *,
    direction: str = "auto",
    script: str = "",
    language: str = "",
    features: dict | None = None,
) -> dict:
    """Shape text with BabelScript (Python re-implementation of BabelMap's OT engine)."""
    bs = BabelScript(data, text, direction)
    return bs.run()
