#!/usr/bin/env python3
"""Diagnostic contact sheet: every registered asset, labelled with its bounds.

Phase 2 gate artifact. For each asset the cell shows:

- the strokes (ink), drawn in order;
- arrowhead legs (teal) where the asset declares them;
- the view_box (red rectangle);
- pen-up travel between consecutive strokes (dashed orange lines);
- id, view_box, stroke/lift counts and total pen-up distance.

Writes ``baseline/assets_contact_sheet.png``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

from asset_registry import AssetRegistry  # noqa: E402

ASSET_DIR = WHITEBOARD_ROOT / "assets"
OUTPUT = WHITEBOARD_ROOT / "baseline" / "assets_contact_sheet.png"

CELL_W, CELL_H = 426, 240
LABEL_H = 64
COLUMNS = 3
SCALE = 3  # board 1280x720 -> cell 426x240 (approximately /3)

INK = (38, 43, 46)
TEAL = (31, 111, 112)
RED = (202, 60, 40)
ORANGE = (222, 130, 40)
PAPER = (252, 251, 246)


def font(size: int) -> ImageFont.ImageFont:
    for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def dashed_line(draw: ImageDraw.ImageDraw, a, b, color, dash=6, width=2) -> None:
    distance = math.dist(a, b)
    if distance < 1:
        return
    steps = max(1, int(distance / dash))
    for i in range(0, steps, 2):
        t0, t1 = i / steps, min(1.0, (i + 1) / steps)
        draw.line((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                   a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1),
                  fill=color, width=width)


def render_cell(asset) -> Image.Image:
    board = Image.new("RGB", asset.board, PAPER)
    draw = ImageDraw.Draw(board)
    for stroke, following in zip(asset.strokes, asset.strokes[1:]):
        dashed_line(draw, stroke.points[-1], following.points[0], ORANGE, dash=14, width=4)
    for stroke in asset.strokes:
        draw.line([tuple(p) for p in stroke.points], fill=INK, width=5, joint="curve")
        if stroke.arrowhead:
            draw.line([tuple(p) for p in stroke.arrowhead], fill=TEAL, width=4, joint="curve")
    x0, y0, x1, y1 = asset.view_box
    draw.rectangle((x0, y0, x1, y1), outline=RED, width=3)

    cell = Image.new("RGB", (CELL_W, CELL_H + LABEL_H), (255, 255, 255))
    cell.paste(board.resize((CELL_W, CELL_H), Image.Resampling.LANCZOS), (0, 0))
    label = ImageDraw.Draw(cell)
    lifts = sum(1 for s in asset.strokes if s.pen_lift_after)
    label.text((8, CELL_H + 6), asset.id, font=font(16), fill=INK)
    label.text((8, CELL_H + 26),
               f"view_box=({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})",
               font=font(12), fill=(90, 90, 90))
    label.text((8, CELL_H + 42),
               f"{len(asset.strokes)} strokes, {lifts} pen lifts, "
               f"{asset.pen_up_travel():.0f}px pen-up travel",
               font=font(12), fill=(90, 90, 90))
    return cell


def main() -> None:
    registry = AssetRegistry(ASSET_DIR)
    names = registry.names()
    rows = -(-len(names) // COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * (CELL_W + 12) + 12,
                              rows * (CELL_H + LABEL_H + 12) + 12), (235, 233, 226))
    for index, name in enumerate(names):
        cell = render_cell(registry.load(name))
        x = 12 + (index % COLUMNS) * (CELL_W + 12)
        y = 12 + (index // COLUMNS) * (CELL_H + LABEL_H + 12)
        sheet.paste(cell, (x, y))
    OUTPUT.parent.mkdir(exist_ok=True)
    sheet.save(OUTPUT)
    print(f"wrote {OUTPUT.relative_to(WHITEBOARD_ROOT)} ({len(names)} assets)")


if __name__ == "__main__":
    main()
