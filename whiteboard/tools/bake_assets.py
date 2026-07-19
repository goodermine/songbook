#!/usr/bin/env python3
"""Bake the legacy procedural asset geometry into typed assets/*.json files.

This tool is the provenance of the Phase 2 asset migration: it contains the
exact procedural generators that previously lived inside the renderer's
``asset_paths()`` switch, evaluates them once, computes the typed metadata
(closed flags, pen lifts, view boxes, arrowhead legs) and writes one JSON file
per asset. Rendering the baked data is byte-identical to the old procedural
path — the golden-frame tests enforce that.

Run from the whiteboard directory::

    python3 tools/bake_assets.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

from asset_registry import EPSILON, AssetRegistry  # noqa: E402

BOARD = (1280, 720)
ASSET_DIR = WHITEBOARD_ROOT / "assets"

# Arrowhead legs match the legacy renderer formula exactly (size 23, ±0.55 rad).
ARROW_SIZE = 23
ARROW_SPREAD = 0.55


def person_paths(cx: float, cy: float) -> list[tuple[str, list]]:
    head = [(cx + math.cos(a) * 35, cy - 105 + math.sin(a) * 35)
            for a in np.linspace(-math.pi / 2, 3 * math.pi / 2, 36)]
    return [
        ("head", head),
        ("torso", [(cx, cy - 70), (cx, cy + 15)]),
        ("arm_left", [(cx, cy - 35), (cx - 55, cy - 2)]),
        ("arm_right", [(cx, cy - 35), (cx + 55, cy - 2)]),
        ("leg_left", [(cx, cy + 15), (cx - 48, cy + 83)]),
        ("leg_right", [(cx, cy + 15), (cx + 48, cy + 83)]),
    ]


def quadratic_arrow(x1, y1, x2, y2, bend=0.0, samples=45) -> list:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    nx, ny = -(y2 - y1), x2 - x1
    length = math.hypot(nx, ny) or 1.0
    cx, cy = mx + nx / length * bend, my + ny / length * bend
    return [((1 - u) ** 2 * x1 + 2 * (1 - u) * u * cx + u * u * x2,
             (1 - u) ** 2 * y1 + 2 * (1 - u) * u * cy + u * u * y2)
            for u in np.linspace(0, 1, samples)]


ASSETS: dict[str, list[tuple[str, list]]] = {
    "person_one": person_paths(390, 370),
    "person_two": person_paths(640, 365),
    "cracks": [
        ("main", [(390, 268), (374, 293), (392, 310)]),
        ("branch_left", [(392, 310), (370, 337)]),
        ("branch_right", [(392, 310), (414, 339)]),
    ],
    "cross_out": [
        ("slash_a", [(665, 105), (1025, 160)]),
        ("slash_b", [(1010, 92), (685, 175)]),
    ],
    "rehearsal_loop": [
        ("loop", [(640 + math.cos(a) * 235, 360 + math.sin(a) * 190)
                  for a in np.linspace(-.55, math.pi * 1.73, 100)]),
    ],
    "reaction_arrows": [
        (f"arrow_{i + 1}", quadratic_arrow(x - 75, 310, x + 75, 310, -28))
        for i, x in enumerate([205, 420, 635, 850, 1065])
    ],
    "identity_box": [
        ("box", [(330, 160), (950, 160), (950, 395), (330, 395), (330, 160)]),
    ],
    "identity_break": [
        ("break", [(640, 158), (610, 210), (662, 255), (620, 312), (650, 395)]),
    ],
    "old_loop": [
        ("loop", [(345 + math.cos(a) * 125, 330 + math.sin(a) * 115)
                  for a in np.linspace(0, math.pi * 2, 80)]),
    ],
    "pause_symbol": [
        ("bar_left", [(322, 275), (322, 385)]),
        ("bar_right", [(370, 275), (370, 385)]),
    ],
    "choice_path": [
        ("path", [(465, 425), (540, 395), (615, 420), (700, 340), (790, 355),
                  (875, 250), (1010, 215)]),
    ],
}

# cross_out's two slashes deliberately cross each other; everything else must
# be free of self-intersections. (The policy is checked within strokes;
# between-stroke contact such as limbs meeting a torso is always legitimate.)
SELF_INTERSECTIONS = {name: "forbid" for name in ASSETS}
SELF_INTERSECTIONS["cross_out"] = "allow"


def arrowhead_legs(points: list) -> list:
    tip, previous = points[-1], points[-2]
    angle = math.atan2(tip[1] - previous[1], tip[0] - previous[0])
    left = (tip[0] - math.cos(angle - ARROW_SPREAD) * ARROW_SIZE,
            tip[1] - math.sin(angle - ARROW_SPREAD) * ARROW_SIZE)
    right = (tip[0] - math.cos(angle + ARROW_SPREAD) * ARROW_SIZE,
             tip[1] - math.sin(angle + ARROW_SPREAD) * ARROW_SIZE)
    return [left, tip, right]


def bake_asset(name: str, named_paths: list[tuple[str, list]]) -> dict:
    strokes = []
    xs: list[float] = []
    ys: list[float] = []
    for index, (stroke_id, raw_points) in enumerate(named_paths):
        points = [(float(x), float(y)) for x, y in raw_points]
        xs.extend(p[0] for p in points)
        ys.extend(p[1] for p in points)
        is_last = index == len(named_paths) - 1
        next_start = None if is_last else named_paths[index + 1][1][0]
        gap = 0.0 if is_last else math.dist(points[-1], (float(next_start[0]), float(next_start[1])))
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
        "self_intersections": SELF_INTERSECTIONS[name],
        "strokes": strokes,
    }


def main() -> None:
    ASSET_DIR.mkdir(exist_ok=True)
    for name, named_paths in ASSETS.items():
        data = bake_asset(name, named_paths)
        path = ASSET_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        print(f"baked {path.relative_to(WHITEBOARD_ROOT)}: "
              f"{len(data['strokes'])} strokes")
    registry = AssetRegistry(ASSET_DIR)
    for name in registry.names():
        registry.load(name)  # preflight everything we just wrote
    print(f"preflight passed for {len(registry.names())} assets")


if __name__ == "__main__":
    main()
