#!/usr/bin/env python3
"""Generate the illustrated hand/marker sprite ONCE, as a controlled asset.

Produces ``assets/hand/hand_right_marker.png`` (RGBA) and its metadata JSON
(nib anchor, native pen angle, wrist anchor). The sprite is drawn at 4x and
downsampled for clean edges. It is committed to the repository and loaded by
``hand_rig.py`` — per the product rules, no image is ever regenerated per
frame, and no image model is involved.

Sprite geometry (final coordinates, 460x460 canvas):

- The marker nib touches the board at NIB (a known pixel, recorded in
  metadata). The barrel extends from the nib toward the lower-right at
  ``PEN_ANGLE_DEG`` (screen degrees, y-down), with the illustrated right hand
  gripping it and the wrist exiting toward the lower-right corner.
- The canvas leaves generous margins so rotating up to ±25 degrees around the
  nib never clips the artwork.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

OUT_DIR = WHITEBOARD_ROOT / "assets" / "hand"
SCALE = 4
SIZE = 460  # final sprite canvas (square)

# Final-coordinate anchors, recorded in metadata.
NIB = (92.0, 88.0)
PEN_ANGLE_DEG = 42.0        # nib -> barrel direction, screen degrees (y down)
WRIST = (238.0, 248.0)      # sits at the palm heel; the cuff tucks under it

SKIN = (222, 176, 138, 255)
SKIN_SHADE = (196, 146, 108, 255)
OUTLINE = (114, 76, 54, 255)
BARREL = (58, 63, 66, 255)
BARREL_LIGHT = (86, 92, 96, 255)
CAP = (34, 38, 40, 255)
NIB_INK = (24, 27, 29, 255)
CUFF = (92, 118, 158, 255)


def to_canvas(point: tuple[float, float]) -> tuple[float, float]:
    return point[0] * SCALE, point[1] * SCALE


def along(origin: tuple[float, float], angle_rad: float, distance: float,
          side: float = 0.0) -> tuple[float, float]:
    """Point at ``distance`` along ``angle`` from origin, offset ``side`` px
    perpendicular (positive = clockwise/right of travel)."""
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)
    px, py = -dy, dx
    return (origin[0] + dx * distance + px * side,
            origin[1] + dy * distance + py * side)


def rounded_quad(draw: ImageDraw.ImageDraw, quad: list[tuple[float, float]],
                 fill, outline=None, width: int = 0) -> None:
    draw.polygon(quad, fill=fill, outline=outline, width=width)


def finger(draw: ImageDraw.ImageDraw, base: tuple[float, float], angle_rad: float,
           length: float, thickness: float) -> None:
    """A capsule-shaped finger from base along angle."""
    tip = along(base, angle_rad, length)
    half = thickness / 2
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)
    px, py = -dy, dx
    quad = [
        (base[0] + px * half, base[1] + py * half),
        (tip[0] + px * half, tip[1] + py * half),
        (tip[0] - px * half, tip[1] - py * half),
        (base[0] - px * half, base[1] - py * half),
    ]
    draw.polygon(quad, fill=SKIN, outline=OUTLINE, width=2 * SCALE)
    draw.ellipse((tip[0] - half, tip[1] - half, tip[0] + half, tip[1] + half),
                 fill=SKIN, outline=OUTLINE, width=2 * SCALE)
    draw.ellipse((base[0] - half, base[1] - half, base[0] + half, base[1] + half),
                 fill=SKIN)


def build() -> Image.Image:
    canvas = SIZE * SCALE
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    angle = math.radians(PEN_ANGLE_DEG)
    nib = to_canvas(NIB)
    s = SCALE

    # --- Marker ---------------------------------------------------------
    cone_end = along(nib, angle, 26 * s)
    barrel_end = along(nib, angle, 190 * s)
    # Nib cone.
    draw.polygon([nib,
                  along(cone_end, angle, 0, -9 * s),
                  along(cone_end, angle, 0, 9 * s)], fill=NIB_INK)
    # Ferrule.
    ferrule_end = along(nib, angle, 40 * s)
    rounded_quad(draw, [along(cone_end, angle, 0, -10 * s),
                        along(ferrule_end, angle, 0, -11 * s),
                        along(ferrule_end, angle, 0, 11 * s),
                        along(cone_end, angle, 0, 10 * s)],
                 fill=(180, 184, 186, 255), outline=CAP, width=s)
    # Barrel with a light top edge.
    rounded_quad(draw, [along(ferrule_end, angle, 0, -14 * s),
                        along(barrel_end, angle, 0, -15 * s),
                        along(barrel_end, angle, 0, 15 * s),
                        along(ferrule_end, angle, 0, 14 * s)],
                 fill=BARREL, outline=CAP, width=s)
    rounded_quad(draw, [along(ferrule_end, angle, 0, -13 * s),
                        along(barrel_end, angle, 0, -14 * s),
                        along(barrel_end, angle, 0, -7 * s),
                        along(ferrule_end, angle, 0, -6 * s)],
                 fill=BARREL_LIGHT)
    # End cap.
    cap_start = along(nib, angle, 178 * s)
    rounded_quad(draw, [along(cap_start, angle, 0, -15 * s),
                        along(barrel_end, angle, 0, -15 * s),
                        along(barrel_end, angle, 0, 15 * s),
                        along(cap_start, angle, 0, 15 * s)],
                 fill=CAP)

    # --- Hand -------------------------------------------------------------
    # Screen-space orientation: the barrel runs down-right at 42 deg; the palm
    # sits on the lower-left side of the barrel (side > 0) with the fingers
    # curling up over the barrel and the wrist exiting toward lower-right.

    # Forearm/cuff band behind the palm.
    wrist = to_canvas(WRIST)
    cuff_dir = angle + math.radians(14)
    draw.polygon([along(wrist, cuff_dir, -26 * s, -40 * s),
                  along(wrist, cuff_dir, 34 * s, -46 * s),
                  along(wrist, cuff_dir, 34 * s, 46 * s),
                  along(wrist, cuff_dir, -26 * s, 40 * s)],
                 fill=CUFF, outline=(60, 82, 116, 255), width=2 * s)

    # Palm: rounded polygon hugging the barrel from the lower-left side and
    # wrapping behind it toward the wrist.
    palm_points = [
        along(nib, angle, 96 * s, 16 * s),
        along(nib, angle, 88 * s, 48 * s),
        along(nib, angle, 118 * s, 74 * s),
        along(nib, angle, 170 * s, 80 * s),
        along(nib, angle, 212 * s, 56 * s),
        along(nib, angle, 208 * s, 4 * s),
        along(nib, angle, 160 * s, -12 * s),
        along(nib, angle, 118 * s, -6 * s),
    ]
    draw.polygon(palm_points, fill=SKIN, outline=OUTLINE, width=2 * s)

    # Curled middle/ring/little fingers reaching from the palm up over the
    # barrel (crossing it to the upper-right side).
    for i, (dist, length, thick) in enumerate([(104, 52, 27), (124, 50, 26), (144, 44, 23)]):
        base = along(nib, angle, dist * s, 40 * s)
        finger(draw, base, angle - math.radians(90 - i * 6), length * s, thick * s)

    # Thumb: pinches the barrel near the ferrule from the palm side.
    thumb_base = along(nib, angle, 92 * s, 26 * s)
    finger(draw, thumb_base, angle - math.radians(148), 46 * s, 27 * s)

    # Index finger: rests on top of the barrel pointing toward the nib.
    index_base = along(nib, angle, 108 * s, -16 * s)
    finger(draw, index_base, angle + math.pi + math.radians(10), 56 * s, 25 * s)

    # Soft shading on the palm heel (clipped to the palm alpha).
    shade = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    heel = along(nib, angle, 178 * s, 44 * s)
    ImageDraw.Draw(shade).ellipse(
        (heel[0] - 34 * s, heel[1] - 26 * s, heel[0] + 34 * s, heel[1] + 26 * s),
        fill=(*SKIN_SHADE[:3], 120))
    shade = shade.filter(ImageFilter.GaussianBlur(5 * s))
    mask = image.getchannel("A").point(lambda a: 255 if a > 200 else 0)
    image.paste(Image.alpha_composite(image, shade), (0, 0), mask)

    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sprite = build()
    sprite_path = OUT_DIR / "hand_right_marker.png"
    sprite.save(sprite_path)
    metadata = {
        "id": "hand_right_marker",
        "sprite": sprite_path.name,
        "size": [SIZE, SIZE],
        "nib": list(NIB),
        "pen_angle_deg": PEN_ANGLE_DEG,
        "wrist": list(WRIST),
        "contact": "down",
        "provenance": "generated once by tools/generate_hand.py; do not regenerate per frame",
    }
    (OUT_DIR / "hand_right_marker.json").write_text(json.dumps(metadata, indent=2) + "\n",
                                                    encoding="utf-8")
    print(f"wrote {sprite_path.relative_to(WHITEBOARD_ROOT)} and metadata")


if __name__ == "__main__":
    main()
