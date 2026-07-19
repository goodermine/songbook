# Bundled fonts

## PermanentMarker-Regular.ttf — Permanent Marker

Marker-style display font by Font Diner, from Google Fonts. Licensed under
the Apache License, Version 2.0. Used by `write_text` actions with
`"font": "marker"` (or storyboard-level `"text_font": "marker"`): glyphs are
rasterised and revealed through a brush mask that follows Hershey skeleton
paths fitted to the rendered text, so the nib traces believable letter
motion while the finished text keeps the marker look.

# Bundled single-line (stroke) fonts

## futural.jhf — Hershey Simplex

Single-stroke vector font digitised by Dr. Allen V. Hershey at the U.S.
National Bureau of Standards, distributed in the James Hurt (`.jhf`) format
via the Usenet `mod.sources` release (1986). The Hershey fonts are free to
use and distribute; the original distribution asks that the font data not be
sold as-is and that Allen V. Hershey and the NBS be credited.

Format: one glyph per line (ASCII 32–126 in order). Columns 0–4 glyph id,
5–7 vertex-pair count, then coordinate pairs encoded as
`chr(value + ord('R'))`, with the first pair being the left/right advance
hands and the pair `" R"` marking a pen lift. Y increases downward.

Parsed by `text_strokes.py`, which turns glyphs into the same ordered
`StrokePath` geometry the illustration assets use, so text is physically
written by the marker rather than revealed with a raster wipe.
