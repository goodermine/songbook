#!/usr/bin/env python3
"""Generate the 'You're Not Broken' SQUARE reel - fully hand-drawn.

Whiteboard rule: nothing pops. Every element is drawn by the hand, sequentially
(only one pen is ever active):
  - headlines + captions: hand-written marker text
  - illustrations: sketch_image (revealed behind the moving nib)
  - colour shading: hand-scribbled draw_fill patches in pastel tones
  - doodles: drawn as before

Scene windows auto-size to the drawing time; the narration retimer then maps
each scene onto its spoken segment.
"""
from __future__ import annotations

import json
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
scenes: list[dict] = []
_actions: list[dict] = []
_t = 0.0          # global timeline cursor
_scene_start = 0.0
_uid = 0


def _nid() -> str:
    global _uid
    _uid += 1
    return f"a{_uid:03d}"


def open_scene() -> None:
    global _actions, _t, _scene_start
    _actions = []
    _scene_start = _t
    _t = round(_t + 0.2, 2)


def close_scene(sid: str) -> None:
    global _t
    scenes.append({"id": sid, "start": round(_scene_start, 2),
                   "end": round(_t + 0.25, 2), "actions": _actions})
    _t = round(_t + 0.25, 2)


def pen(kind: str, duration: float, **fields) -> None:
    global _t
    _actions.append({"id": _nid(), "type": kind, "start": round(_t, 2),
                     "duration": duration, "requires_pen": True, **fields})
    _t = round(_t + duration + GAP, 2)


def text(txt, x, y, size, color, dur, width=5):
    pen("write_text", dur, text=txt, x=x, y=y, size=size, width=width, color=color)


def caption(txt, y, dur=1.2, size=30, color="faint"):
    pen("write_text", dur, text=txt, x=None, y=y, size=size, width=3, color=color, align="center")


def sketch(image, at, height, dur):
    pen("sketch_image", dur, image=image, at=list(at), height=height)


def doodle(asset, at, scale, color, dur=0.4, width=5):
    pen("draw_asset", dur, asset=asset, at=list(at), scale=scale, color=color, width=width)


def shade(cx, cy, color, w=230, h=165, dur=0.7, width=17):
    # Octagon-ish blob; a narrower fill width leaves the serpentine passes
    # visible so it reads as loose scribbled shading, not a solid sticker.
    poly = [[cx - w / 2, cy - h / 6], [cx - w / 3, cy - h / 2], [cx + w / 3, cy - h / 2],
            [cx + w / 2, cy - h / 6], [cx + w / 2, cy + h / 6], [cx + w / 3, cy + h / 2],
            [cx - w / 3, cy + h / 2], [cx - w / 2, cy + h / 6]]
    pen("draw_fill", dur, polygon=poly, width=width, color=color)


# =========================================================================
# S1  HOOK  (voice lingers here; leisurely draw with holds after retime)
open_scene()
shade(180, 470, "pgreen", w=240, h=200, dur=0.7)
shade(900, 720, "ppeach", w=220, h=180, dur=0.7)
text("YOU'RE NOT", 250, 400, 66, "ink", 1.4)
text("BROKEN", 290, 515, 98, "accent", 1.3, width=8)
doodle("circle_highlight", (CX, 560), 2.0, "teal", dur=0.7, width=6)
doodle("question_mark", (180, 250), 0.5, "faint")
doodle("question_mark", (880, 300), 0.42, "faint")
doodle("exclamation", (930, 560), 0.5, "accent")
doodle("star_five", (150, 700), 0.32, "teal")
close_scene("hook")

# S2  your mind is doing its job
open_scene()
shade(160, 720, "pmint", dur=0.6)
text("YOUR MIND IS", 260, 95, 52, "ink", 1.3, width=4)
text("DOING ITS JOB", 230, 185, 56, "ink", 1.3)
doodle("underline_swash", (CX, 300), 1.6, "teal", dur=0.6, width=6)
sketch("two_chairs", (CX, 700), 520, 1.9)
caption("for you - not against you", 1000)
close_scene("job")

