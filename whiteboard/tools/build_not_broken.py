#!/usr/bin/env python3
"""Generate the maximum-scribble 'You're Not Broken' vertical reel storyboard.

Each beat is its own SCENE (the renderer only draws the active scene's actions,
so the board wipes clean between beats). Within a scene, pen actions
(write_text, draw_asset, draw_fill) are packed sequentially so only one pen is
ever active; illustrations (show_image) and captions (fade_text) float on top.
Timing is a silent-master approximation; the narration retimer locks it to the
VO later.
"""
from __future__ import annotations

import json
from pathlib import Path

W, H = 1080, 1920
CX = W // 2
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "storyboards" / "sdh_not_broken_reel.json"

TRANSCRIPT = (
    "If you feel stuck, like something's wrong with you, read this. "
    "You are not broken. Your mind is doing exactly what it was built to do: "
    "protect you. Years ago some part of you drew a conclusion - I'm not safe, "
    "I'm not enough - and built everything on top of it. So the anxiety, the "
    "doubt, the stuck feeling? That's not a fault. It's an old protection, "
    "still running. You're not a knot that can't be undone. You're a thread "
    "that got tangled, and threads can be smoothed. You don't need fixing. You "
    "need to meet that old conclusion, and gently update it. You were never "
    "broken. You were protecting yourself. And that can change."
)

GAP = 0.12
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


def wash(color: str, side: str, y: float = 1120, h: int = 1120) -> None:
    """Soft colour band in a side margin, drawn behind the scene's content."""
    x = 190 if side == "left" else W - 190
    _actions.append({"id": _next_id(), "type": "show_image", "start": round(_scene_start + 0.05, 2),
                     "duration": 1.0, "requires_pen": False,
                     "image": f"wash_{color}", "at": [x, y], "height": h})


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


# =========================================================================
# S1  HOOK  0-7
open_scene("hook", 0.0)
wash("green", "left", y=1180)
wash("amber", "right", y=760, h=900)
pen("write_text", 1.4, text="YOU'RE NOT", x=210, y=360, size=64, width=5, color="ink")
pen("write_text", 1.2, text="BROKEN", x=250, y=470, size=96, width=8, color="accent")
scribble("circle_highlight", (CX, 470), 2.0, "teal", dur=0.7, width=6)
scribble("question_mark", (170, 250), 0.5, "faint")
scribble("question_mark", (900, 300), 0.42, "faint")
scribble("exclamation", (840, 560), 0.5, "accent")
scribble("star_five", (200, 620), 0.32, "teal")
scribble("star_five", (880, 660), 0.28, "teal")
close_scene("hook", 0.0, 7.0)

# S2  your mind is doing its job  7-15
open_scene("job", 7.0)
wash("teal", "left", y=1150)
wash("orange", "right", y=1250, h=980)
pen("write_text", 1.4, text="YOUR MIND IS", x=250, y=230, size=52, width=4, color="ink")
pen("write_text", 1.3, text="DOING ITS JOB", x=210, y=320, size=56, width=5, color="ink")
scribble("underline_swash", (CX, 430), 1.7, "teal", dur=0.6, width=6)
scribble("reaction_arrows", (CX, 560), 0.42, "accent", dur=0.5)
scribble("star_five", (180, 700), 0.3, "teal")
scribble("star_five", (900, 720), 0.3, "accent")
scribble("heart", (860, 620), 0.32, "accent")
floats("show_image", 7.3, 6.9, image="two_chairs", at=[CX, 1150], height=780)
floats("fade_text", 13.6, 0.9, text="not against you - for you", x=300, y=1640,
       size=34, italic=True, color="faint")
close_scene("job", 7.0, 15.0)

# S3  an old conclusion  15-24
open_scene("conclusion", 15.0)
wash("green", "right", y=1150)
wash("teal", "left", y=1250, h=980)
pen("write_text", 1.4, text="AN OLD", x=330, y=230, size=58, width=5, color="ink")
pen("write_text", 1.4, text="CONCLUSION", x=250, y=330, size=58, width=5, color="teal")
scribble("old_loop", (190, 260), 0.5, "faint", dur=0.5)
scribble("question_mark", (200, 1500), 0.5, "faint")
scribble("question_mark", (880, 1520), 0.45, "faint")
scribble("cracks", (760, 980), 0.7, "accent", dur=0.5)
floats("show_image", 15.3, 7.9, image="iceberg_mind", at=[CX, 1150], height=820)
floats("fade_text", 22.4, 0.9, text="I'm not safe. I'm not enough.", x=270, y=1640,
       size=36, italic=True, color="faint")
close_scene("conclusion", 15.0, 24.0)

