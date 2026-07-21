#!/usr/bin/env python3
"""Reusable helper for drawing Mega-pack doodles ink-then-colour.

`draw_doodle` returns the actions to draw one doodle: a charcoal outline pass
(the hand inks the linework) followed by a serpentine colour pass (the hand
scribbles the colour in, band by band). Height is auto-fitted to a box from the
PNG's aspect ratio, so callers only pick a name, a centre and a size.

Use as a library::

    from tools.doodle_lib import draw_doodle
    actions, end = draw_doodle("doodle-05", at=(540, 560), box=760, start=0.2)

Or as a CLI to build a whole "draw these doodles" storyboard::

    python3 tools/doodle_lib.py doodle-05 doodle-104 doodle-103 \
        --labels BURGER BEAR PINEAPPLE --out storyboards/my_doodles.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEGA_DIR = ROOT / "assets" / "images" / "mega"
GAP = 0.12


def _resolve(name: str) -> tuple[str, Path]:
    """Accept 'doodle-05' or 'mega/doodle-05'; return (image_ref, png_path)."""
    stem = name.split("/")[-1]
    path = MEGA_DIR / f"{stem}.png"
    if not path.is_file():
        raise FileNotFoundError(f"No doodle {stem!r} at {path}")
    return f"mega/{stem}", path


def fit_height(name: str, box: int) -> int:
    """Largest height (px) that keeps the doodle within a box x box square."""
    _, path = _resolve(name)
    with Image.open(path) as im:
        w, h = im.size
    return int(min(box, box * h / w))


def draw_doodle(name: str, at: tuple[float, float] = (540, 560), box: int = 760,
                start: float = 0.2, ink_dur: float = 1.5, colour_dur: float = 2.6,
                id_prefix: str = "dd", label: str | None = None,
                label_y: float = 120, label_size: int = 60,
                label_color: str = "accent") -> tuple[list[dict], float]:
    """Actions to draw one doodle ink-then-colour. Returns (actions, end_time).

    - ink pass: ``sketch_image`` with ``layer:"ink"`` (charcoal outline sweep)
    - colour pass: ``sketch_image`` with ``reveal:"serpentine"`` (scribble fill)
    - optional hand-written label above it
    """
    image, _ = _resolve(name)
    height = fit_height(name, box)
    ink_start = round(start, 2)
    col_start = round(ink_start + ink_dur + GAP, 2)
    actions = [
        {"id": f"{id_prefix}_ink", "type": "sketch_image", "image": image, "layer": "ink",
         "at": [at[0], at[1]], "height": height, "start": ink_start,
         "duration": ink_dur, "requires_pen": True},
        {"id": f"{id_prefix}_col", "type": "sketch_image", "image": image, "reveal": "serpentine",
         "at": [at[0], at[1]], "height": height, "start": col_start,
         "duration": colour_dur, "requires_pen": True},
    ]
    end = round(col_start + colour_dur, 2)
    if label:
        actions.append({"id": f"{id_prefix}_lbl", "type": "write_text", "text": label,
                        "align": "center", "y": label_y, "size": label_size, "width": 5,
                        "start": round(end + 0.3, 2), "duration": 1.1,
                        "requires_pen": True, "color": label_color})
        end = round(end + 0.3 + 1.1, 2)
    return actions, end


def build_reel(names: list[str], out: Path, labels: list[str] | None = None,
               width: int = 1080, height: int = 1080, box: int = 760,
               at: tuple[float, float] = (540, 600)) -> dict:
    """One scene per doodle (board wipes between), each drawn ink-then-colour."""
    scenes: list[dict] = []
    t = 0.0
    for i, name in enumerate(names):
        lbl = labels[i] if labels and i < len(labels) else None
        actions, end = draw_doodle(name, at=at, box=box, start=round(t + 0.2, 2),
                                   id_prefix=f"d{i}", label=lbl)
        scenes.append({"id": f"doodle_{i}", "start": round(t, 2),
                       "end": round(end + 0.4, 2), "actions": actions})
        t = round(end + 0.4, 2)
    storyboard = {
        "version": 2, "title": "Doodle draw", "width": width, "height": height, "fps": 24,
        "content_duration": round(t, 2), "safe_content_end": round(t - 0.4, 2), "final_hold": 1.6,
        "pen_physics": "lift", "hand": "sprite", "chrome": "none",
        "text_font": "marker", "caption_font": "marker", "stroke_style": "round",
        "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
                  "accent": [202, 83, 48], "teal": [31, 111, 112], "amber": [232, 163, 61]},
        "scenes": scenes,
    }
    out.write_text(json.dumps(storyboard, indent=2))
    return storyboard


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doodles", nargs="+", help="doodle names, e.g. doodle-05")
    ap.add_argument("--labels", nargs="*", help="optional label per doodle")
    ap.add_argument("--out", type=Path, default=ROOT / "storyboards" / "doodles.json")
    ap.add_argument("--box", type=int, default=760)
    args = ap.parse_args()
    sb = build_reel(args.doodles, args.out, args.labels, box=args.box)
    print(f"wrote {args.out}  ({len(sb['scenes'])} doodles, {sb['content_duration']}s)")


if __name__ == "__main__":
    main()