# S3  an old conclusion
open_scene()
shade(920, 470, "psky", dur=0.6)
shade(160, 780, "psage", dur=0.6)
text("AN OLD", 360, 95, 58, "ink", 1.3)
text("CONCLUSION", 280, 190, 58, "teal", 1.4)
doodle("old_loop", (150, 250), 0.45, "faint", dur=0.5)
sketch("iceberg_mind", (CX, 700), 540, 2.1)
caption("I'm not safe. I'm not enough.", 1005)
close_scene("conclusion")

# S4  not a fault, a guard
open_scene()
shade(170, 470, "pamber", dur=0.6)
text("NOT A FAULT", 310, 95, 54, "ink", 1.3)
text("A GUARD", 370, 190, 64, "accent", 1.2, width=6)
doodle("circle_highlight", (CX + 10, 205), 1.7, "teal", dur=0.7, width=6)
sketch("key_keyhole", (CX, 700), 500, 1.9)
caption("an old protection, still running", 1010)
close_scene("guard")

# S5  just tangled
open_scene()
shade(920, 760, "pgreen", dur=0.6)
text("NOT BROKEN.", 300, 95, 52, "faint", 1.2)
doodle("cross_out", (CX + 10, 85), 1.5, "accent", dur=0.5, width=6)
text("JUST TANGLED", 270, 195, 60, "teal", 1.3, width=6)
sketch("tangled_thread", (CX, 720), 440, 1.7)
caption("threads can be smoothed", 1010)
close_scene("tangled")

# S6  you don't need fixing
open_scene()
shade(150, 760, "pmint", dur=0.6)
text("YOU DON'T", 350, 95, 56, "ink", 1.3)
text("NEED FIXING", 300, 190, 60, "ink", 1.3, width=6)
doodle("underline_swash", (CX, 300), 1.6, "accent", dur=0.6, width=6)
sketch("head_staircase", (CX, 700), 500, 1.9)
doodle("heart", (935, 470), 0.5, "accent", dur=0.6, width=6)
caption("just meet it, and update it", 1010)
close_scene("fixing")

# S7  you were protecting yourself  (tight segment - keep lean)
open_scene()
shade(920, 500, "psage", dur=0.6)
text("YOU WERE", 370, 95, 56, "ink", 1.3)
text("PROTECTING YOU", 210, 190, 52, "teal", 1.3)
doodle("checkmark", (CX, 330), 1.0, "teal", dur=0.7, width=9)
sketch("seed_grow_6", (CX, 730), 430, 1.6)
close_scene("protect")

# S8  and that can change
open_scene()
shade(170, 470, "ppeach", dur=0.6)
text("AND THAT", 360, 110, 60, "ink", 1.3)
text("CAN CHANGE.", 290, 210, 66, "accent", 1.3, width=6)
doodle("underline_swash", (CX, 320), 1.9, "teal", dur=0.7, width=6)
sketch("open_ground", (CX, 700), 470, 1.7)
caption("Aaron Ellis", 1000, size=44, color="faint", dur=1.2)
close_scene("change")

# =========================================================================
END = round(_t, 2)
storyboard = {
    "version": 2,
    "title": "SDH Reel - You're Not Broken (square, hand-drawn)",
    "width": W, "height": H, "fps": 24,
    "content_duration": END,
    "safe_content_end": round(END - 0.4, 2),
    "final_hold": 1.8,
    "pen_physics": "lift",
    "hand": "sprite",
    "chrome": "none",
    "text_font": "marker",
    "caption_font": "marker",
    "stroke_style": "round",
    "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
              "accent": [202, 83, 48], "teal": [31, 111, 112], "amber": [232, 163, 61],
              "pgreen": [178, 206, 168], "pmint": [190, 216, 202], "psage": [196, 214, 180],
              "psky": [192, 210, 214], "ppeach": [234, 208, 186], "pamber": [232, 216, 172]},
    "narration": {"transcript": TRANSCRIPT},
    "scenes": scenes,
}
OUT.write_text(json.dumps(storyboard, indent=2))
total = sum(len(s["actions"]) for s in scenes)
print(f"wrote {OUT.relative_to(ROOT)}  ({len(scenes)} scenes, {total} actions, {END}s silent)")
