"""Physical pen timeline: compile drawable assets into explicit pen events.

The legacy renderer allocated an action's duration across subpaths purely by
stroke length, so the nib teleported across every discontinuity (120 px
between pause bars, ~325 px inside a person, arrowheads popping in). This
compiler turns one drawable action into an ordered, gap-free sequence of

- ``stroke``    — pen down, tracing a stroke's points;
- ``arrowhead`` — pen down, tracing an arrowhead's legs (when the action
  enables arrowheads, heads are physically drawn, not popped in);
- ``travel``    — pen up, moving between disconnected geometry. Nothing is
  drawn and no pen is claimed: the hand lifts rather than teleports.

Time allocation: pen-down cost is stroke length at drawing speed; pen-up cost
is gap distance at ``TRAVEL_SPEED_RATIO``× drawing speed. Costs are scaled so
the events exactly fill the action's storyboard duration, then every travel
event is guaranteed at least ``MIN_TRAVEL_SECONDS`` of visible lift time
(taken proportionally from pen-down events) so a lift never flashes by in a
single frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from asset_registry import Asset, EPSILON

Point = tuple[float, float]

TRAVEL_SPEED_RATIO = 2.5     # pen-up travel is ~2.5x faster than drawing
MIN_TRAVEL_SECONDS = 0.08    # minimum visible pen-up travel / lift-lower time
SPEED_RANGE_PX_S = (200.0, 2000.0)  # sane pen-down speeds; outside -> warning


@dataclass(frozen=True)
class PenEvent:
    kind: str                 # "stroke" | "arrowhead" | "travel"
    start: float              # seconds from action start
    end: float
    stroke_index: int         # parent stroke index within the asset
    points: tuple[Point, ...] # traced geometry; (from, to) for travel

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def pen_down(self) -> bool:
        return self.kind in ("stroke", "arrowhead")


def _length(points: tuple[Point, ...]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def compile_drawable(asset: Asset, duration: float,
                     arrowheads: bool = False) -> tuple[list[PenEvent], dict]:
    """Compile one drawable action into contiguous pen events plus statistics."""
    if duration <= 0:
        raise ValueError(f"Cannot compile asset {asset.id!r} into duration {duration}")

    # (kind, stroke_index, points, cost) where cost is px-at-drawing-speed.
    segments: list[tuple[str, int, tuple[Point, ...], float]] = []
    position: Point | None = None

    def add_travel(index: int, target: Point) -> None:
        nonlocal position
        if position is not None:
            gap = math.dist(position, target)
            if gap > EPSILON:
                segments.append(("travel", index, (position, target), gap / TRAVEL_SPEED_RATIO))
        position = target

    for index, stroke in enumerate(asset.strokes):
        add_travel(index, stroke.points[0])
        segments.append(("stroke", index, stroke.points, _length(stroke.points)))
        position = stroke.points[-1]
        if arrowheads and stroke.arrowhead:
            add_travel(index, stroke.arrowhead[0])
            segments.append(("arrowhead", index, stroke.arrowhead, _length(stroke.arrowhead)))
            position = stroke.arrowhead[-1]

    total_cost = sum(cost for *_, cost in segments)
    if total_cost <= 0:
        raise ValueError(f"Asset {asset.id!r} compiled to zero drawable cost")
    seconds = [cost / total_cost * duration for *_, cost in segments]

    # Guarantee visible travel time, funded proportionally by pen-down events.
    travel_indices = [i for i, seg in enumerate(segments) if seg[0] == "travel"]
    deficit = sum(max(0.0, MIN_TRAVEL_SECONDS - seconds[i]) for i in travel_indices)
    down_indices = [i for i, seg in enumerate(segments) if seg[0] != "travel"]
    down_total = sum(seconds[i] for i in down_indices)
    if deficit > 0 and down_total > deficit * 2:
        for i in travel_indices:
            seconds[i] = max(seconds[i], MIN_TRAVEL_SECONDS)
        scale = (down_total - deficit) / down_total
        for i in down_indices:
            seconds[i] *= scale

    events: list[PenEvent] = []
    clock = 0.0
    for (kind, index, points, _), span in zip(segments, seconds):
        events.append(PenEvent(kind, clock, clock + span, index, tuple(points)))
        clock += span
    # Absorb float drift so the final event ends exactly on the duration.
    last = events[-1]
    events[-1] = PenEvent(last.kind, last.start, duration, last.stroke_index, last.points)

    pen_down_px = sum(_length(e.points) for e in events if e.pen_down)
    pen_down_s = sum(e.duration for e in events if e.pen_down)
    pen_up_px = sum(math.dist(e.points[0], e.points[1]) for e in events if not e.pen_down)
    draw_speed = pen_down_px / pen_down_s if pen_down_s else 0.0
    warnings = []
    if not SPEED_RANGE_PX_S[0] <= draw_speed <= SPEED_RANGE_PX_S[1]:
        warnings.append(f"pen-down speed {draw_speed:.0f}px/s outside "
                        f"{SPEED_RANGE_PX_S[0]:.0f}-{SPEED_RANGE_PX_S[1]:.0f}px/s")
    stats = {
        "events": len(events),
        "pen_down_px": pen_down_px,
        "pen_up_px": pen_up_px,
        "pen_down_s": pen_down_s,
        "pen_up_s": duration - pen_down_s,
        "draw_px_per_s": draw_speed,
        "warnings": warnings,
    }
    return events, stats


def serpentine_fill(polygon: list[Point], spacing: float, inset: float) -> list[list[Point]]:
    """Colouring-in strokes for a polygon: horizontal marker passes.

    Scanlines advance by ``spacing``; each in-polygon interval becomes one
    stroke, alternating direction row by row like a real marker filling a
    shape. ``inset`` pulls the passes inside the outline so the fill tucks
    under the drawn border instead of spilling past it.
    """
    if len(polygon) < 3:
        raise ValueError("Fill polygon needs at least 3 points")
    ys = [p[1] for p in polygon]
    y_top, y_bottom = min(ys) + inset, max(ys) - inset
    if y_bottom <= y_top:
        return []
    rows = max(1, round((y_bottom - y_top) / spacing))
    strokes: list[list[Point]] = []
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    for row in range(rows + 1):
        y = y_top + (y_bottom - y_top) * row / rows
        crossings = []
        for (px, py), (qx, qy) in edges:
            if (py <= y < qy) or (qy <= y < py):
                crossings.append(px + (y - py) * (qx - px) / (qy - py))
        crossings.sort()
        intervals = []
        for a, b in zip(crossings[0::2], crossings[1::2]):
            a, b = a + inset, b - inset
            if b - a > 2.0:
                intervals.append((a, b))
        if row % 2:
            intervals = [(b, a) for a, b in reversed(intervals)]
        for a, b in intervals:
            strokes.append([(a, y), (b, y)])
    return strokes


def smoothed_tangent(points: list[Point], arc_px: float = 22.0) -> Point:
    """Average direction over the trailing arc, for a stable marker angle.

    The raw segment tangent flips abruptly at polyline corners; averaging the
    last ``arc_px`` of travel keeps the wrist rotation bounded and smooth
    while remaining a pure function of the partial path (deterministic).
    """
    if len(points) < 2:
        return (1.0, 0.0)
    dx = dy = 0.0
    remaining = arc_px
    for a, b in zip(reversed(points[:-1]), reversed(points[1:])):
        segment = math.dist(a, b)
        if segment <= 0:
            continue
        take = min(segment, remaining)
        dx += (b[0] - a[0]) / segment * take
        dy += (b[1] - a[1]) / segment * take
        remaining -= take
        if remaining <= 0:
            break
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        a, b = points[-2], points[-1]
        return (b[0] - a[0], b[1] - a[1])
    return (dx, dy)
