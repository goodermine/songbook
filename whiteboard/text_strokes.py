"""True stroke text: Hershey single-line glyphs through the stroke engine.

Parses the bundled ``assets/fonts/futural.jhf`` (Hershey Simplex) and lays
out strings as ordered polyline strokes in board coordinates, so headings are
physically written by the marker — at 50 % progress only the first half of
the glyph strokes exists, and the pen lifts between disconnected components.

Layout contract: ``(x, y)`` is the top-left of the capital-letter box and
``size`` is the cap height in pixels, mirroring how the raster text actions
position type closely enough for storyboard authors to swap action types.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

Point = tuple[float, float]

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
DEFAULT_FONT = FONT_DIR / "futural.jhf"


class TextStrokeError(RuntimeError):
    """Raised for unsupported characters or unusable font data."""


@dataclass(frozen=True)
class Glyph:
    char: str
    left: float
    right: float
    polylines: tuple[tuple[Point, ...], ...]  # y increases downward, baseline at 0-ish

    @property
    def advance(self) -> float:
        return self.right - self.left


def _parse_jhf(path: Path) -> dict[str, Glyph]:
    """Parse a James Hurt Hershey font file, handling wrapped glyph lines."""
    if not path.is_file():
        raise TextStrokeError(f"Stroke font not found: {path}")
    lines = path.read_text(encoding="ascii").splitlines()
    records: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        vertex_pairs = int(line[5:8])
        needed = 8 + vertex_pairs * 2
        while len(line) < needed and index < len(lines):
            line += lines[index]
            index += 1
        if len(line) < needed:
            raise TextStrokeError(f"Truncated glyph record in {path.name}")
        records.append(line)

    origin = ord("R")
    glyphs: dict[str, Glyph] = {}
    for offset, record in enumerate(records):
        char = chr(32 + offset)
        data = record[8:]
        left = ord(data[0]) - origin
        right = ord(data[1]) - origin
        polylines: list[tuple[Point, ...]] = []
        current: list[Point] = []
        for i in range(2, len(data), 2):
            pair = data[i:i + 2]
            if pair == " R":  # pen lift
                if len(current) >= 2:
                    polylines.append(tuple(current))
                current = []
                continue
            current.append((float(ord(pair[0]) - origin), float(ord(pair[1]) - origin)))
        if len(current) >= 2:
            polylines.append(tuple(current))
        glyphs[char] = Glyph(char, float(left), float(right), tuple(polylines))
    return glyphs


@lru_cache(maxsize=4)
def load_font(path: Path = DEFAULT_FONT) -> dict[str, Glyph]:
    glyphs = _parse_jhf(path)
    for probe in ("H", "A", " "):
        if probe not in glyphs:
            raise TextStrokeError(f"Font {path.name} lacks required glyph {probe!r}")
    return glyphs


@lru_cache(maxsize=4)
def _cap_metrics(path: Path = DEFAULT_FONT) -> tuple[float, float]:
    """(cap_top, baseline) in font units, measured from the 'H' glyph."""
    h = load_font(path)["H"]
    ys = [p[1] for poly in h.polylines for p in poly]
    return min(ys), max(ys)


def text_to_strokes(text: str, x: float, y: float, size: float,
                    font_path: Path = DEFAULT_FONT,
                    letter_spacing: float = 0.0) -> list[list[Point]]:
    """Lay out ``text`` as ordered strokes; ``size`` is the cap height in px."""
    if not text.strip():
        raise TextStrokeError("Cannot lay out empty text")
    glyphs = load_font(font_path)
    unsupported = sorted({c for c in text if c not in glyphs})
    if unsupported:
        raise TextStrokeError(f"Font {font_path.name} has no glyphs for {unsupported!r} "
                              f"in {text!r}")
    cap_top, baseline = _cap_metrics(font_path)
    scale = size / (baseline - cap_top)

    strokes: list[list[Point]] = []
    pen_x = x
    for char in text:
        glyph = glyphs[char]
        for polyline in glyph.polylines:
            strokes.append([
                (pen_x + (px - glyph.left) * scale, y + (py - cap_top) * scale)
                for px, py in polyline
            ])
        pen_x += glyph.advance * scale + letter_spacing
    if not strokes:
        raise TextStrokeError(f"Text {text!r} produced no visible strokes")
    return strokes


def strokes_bounds(strokes: list[list[Point]]) -> tuple[float, float, float, float]:
    xs = [p[0] for stroke in strokes for p in stroke]
    ys = [p[1] for stroke in strokes for p in stroke]
    return min(xs), min(ys), max(xs), max(ys)


def total_length(strokes: list[list[Point]]) -> float:
    return sum(math.dist(a, b) for stroke in strokes for a, b in zip(stroke, stroke[1:]))
