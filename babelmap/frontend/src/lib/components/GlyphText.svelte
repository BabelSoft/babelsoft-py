<script lang="ts">
  // The edit buffer's Glyph Mode renderer — the port of `DrawSimple`.
  //
  // The original walks the text one code point at a time, asks GDI for the
  // glyph's metrics (`GGO_METRICS`) and turns them into a *cell*:
  //
  //     lsb     = gmptGlyphOrigin.x
  //     trailing= gmCellIncX - (lsb + gmBlackBoxX)
  //     pad     = max(lsb, trailing)          (lsb = ink/4 when both are < 0)
  //     cell    = pad + gmBlackBoxX + pad
  //
  // and then simply lays the cells out left to right, wrapping at the right
  // edge.  Nothing is shaped: no kerning, no ligatures, no mark stacking — a
  // combining mark gets its own cell like any other glyph.  Canvas has the same
  // primitives (`actualBoundingBoxLeft/Right`, `width`), so this reproduces the
  // algorithm exactly.
  interface Props {
    text: string;
    /** Font size in px (the buffer's, never changed by the mode toggles). */
    px: number;
    /** The same `font-family` stack the buffer uses. */
    family: string;
    /** Caret / selection positions, mirrored from the textarea. */
    caret: number;
    selStart: number;
    selEnd: number;
    /** Vertical scroll offset of the textarea, in px. */
    scrollTop: number;
    colour: string;
    /** Colour Glyphs off → force the monochrome (text) presentation. */
    colourGlyphs: boolean;
    /** Panel background, painted first so the canvas hides the textarea. */
    bg: string;
  }
  let {
    text,
    px,
    family,
    caret,
    selStart,
    selEnd,
    scrollTop,
    colour,
    colourGlyphs,
    bg,
  }: Props = $props();

  const LINE_HEIGHT = 1.5;
  const PAD_X = 2;
  const PAD_Y = 2;

  /** Characters that a colour font may render as a colour glyph. */
  function isEmojiish(ch: string): boolean {
    const cp = ch.codePointAt(0) ?? 0;
    return (
      (cp >= 0x1f000 && cp <= 0x1faff) ||
      (cp >= 0x2600 && cp <= 0x27bf) ||
      cp === 0xfe0f
    );
  }

  let canvas = $state<HTMLCanvasElement>();
  let box = $state<HTMLDivElement>();

  interface Glyph {
    ch: string;
    /** Ink-left edge, relative to the line origin. */
    x: number;
    /** Where the pen goes so the ink lands on `x`. */
    ox: number;
    cellW: number;
    line: number;
  }

  /** The cell layout — the whole point of glyph mode. */
  function layout(ctx: CanvasRenderingContext2D, maxW: number) {
    const glyphs: Glyph[] = [];
    const starts: number[] = []; // pen x per string index
    const lines: number[] = [];
    let x = 0;
    let line = 0;
    for (let i = 0; i < text.length; ) {
      const cp = text.codePointAt(i)!;
      const ch = String.fromCodePoint(cp);
      const step = ch.length;
      if (ch === "\n") {
        starts[i] = 0;
        lines[i] = line;
        x = 0;
        line++;
        i += step;
        continue;
      }
      const m = ctx.measureText(ch);
      const inkW = m.actualBoundingBoxLeft + m.actualBoundingBoxRight;
      let lsb = -m.actualBoundingBoxLeft;
      let trailing = m.width - m.actualBoundingBoxRight;
      if (lsb < 0 && trailing < 0) lsb = inkW / 4;
      // GDI pads both sides with whichever side bearing is larger, so every
      // cell is symmetric even when the glyph leans left or right.
      const pad = Math.max(lsb, trailing);
      const cellW = pad + inkW + pad;
      if (x > 0 && x + cellW > maxW - PAD_X * 2) {
        x = 0;
        line++;
      }
      starts[i] = x;
      lines[i] = line;
      glyphs.push({ ch, x: x + pad, ox: m.actualBoundingBoxLeft, cellW, line });
      x += cellW;
      i += step;
    }
    starts[text.length] = x;
    lines[text.length] = line;
    return { glyphs, starts, lines };
  }

  function draw() {
    const el = canvas;
    const host = box;
    if (!el || !host) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w <= 0 || h <= 0) return;
    el.width = Math.round(w * dpr);
    el.height = Math.round(h * dpr);
    el.style.width = w + "px";
    el.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const css = getComputedStyle(host);
    ctx.clearRect(0, 0, w, h);
    // Opaque, so the textarea underneath (and its shaped caret/selection)
    // cannot show through this layout.
    ctx.fillStyle = bg || "#ffffff";
    ctx.fillRect(0, 0, w, h);
    ctx.font = `${px}px ${family || css.fontFamily}`;
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";

    const probe = ctx.measureText("Mg");
    const ascent = probe.fontBoundingBoxAscent || px * 0.8;
    const lineH = px * LINE_HEIGHT;

    const { glyphs, starts, lines } = layout(ctx, w);

    ctx.translate(0, -scrollTop);

    // Selection first, so the glyphs stay readable on top of it.
    if (selEnd > selStart) {
      ctx.fillStyle = "rgba(0, 120, 215, 0.28)";
      // Per-index rectangles, so a selection that spans lines is still exact.
      for (let i = selStart; i < selEnd && i < text.length; i++) {
        const line = lines[i] ?? 0;
        const x0 = starts[i] ?? 0;
        const x1 = starts[i + 1] ?? x0 + px * 0.5;
        const sameLine = (lines[i + 1] ?? line) === line;
        ctx.fillRect(
          x0 + PAD_X,
          PAD_Y + line * lineH,
          (sameLine ? x1 : w) - x0,
          lineH,
        );
      }
    }

    ctx.fillStyle = colour;
    for (const g of glyphs) {
      const baseY = PAD_Y + g.line * lineH + ascent;
      // `IsColourGlyph()` off in the original means the monochrome outline is
      // drawn; on the web the equivalent is the text presentation selector.
      const draw = colourGlyphs || !isEmojiish(g.ch) ? g.ch : g.ch + "\uFE0E";
      ctx.fillText(draw, PAD_X + g.x + g.ox, baseY);
    }

    // Our own caret: the browser's would sit where the *shaped* text put it.
    if (caret >= 0) {
      const line = lines[caret] ?? 0;
      const x = (starts[caret] ?? 0) + PAD_X;
      ctx.fillStyle = colour;
      ctx.fillRect(
        x,
        PAD_Y + line * lineH + 1,
        Math.max(1, Math.round(px / 12)),
        lineH - 2,
      );
    }
  }

  // Redraw whenever anything that feeds the layout changes.
  $effect(() => {
    void text;
    void px;
    void family;
    void caret;
    void selStart;
    void selEnd;
    void scrollTop;
    void colour;
    void colourGlyphs;
    void bg;
    draw();
  });
</script>

<div class="gtext" bind:this={box}>
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .gtext {
    position: absolute;
    /* Inset by the textarea's border so the box keeps its outline. */
    inset: 1px;
    z-index: 2;
    pointer-events: none;
    overflow: hidden;
  }
  canvas {
    display: block;
  }
</style>
