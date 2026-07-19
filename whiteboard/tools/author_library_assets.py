#!/usr/bin/env python3
"""Author the reusable doodle library into assets/*.json.

Every library asset is authored centred on the board (640, 360) at a natural
size; storyboards position and resize them per action with ``"at": [x, y]``
and ``"scale"``. Geometry is parametric here, but ships as plain JSON data —
new videos never require Python edits.

Run from the whiteboard directory::

    python3 tools/author_library_assets.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from asset_registry import EPSILON, AssetRegistry  # noqa: E402
from bake_assets import BOARD, arrowhead_legs  # noqa: E402

ASSET_DIR = WHITEBOARD_ROOT / "assets"
CX, CY = 640.0, 360.0


def circle(cx: float, cy: float, r: float, start: float = 0.0,
           end: float = 2 * math.pi, samples: int = 48) -> list:
    return [(cx + math.cos(a) * r, cy + math.sin(a) * r)
            for a in [start + (end - start) * i / (samples - 1) for i in range(samples)]]


def lightbulb() -> list:
    bottom = math.pi / 2  # y-down: +90 deg is the bottom of the circle
    bulb = circle(CX, CY - 40, 62, bottom + 0.55, bottom - 0.55 + 2 * math.pi, 44)
    rays = []
    for angle in (-math.pi / 2, -math.pi / 2 - 0.85, -math.pi / 2 + 0.85):
        rays.append((f"ray_{len(rays)}",
                     [(CX + math.cos(angle) * 82, CY - 40 + math.sin(angle) * 82),
                      (CX + math.cos(angle) * 108, CY - 40 + math.sin(angle) * 108)]))
    return [
        ("bulb", bulb),
        ("base_top", [(CX - 26, CY + 38), (CX + 26, CY + 38)]),
        ("base_mid", [(CX - 23, CY + 56), (CX + 23, CY + 56)]),
        ("base_cap", [(CX - 16, CY + 72), (CX + 16, CY + 72)]),
        *rays,
    ]


def speech_bubble() -> list:
    # Chamfered rectangle with a tail toward the lower-left, one stroke.
    left, right, top, bottom, cut = CX - 235, CX + 235, CY - 105, CY + 65, 26
    tail_tip = (left + 65, bottom + 52)
    outline = [
        tail_tip, (left + 105, bottom),
        (left + cut, bottom), (left, bottom - cut),
        (left, top + cut), (left + cut, top),
        (right - cut, top), (right, top + cut),
        (right, bottom - cut), (right - cut, bottom),
        (left + 150, bottom), tail_tip,
    ]
    return [("outline", outline)]


def thought_bubble() -> list:
    cloud = [(CX + math.cos(a) * (86 + 16 * math.sin(6 * a)),
              CY - 45 + math.sin(a) * (66 + 14 * math.sin(6 * a)))
             for a in [2 * math.pi * i / 72 for i in range(73)]]
    return [
        ("cloud", cloud),
        ("puff_big", circle(CX - 105, CY + 68, 15, samples=20)),
        ("puff_small", circle(CX - 140, CY + 102, 8, samples=14)),
    ]


def star_five() -> list:
    points = []
    for i in range(6):
        a = -math.pi / 2 + i * 4 * math.pi / 5  # {5/2} star polygon
        points.append((CX + math.cos(a) * 100, CY + math.sin(a) * 100))
    return [("star", points)]


def heart() -> list:
    points = []
    for i in range(61):
        t = 2 * math.pi * i / 60
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((CX + x * 6.5, CY - y * 6.5 + 10))
    return [("heart", points)]


def target() -> list:
    return [
        ("ring_outer", circle(CX, CY, 95)),
        ("ring_inner", circle(CX, CY, 55, samples=36)),
        ("bull", circle(CX, CY, 12, samples=14)),
    ]


def clock() -> list:
    ticks = []
    for i, a in enumerate([-math.pi / 2, 0.0, math.pi / 2, math.pi]):
        ticks.append((f"tick_{i}",
                      [(CX + math.cos(a) * 80, CY + math.sin(a) * 80),
                       (CX + math.cos(a) * 93, CY + math.sin(a) * 93)]))
    hour = -math.pi / 3          # pointing toward 2 o'clock
    minute = -0.85 * math.pi     # pointing toward 10 o'clock
    return [
        ("face", circle(CX, CY, 95, samples=56)),
        *ticks,
        ("hand_hour", [(CX, CY), (CX + math.cos(hour) * 42, CY + math.sin(hour) * 42)]),
        ("hand_minute", [(CX, CY), (CX + math.cos(minute) * 68, CY + math.sin(minute) * 68)]),
    ]


def magnifier() -> list:
    a = math.pi / 4
    rim = (CX - 30 + math.cos(a) * 62, CY - 30 + math.sin(a) * 62)
    return [
        ("lens", circle(CX - 30, CY - 30, 62)),
        ("handle", [rim, (rim[0] + 66, rim[1] + 66)]),
    ]


def gear() -> list:
    teeth = []
    r_in, r_out = 68, 94
    for i in range(8):
        base = i * math.pi / 4
        for radius, offset in [(r_in, 0.0), (r_in, 0.28), (r_out, 0.36),
                               (r_out, 0.62), (r_in, 0.70)]:
            a = base + offset
            teeth.append((CX + math.cos(a) * radius, CY + math.sin(a) * radius))
    teeth.append(teeth[0])
    return [("ring", teeth), ("hub", circle(CX, CY, 26, samples=24))]


def mountain_flag() -> list:
    return [
        ("mountain", [(CX - 150, CY + 120), (CX, CY - 120), (CX + 150, CY + 120)]),
        ("pole", [(CX, CY - 120), (CX, CY - 180)]),
        ("flag", [(CX, CY - 180), (CX + 52, CY - 165), (CX, CY - 150)]),
    ]


def question_mark() -> list:
    hook = circle(CX, CY - 55, 58, math.pi, 2 * math.pi, 26)
    hook += [(CX + 55, CY - 30), (CX + 42, CY - 6), (CX + 16, CY + 12), (CX, CY + 35)]
    return [("hook", hook), ("dot", circle(CX, CY + 72, 9, samples=12))]


def exclamation() -> list:
    return [
        ("bar", [(CX, CY - 110), (CX - 2, CY - 30), (CX, CY + 20)]),
        ("dot", circle(CX, CY + 68, 10, samples=12)),
    ]


def circle_highlight() -> list:
    # Hand-circled emphasis: an ellipse that overshoots and spirals slightly
    # outward on the second pass, like a real marker circling a word.
    points = []
    total = 2 * math.pi + 0.9
    for i in range(85):
        a = -0.4 + total * i / 84
        grow = 1.0 + 0.07 * max(0.0, (a - 2 * math.pi + 0.4) / 0.9)
        points.append((CX + math.cos(a) * 170 * grow, CY + math.sin(a) * 72 * grow))
    return [("loop", points)]


def underline_swash() -> list:
    points = [(480 + x, CY + 10 * math.sin(2 * math.pi * x / 80)) for x in range(0, 321, 8)]
    return [("wave", points)]


def straw_glass() -> list:
    # A glass of water with a drinking straw and rising bubbles: the signature
    # semi-occluded vocal tract exercise.
    return [
        ("glass", [(CX - 52, CY - 70), (CX - 40, CY + 70), (CX + 40, CY + 70), (CX + 52, CY - 70)]),
        ("water", [(CX - 46, CY - 30), (CX + 46, CY - 30)]),
        ("straw", [(CX + 62, CY - 112), (CX - 12, CY + 58)]),
        ("bubble_a", circle(CX - 14, CY + 12, 7, samples=12)),
        ("bubble_b", circle(CX + 6, CY - 6, 5, samples=10)),
        ("bubble_c", circle(CX - 4, CY - 20, 4, samples=10)),
    ]


def stone_arch() -> list:
    # A voussoir stone arch with an emphasised keystone at the crown - the
    # Strategic Dialogue Hypnotherapy model of a problem.
    c = (CX, CY + 70)
    outer, inner = 200.0, 125.0

    def joint(angle_frac: float, sid: str) -> tuple:
        a = math.pi * angle_frac
        return (sid, [(c[0] + math.cos(a) * inner, c[1] + math.sin(a) * inner),
                      (c[0] + math.cos(a) * outer, c[1] + math.sin(a) * outer)])

    return [
        ("outer_arc", circle(c[0], c[1], outer, math.pi, 2 * math.pi, 40)),
        ("inner_arc", circle(c[0], c[1], inner, math.pi, 2 * math.pi, 30)),
        ("pier_left_outer", [(c[0] - outer, c[1]), (c[0] - outer, c[1] + 130)]),
        ("pier_left_inner", [(c[0] - inner, c[1]), (c[0] - inner, c[1] + 130)]),
        ("pier_right_inner", [(c[0] + inner, c[1]), (c[0] + inner, c[1] + 130)]),
        ("pier_right_outer", [(c[0] + outer, c[1]), (c[0] + outer, c[1] + 130)]),
        ("ground", [(c[0] - outer - 30, c[1] + 130), (c[0] + outer + 30, c[1] + 130)]),
        joint(1.15, "joint_a"),
        joint(1.30, "joint_b"),
        joint(1.70, "joint_c"),
        joint(1.85, "joint_d"),
        joint(1.44, "keystone_left"),
        joint(1.56, "keystone_right"),
    ]


def music_note() -> list:
    # Eighth note: head, stem, flag.
    return [
        ("head", circle(CX - 24, CY + 66, 17, samples=18)),
        ("stem", [(CX - 7, CY + 66), (CX - 7, CY - 80)]),
        ("flag", [(CX - 7, CY - 80), (CX + 18, CY - 62), (CX + 30, CY - 34), (CX + 22, CY - 6)]),
    ]


LIBRARY = {
    "lightbulb": (lightbulb, "forbid"),
    "speech_bubble": (speech_bubble, "forbid"),
    "thought_bubble": (thought_bubble, "forbid"),
    "star_five": (star_five, "allow"),
    "heart": (heart, "forbid"),
    "target": (target, "forbid"),
    "clock": (clock, "forbid"),
    "magnifier": (magnifier, "forbid"),
    "gear": (gear, "forbid"),
    "mountain_flag": (mountain_flag, "forbid"),
    "question_mark": (question_mark, "forbid"),
    "exclamation": (exclamation, "forbid"),
    "circle_highlight": (circle_highlight, "allow"),
    "underline_swash": (underline_swash, "forbid"),
    "straw_glass": (straw_glass, "allow"),
    "music_note": (music_note, "forbid"),
    "stone_arch": (stone_arch, "forbid"),
}


def bake(name: str, named_paths: list, policy: str) -> dict:
    strokes = []
    xs, ys = [], []
    for index, (stroke_id, raw) in enumerate(named_paths):
        points = [(float(x), float(y)) for x, y in raw]
        if len(points) > 2 and math.dist(points[0], points[-1]) <= 1e-6:
            points[-1] = points[0]  # snap closed strokes exactly shut
        xs.extend(p[0] for p in points)
        ys.extend(p[1] for p in points)
        is_last = index == len(named_paths) - 1
        gap = 0.0 if is_last else math.dist(
            points[-1], tuple(map(float, named_paths[index + 1][1][0])))
        strokes.append({
            "id": stroke_id,
            "points": [[x, y] for x, y in points],
            "closed": math.dist(points[0], points[-1]) <= EPSILON,
            "pen_lift_after": (not is_last) and gap > EPSILON,
            "arrowhead": [[float(x), float(y)] for x, y in arrowhead_legs(points)],
            "color_intent": None,
            "width_intent": None,
        })
    return {
        "id": name,
        "board": list(BOARD),
        "view_box": [min(xs), min(ys), max(xs), max(ys)],
        "self_intersections": policy,
        "strokes": strokes,
    }


def main() -> None:
    for name, (generator, policy) in LIBRARY.items():
        data = bake(name, generator(), policy)
        (ASSET_DIR / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n",
                                                encoding="utf-8")
        print(f"authored assets/{name}.json ({len(data['strokes'])} strokes)")
    registry = AssetRegistry(ASSET_DIR)
    for name in registry.names():
        registry.load(name)
    print(f"preflight passed for {len(registry.names())} assets")


if __name__ == "__main__":
    main()
