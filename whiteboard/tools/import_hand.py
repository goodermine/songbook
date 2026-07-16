#!/usr/bin/env python3
"""Import an externally created hand/marker image into the rig.

Use this to replace the built-in procedural sprite with a nicer hand made
anywhere — an AI-generated illustration (Midjourney, DALL-E, GPT-4o image
output…), a scan, or a photograph cut out to transparency. Per the product
rules the image is imported ONCE as a controlled asset; the engine never
regenerates it per frame.

Requirements for the source image:

- RGBA with a transparent background (the tool can also key out a solid
  near-white background with ``--key-background``);
- a right hand holding one marker, nib clearly visible;
- roughly the pose of the default sprite: nib toward the upper-left, barrel
  toward the lower-right, wrist exiting lower-right.

You must tell the tool where the nib is and which way the barrel points —
measure both in any image editor:

    python3 tools/import_hand.py my_hand.png \
        --nib 184,120 \
        --pen-angle 47 \
        --height 340

``--nib``       pixel of the marker tip in the SOURCE image (x,y)
``--pen-angle`` direction from the nib toward the barrel's back end, in
                screen degrees (y down): 0 = right, 90 = straight down.
                The default sprite uses 42.
``--wrist``     optional wrist pixel (defaults to the lower-right of the art)
``--height``    optional final sprite height in board pixels (default keeps
                the source scale; the default rig hand is ~330px tall at 720p)

The tool scales/pads the art onto a rig-compatible canvas with margins for
±25 degrees of nib-anchored rotation, writes ``assets/hand/<name>.png`` and
``<name>.json``, and verifies the result loads through HandRig. Pass
``--name hand_right_marker`` (the default) to replace the active rig, or a
different name and switch via the metadata later. The previous sprite is
backed up alongside with a ``.bak`` suffix.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

from hand_rig import HandRig  # noqa: E402

HAND_DIR = WHITEBOARD_ROOT / "assets" / "hand"
ROTATION_HEADROOM_DEG = 25.0


def parse_point(text: str) -> tuple[float, float]:
    x, y = text.split(",")
    return float(x), float(y)


def key_background(image: Image.Image, tolerance: int) -> Image.Image:
    """Make near-white pixels transparent (for sources without an alpha)."""
    data = image.getdata()
    keyed = [(r, g, b, 0) if r > 255 - tolerance and g > 255 - tolerance and b > 255 - tolerance
             else (r, g, b, a) for r, g, b, a in data]
    result = Image.new("RGBA", image.size)
    result.putdata(keyed)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="RGBA image of a right hand holding a marker")
    parser.add_argument("--nib", type=parse_point, required=True,
                        help="marker tip pixel in the source image, e.g. 184,120")
    parser.add_argument("--pen-angle", type=float, required=True,
                        help="nib->barrel direction in screen degrees (y down)")
    parser.add_argument("--wrist", type=parse_point, default=None,
                        help="wrist pixel in the source image (optional)")
    parser.add_argument("--height", type=float, default=None,
                        help="final sprite height in board pixels (optional rescale)")
    parser.add_argument("--name", default="hand_right_marker",
                        help="asset name to write (default replaces the active rig)")
    parser.add_argument("--key-background", type=int, default=None, metavar="TOLERANCE",
                        help="key out a near-white background with this tolerance (e.g. 24)")
    args = parser.parse_args()

    image = Image.open(args.source).convert("RGBA")
    if args.key_background is not None:
        image = key_background(image, args.key_background)
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise SystemExit("Source image is fully transparent — nothing to import")
    image = image.crop(bbox)
    nib = (args.nib[0] - bbox[0], args.nib[1] - bbox[1])
    wrist = ((args.wrist[0] - bbox[0], args.wrist[1] - bbox[1]) if args.wrist
             else (image.width * 0.8, image.height * 0.85))
    if not (0 <= nib[0] < image.width and 0 <= nib[1] < image.height):
        raise SystemExit(f"--nib {args.nib} falls outside the artwork bounds {bbox}")

    scale = (args.height / image.height) if args.height else 1.0
    if scale != 1.0:
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))),
                             Image.Resampling.LANCZOS)
        nib = (nib[0] * scale, nib[1] * scale)
        wrist = (wrist[0] * scale, wrist[1] * scale)

    # Pad the canvas so ±ROTATION_HEADROOM_DEG around the nib never clips.
    corners = [(0, 0), (image.width, 0), (0, image.height), (image.width, image.height)]
    reach = max(math.dist(nib, corner) for corner in corners)
    margin = reach * math.sin(math.radians(ROTATION_HEADROOM_DEG)) + 4
    canvas_size = (image.width + 2 * round(margin), image.height + 2 * round(margin))
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    canvas.alpha_composite(image, (round(margin), round(margin)))
    nib = (nib[0] + round(margin), nib[1] + round(margin))
    wrist = (wrist[0] + round(margin), wrist[1] + round(margin))

    HAND_DIR.mkdir(parents=True, exist_ok=True)
    sprite_path = HAND_DIR / f"{args.name}.png"
    metadata_path = HAND_DIR / f"{args.name}.json"
    for path in (sprite_path, metadata_path):
        if path.exists():
            path.replace(path.with_suffix(path.suffix + ".bak"))
    canvas.save(sprite_path)
    metadata_path.write_text(json.dumps({
        "id": args.name,
        "sprite": sprite_path.name,
        "size": list(canvas.size),
        "nib": [round(nib[0], 2), round(nib[1], 2)],
        "pen_angle_deg": args.pen_angle,
        "wrist": [round(wrist[0], 2), round(wrist[1], 2)],
        "contact": "down",
        "provenance": f"imported once from {args.source.name} by tools/import_hand.py",
    }, indent=2) + "\n", encoding="utf-8")

    rig = HandRig(HAND_DIR, args.name)  # verify it loads and anchors are sane
    probe = Image.new("RGBA", (1280, 720))
    pose = rig.draw(probe, (640.0, 360.0), (1.0, 0.0))
    print(f"imported {sprite_path.relative_to(WHITEBOARD_ROOT)} "
          f"({canvas.size[0]}x{canvas.size[1]}, nib at {metadata_path.name}:nib)")
    print(f"verification pose: nib_error={pose['nib_error_px']:.2f}px "
          f"angle_error={pose['angle_error_deg']:.2f}deg")
    print("Previous sprite (if any) kept with a .bak suffix.")


if __name__ == "__main__":
    main()
