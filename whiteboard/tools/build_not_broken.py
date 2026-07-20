#!/usr/bin/env python3
"""Generate the 'You're Not Broken' SQUARE (1:1) reel storyboard.

Each beat is its own SCENE (the renderer only draws the active scene's actions,
so the board wipes clean between beats). Within a scene, pen actions
(write_text, draw_asset, draw_fill) are packed sequentially so only one pen is
ever active; illustrations (show_image) and captions (fade_text) float on top.
Scattered pastel watercolour blobs sit behind everything for soft colour.
Timing is a silent-master approximation; the narration retimer locks it to the
VO later.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

W, H = 1080, 1080
CX, CY = W // 2, H // 2
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "storyboards" / "sdh_not_broken_reel.json"

TRANSCRIPT = (
    "If you feel stuck, like something's wrong with you, listen to this, "
    "you're not broken. Your mind is doing exactly what it was built to do: "
    "protect you. And years ago some part of you drew a conclusion - I'm not "
    "safe, I'm not enough - and built everything on top of that. So the "
    "anxiety, the doubt, the stuck feeling, that's not a fault. It's an old "
    "protection, still running. You're not a knot that can't be undone. You're "
    "a thread that got tangled, and threads can be smoothed. You don't need "
    "fixing. You need to meet that old conclusion, and gently update it. You "
    "are never broken. You're protecting yourself. And that can change."
)

GAP = 0.12
BLOB_ASPECT = 520 / 440  # native wash blob w/h
WASH_COLORS = ["green", "mint", "sage", "sky", "peach", "amber"]
scenes: list[dict] = []
_actions: list[dict] = []
_pen_t = 0.0
_scene_start = 0.0
_uid = 0


def _next_id() -> str:
    global _uid
    _uid += 1
    return f"a{_uid:03d}"


def open_scene(sid: str, start: float) -> None:
    global _actions, _pen_t, _scene_start
    _actions = []
    _pen_t = start + 0.2
    _scene_start = start


def close_scene(sid: str, start: float, end: float) -> None:
    scenes.append({"id": sid, "start": start, "end": end, "actions": _actions})


def pen(kind: str, duration: float, **fields) -> None:
    global _pen_t
    _actions.append({"id": _next_id(), "type": kind, "start": round(_pen_t, 2),
                     "duration": duration, "requires_pen": True, **fields})
    _pen_t = round(_pen_t + duration + GAP, 2)


def floats(kind: str, start: float, duration: float, **fields) -> None:
    _actions.append({"id": _next_id(), "type": kind, "start": round(start, 2),
                     "duration": duration, "requires_pen": False, **fields})


def scribble(asset, at, scale, color, dur=0.4, width=5):
    pen("draw_asset", dur, asset=asset, at=list(at), scale=scale, color=color, width=width)


def scatter_washes(seed: int, n: int = 6) -> None:
    """Add n random pastel blobs behind the scene's content (call first)."""
    rng = random.Random(seed)
    for _ in range(n):
        color = rng.choice(WASH_COLORS)
        h = rng.randint(300, 520)
        w = BLOB_ASPECT * h
        cx = rng.uniform(w / 2, W - w / 2)
        cy = rng.uniform(h / 2, H - h / 2)
        floats("show_image", round(_scene_start + 0.05, 2), 1.2,
               image=f"wash_{color}", at=[round(cx), round(cy)], height=h)


# =========================================================================
# S1  HOOK  0-7  (voice holds here ~12s; extra scatter keeps it alive)
open_scene("hook", 0.0)
scatter_washes(1, 7)
pen("write_text", 1.4, text="YOU'RE NOT", x=250, y=400, size=66, width=5, color="ink")
pen("write_text", 1.2, text="BROKEN", x=290, y=515, size=98, width=8, color="accent")
scribble("circle_highlight", (CX, 560), 2.0, "teal", dur=0.7, width=6)
scribble("question_mark", (180, 250), 0.5, "faint")
scribble("question_mark", (880, 300), 0.42, "faint")
scribble("exclamation", (930, 560), 0.5, "accent")
scribble("star_five", (150, 560), 0.34, "teal")
scribble("star_five", (930, 800), 0.3, "teal")
close_scene("hook", 0.0, 7.0)

# S2  your mind is doing its job  7-15
open_scene("job", 7.0)
scatter_washes(2, 6)
pen("write_text", 1.3, text="YOUR MIND IS", x=260, y=95, size=52, width=4, color="ink")
pen("write_text", 1.3, text="DOING ITS JOB", x=230, y=185, size=56, width=5, color="ink")
scribble("underline_swash", (CX, 300), 1.6, "teal", dur=0.6, width=6)
floats("show_image", 7.3, 6.9, image="two_chairs", at=[CX, 690], height=520)
floats("fade_text", 13.6, 0.9, text="not against you - for you", x=330, y=1000,
       size=32, italic=True, color="faint")
scribble("star_five", (150, 520), 0.3, "teal")
scribble("heart", (930, 470), 0.32, "accent")
scribble("star_five", (930, 860), 0.28, "accent")
close_scene("job", 7.0, 15.0)

# S3  an old conclusion  15-24
open_scene("conclusion", 15.0)
scatter_washes(3, 6)
pen("write_text", 1.3, text="AN OLD", x=360, y=95, size=58, width=5, color="ink")
pen("write_text", 1.4, text="CONCLUSION", x=280, y=190, size=58, width=5, color="teal")
scribble("old_loop", (150, 250), 0.45, "faint", dur=0.5)
floats("show_image", 15.3, 7.9, image="iceberg_mind", at=[CX, 700], height=540)
floats("fade_text", 22.4, 0.9, text="I'm not safe. I'm not enough.", x=300, y=1005,
       size=34, italic=True, color="faint")