# S4  not a fault, a guard  24-32
open_scene("guard", 24.0)
wash("amber", "left", y=1180)
wash("teal", "right", y=1200, h=980)
pen("write_text", 1.3, text="NOT A FAULT", x=290, y=230, size=56, width=5, color="ink")
pen("write_text", 1.2, text="A GUARD", x=340, y=330, size=64, width=6, color="accent")
scribble("circle_highlight", (CX + 10, 330), 1.7, "teal", dur=0.7, width=6)
scribble("star_five", (200, 560), 0.3, "teal")
scribble("exclamation", (880, 520), 0.45, "accent")
scribble("star_five", (900, 720), 0.28, "teal")
floats("show_image", 24.3, 6.9, image="key_keyhole", at=[CX, 1180], height=760)
floats("fade_text", 30.4, 0.9, text="an old protection, still running", x=290, y=1660,
       size=34, italic=True, color="faint")
close_scene("guard", 24.0, 32.0)

# S5  just tangled  32-41
open_scene("tangled", 32.0)
wash("green", "left", y=1200)
wash("teal", "right", y=1150, h=900)
pen("write_text", 1.2, text="NOT BROKEN.", x=280, y=230, size=54, width=5, color="faint")
scribble("cross_out", (CX + 10, 215), 1.5, "accent", dur=0.5, width=6)
pen("write_text", 1.3, text="JUST TANGLED", x=250, y=350, size=60, width=6, color="teal")
scribble("reaction_arrows", (CX, 560), 0.42, "teal", dur=0.5)
scribble("star_five", (200, 700), 0.32, "accent")
scribble("star_five", (880, 720), 0.3, "teal")
floats("show_image", 32.4, 7.9, image="tangled_thread", at=[CX, 1200], height=620)
floats("fade_text", 39.4, 0.9, text="and threads can be smoothed", x=300, y=1660,
       size=34, italic=True, color="faint")
close_scene("tangled", 32.0, 41.0)

# S6  you don't need fixing  41-49
open_scene("fixing", 41.0)
wash("orange", "left", y=1180)
wash("green", "right", y=1250, h=980)
pen("write_text", 1.3, text="YOU DON'T", x=320, y=230, size=56, width=5, color="ink")
pen("write_text", 1.3, text="NEED FIXING", x=270, y=330, size=60, width=6, color="ink")
scribble("underline_swash", (CX, 440), 1.7, "accent", dur=0.6, width=6)
pen("draw_asset", 0.7, asset="heart", at=[870, 600], scale=0.55, color="accent", width=6)
pen("draw_fill", 1.1, asset="heart", at=[870, 600], scale=0.55, width=18, color="accent")
scribble("star_five", (200, 620), 0.3, "teal")
floats("show_image", 41.3, 6.9, image="head_staircase", at=[CX, 1180], height=780)
floats("fade_text", 47.4, 0.9, text="meet it - and gently update it", x=300, y=1660,
       size=34, italic=True, color="faint")
close_scene("fixing", 41.0, 49.0)

# S7  you were protecting yourself  49-56
open_scene("protect", 49.0)
wash("green", "left", y=1200)
wash("amber", "right", y=1200, h=980)
pen("write_text", 1.3, text="YOU WERE", x=340, y=230, size=56, width=5, color="ink")
pen("write_text", 1.3, text="PROTECTING YOU", x=190, y=330, size=52, width=5, color="teal")
scribble("checkmark", (CX, 560), 1.1, "teal", dur=0.7, width=9)
scribble("star_five", (210, 700), 0.32, "accent")
scribble("star_five", (880, 680), 0.3, "teal")
floats("show_image_sequence", 49.3, 5.9,
       images=[f"seed_grow_{i}" for i in range(1, 7)], at=[CX, 1200], height=720)
close_scene("protect", 49.0, 56.0)

# S8  and that can change  56-63
open_scene("change", 56.0)
wash("teal", "left", y=1220)
wash("amber", "right", y=1220, h=980)
pen("write_text", 1.4, text="AND THAT", x=330, y=430, size=62, width=5, color="ink")
pen("write_text", 1.3, text="CAN CHANGE.", x=270, y=540, size=68, width=6, color="accent")
scribble("underline_swash", (CX, 665), 2.0, "teal", dur=0.7, width=6)
scribble("star_five", (210, 360), 0.3, "teal")
scribble("star_five", (880, 380), 0.28, "accent")
floats("show_image", 56.3, 5.4, image="open_ground", at=[CX, 1200], height=720)
floats("fade_text", 61.3, 1.2, text="Aaron Ellis", x=390, y=1680, size=46, color="faint")
close_scene("change", 56.0, 63.0)

# =========================================================================
END = 63.0
storyboard = {
    "version": 2,
    "title": "SDH Reel - You're Not Broken",
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