scribble("question_mark", (150, 840), 0.5, "faint")
scribble("question_mark", (940, 860), 0.45, "faint")
close_scene("conclusion", 15.0, 24.0)

# S4  not a fault, a guard  24-32
open_scene("guard", 24.0)
scatter_washes(4, 6)
pen("write_text", 1.3, text="NOT A FAULT", x=310, y=95, size=54, width=5, color="ink")
pen("write_text", 1.2, text="A GUARD", x=370, y=190, size=64, width=6, color="accent")
scribble("circle_highlight", (CX + 10, 205), 1.7, "teal", dur=0.7, width=6)
floats("show_image", 24.3, 6.9, image="key_keyhole", at=[CX, 700], height=500)
floats("fade_text", 30.4, 0.9, text="an old protection, still running", x=310, y=1010,
       size=32, italic=True, color="faint")
scribble("star_five", (150, 470), 0.3, "teal")
scribble("exclamation", (940, 440), 0.45, "accent")
scribble("star_five", (940, 880), 0.28, "teal")
close_scene("guard", 24.0, 32.0)

# S5  just tangled  32-41
open_scene("tangled", 32.0)
scatter_washes(5, 6)
pen("write_text", 1.2, text="NOT BROKEN.", x=300, y=95, size=52, width=5, color="faint")
scribble("cross_out", (CX + 10, 85), 1.5, "accent", dur=0.5, width=6)
pen("write_text", 1.3, text="JUST TANGLED", x=270, y=195, size=60, width=6, color="teal")
floats("show_image", 32.4, 7.9, image="tangled_thread", at=[CX, 720], height=440)
floats("fade_text", 39.4, 0.9, text="and threads can be smoothed", x=320, y=1010,
       size=32, italic=True, color="faint")
scribble("star_five", (150, 560), 0.32, "accent")
scribble("star_five", (940, 560), 0.3, "teal")
close_scene("tangled", 32.0, 41.0)

# S6  you don't need fixing  41-49
open_scene("fixing", 41.0)
scatter_washes(6, 6)
pen("write_text", 1.3, text="YOU DON'T", x=350, y=95, size=56, width=5, color="ink")
pen("write_text", 1.3, text="NEED FIXING", x=300, y=190, size=60, width=6, color="ink")
scribble("underline_swash", (CX, 300), 1.6, "accent", dur=0.6, width=6)
floats("show_image", 41.3, 6.9, image="head_staircase", at=[CX, 700], height=500)
pen("draw_asset", 0.7, asset="heart", at=[935, 470], scale=0.5, color="accent", width=6)
pen("draw_fill", 1.1, asset="heart", at=[935, 470], scale=0.5, width=16, color="accent")
floats("fade_text", 47.4, 0.9, text="meet it - and gently update it", x=320, y=1010,
       size=32, italic=True, color="faint")
scribble("star_five", (140, 470), 0.3, "teal")
close_scene("fixing", 41.0, 49.0)

# S7  you were protecting yourself  49-56
open_scene("protect", 49.0)
scatter_washes(7, 6)
pen("write_text", 1.3, text="YOU WERE", x=370, y=95, size=56, width=5, color="ink")
pen("write_text", 1.3, text="PROTECTING YOU", x=210, y=190, size=52, width=5, color="teal")
scribble("checkmark", (CX, 330), 1.0, "teal", dur=0.7, width=9)
floats("show_image_sequence", 49.3, 5.9,
       images=[f"seed_grow_{i}" for i in range(1, 7)], at=[CX, 730], height=430)
scribble("star_five", (160, 560), 0.32, "accent")
scribble("star_five", (940, 560), 0.3, "teal")
close_scene("protect", 49.0, 56.0)

# S8  and that can change  56-63
open_scene("change", 56.0)
scatter_washes(8, 6)
pen("write_text", 1.3, text="AND THAT", x=360, y=110, size=60, width=5, color="ink")
pen("write_text", 1.3, text="CAN CHANGE.", x=290, y=210, size=66, width=6, color="accent")
scribble("underline_swash", (CX, 320), 1.9, "teal", dur=0.7, width=6)
floats("show_image", 56.3, 5.4, image="open_ground", at=[CX, 710], height=470)
floats("fade_text", 61.3, 1.2, text="Aaron Ellis", x=410, y=1010, size=44, color="faint")
scribble("star_five", (160, 470), 0.3, "teal")
scribble("star_five", (940, 480), 0.28, "accent")
close_scene("change", 56.0, 63.0)

# =========================================================================
END = 63.0
storyboard = {
    "version": 2,
    "title": "SDH Reel - You're Not Broken (square)",
    "width": W, "height": H, "fps": 24,
    "content_duration": END,
    "safe_content_end": END - 0.4,
    "final_hold": 1.8,
    "pen_physics": "lift",
    "hand": "sprite",
    "chrome": "none",
    "text_font": "marker",
    "caption_font": "marker",
    "stroke_style": "round",
    "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
              "accent": [202, 83, 48], "teal": [31, 111, 112], "amber": [232, 163, 61]},
    "narration": {"transcript": TRANSCRIPT},
    "scenes": scenes,
}
OUT.write_text(json.dumps(storyboard, indent=2))
total = sum(len(s["actions"]) for s in scenes)
print(f"wrote {OUT.relative_to(ROOT)}  ({len(scenes)} scenes, {total} actions)")
