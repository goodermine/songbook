"""Typed stroke geometry: StrokePath/Asset models and the AssetRegistry.

Assets live as JSON files under ``assets/`` — one file per asset — so new
videos change data, not renderer Python. Every asset is preflighted on load:
invalid geometry fails loudly here, before any expensive frame rendering.

JSON schema (one file per asset)::

    {
      "id": "person_one",
      "board": [1280, 720],
      "view_box": [x0, y0, x1, y1],
      "self_intersections": "forbid" | "allow",
      "strokes": [
        {
          "id": "head",
          "points": [[x, y], ...],
          "closed": true,
          "pen_lift_after": true,
          "arrowhead": [[x, y], [x, y], [x, y]] | null,
          "color_intent": null,
          "width_intent": null
        }
      ]
    }

``pen_lift_after`` declares the discontinuity to the next stroke; a stroke
with ``pen_lift_after: false`` must physically connect to the next one. The
Phase 3 timeline compiler turns these flags into explicit pen-up travel.
``arrowhead`` strokes are optional derived geometry (left leg, tip, right
leg); the storyboard action decides whether they are shown.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

Point = tuple[float, float]

EPSILON = 1e-6
SELF_INTERSECTION_POLICIES = ("forbid", "allow")


class GeometryError(RuntimeError):
    """Raised for missing assets or invalid stroke geometry."""


@dataclass(frozen=True)
class StrokePath:
    id: str
    points: tuple[Point, ...]
    closed: bool
    pen_lift_after: bool
    arrowhead: tuple[Point, ...] | None = None
    color_intent: str | None = None
    width_intent: int | None = None

    def length(self) -> float:
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))


@dataclass(frozen=True)
class Asset:
    id: str
    board: tuple[int, int]
    view_box: tuple[float, float, float, float]
    self_intersections: str
    strokes: tuple[StrokePath, ...]

    def pen_up_travel(self) -> float:
        """Total unmodelled pen-up distance between consecutive strokes."""
        return sum(math.dist(a.points[-1], b.points[0])
                   for a, b in zip(self.strokes, self.strokes[1:]))


def _points(raw: list, where: str) -> tuple[Point, ...]:
    points = []
    for value in raw:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise GeometryError(f"{where}: each point must be an [x, y] pair")
        x, y = float(value[0]), float(value[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise GeometryError(f"{where}: non-finite coordinate {value!r}")
        points.append((x, y))
    return tuple(points)


def parse_asset(data: dict, name: str) -> Asset:
    try:
        strokes = []
        for raw in data["strokes"]:
            where = f"asset {name!r} stroke {raw.get('id', '?')!r}"
            arrow = raw.get("arrowhead")
            strokes.append(StrokePath(
                id=str(raw["id"]),
                points=_points(raw["points"], where),
                closed=bool(raw["closed"]),
                pen_lift_after=bool(raw["pen_lift_after"]),
                arrowhead=_points(arrow, where + " arrowhead") if arrow else None,
                color_intent=raw.get("color_intent"),
                width_intent=raw.get("width_intent"),
            ))
        return Asset(
            id=str(data["id"]),
            board=(int(data["board"][0]), int(data["board"][1])),
            view_box=tuple(float(v) for v in data["view_box"]),
            self_intersections=str(data["self_intersections"]),
            strokes=tuple(strokes),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeometryError(f"Asset {name!r} is malformed: {exc!r}") from exc


def _segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    def orient(a: Point, b: Point, c: Point) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _stroke_self_intersects(stroke: StrokePath) -> bool:
    segments = list(zip(stroke.points, stroke.points[1:]))
    for i, (a1, a2) in enumerate(segments):
        for j in range(i + 2, len(segments)):
            b1, b2 = segments[j]
            # Segments sharing an endpoint (adjacent, or first/last of a
            # closed stroke) touch legitimately.
            if a1 in (b1, b2) or a2 in (b1, b2):
                continue
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def preflight_asset(asset: Asset) -> None:
    """Reject invalid geometry loudly, before rendering starts."""
    name = asset.id
    if not asset.strokes:
        raise GeometryError(f"Asset {name!r} has no strokes")
    if asset.self_intersections not in SELF_INTERSECTION_POLICIES:
        raise GeometryError(f"Asset {name!r} declares unknown self-intersection policy "
                            f"{asset.self_intersections!r}")
    width, height = asset.board
    if width <= 0 or height <= 0:
        raise GeometryError(f"Asset {name!r} has an invalid board size {asset.board}")

    xs: list[float] = []
    ys: list[float] = []
    for stroke in asset.strokes:
        where = f"asset {name!r} stroke {stroke.id!r}"
        if len(stroke.points) < 2:
            raise GeometryError(f"{where} needs at least 2 points")
        for a, b in zip(stroke.points, stroke.points[1:]):
            if math.dist(a, b) < EPSILON:
                raise GeometryError(f"{where} contains a zero-length segment at {a}")
        if stroke.closed and math.dist(stroke.points[0], stroke.points[-1]) > EPSILON:
            raise GeometryError(f"{where} is declared closed but does not close")
        if stroke.arrowhead is not None and len(stroke.arrowhead) < 2:
            raise GeometryError(f"{where} arrowhead needs at least 2 points")
        if asset.self_intersections == "forbid" and _stroke_self_intersects(stroke):
            raise GeometryError(f"{where} self-intersects but the asset declares 'forbid'")
        xs.extend(p[0] for p in stroke.points)
        ys.extend(p[1] for p in stroke.points)
        for point in stroke.arrowhead or ():
            if not (0 <= point[0] <= width and 0 <= point[1] <= height):
                raise GeometryError(f"{where} arrowhead leaves the board at {point}")

    bounds = (min(xs), min(ys), max(xs), max(ys))
    if any(abs(a - b) > 1e-3 for a, b in zip(bounds, asset.view_box)):
        raise GeometryError(f"Asset {name!r} view_box {asset.view_box} does not match "
                            f"computed stroke bounds {bounds}")
    if bounds[0] < 0 or bounds[1] < 0 or bounds[2] > width or bounds[3] > height:
        raise GeometryError(f"Asset {name!r} bounds {bounds} clip the {width}x{height} board")

    for current, following in zip(asset.strokes, asset.strokes[1:]):
        gap = math.dist(current.points[-1], following.points[0])
        if not current.pen_lift_after and gap > EPSILON:
            raise GeometryError(f"Asset {name!r} has an undeclared discontinuity of {gap:.1f}px "
                                f"between strokes {current.id!r} and {following.id!r}")


def transform_asset(asset: Asset, at: Point | None = None, scale: float = 1.0) -> Asset:
    """Place an asset: move its view-box centre to ``at`` and scale around it.

    Assets are authored at a natural position (library assets centre on the
    board); storyboard actions may reposition and resize them with
    ``"at": [x, y]`` and ``"scale"`` without touching the asset file.
    """
    if scale <= 0:
        raise GeometryError(f"Asset {asset.id!r}: scale must be positive, got {scale}")
    x0, y0, x1, y1 = asset.view_box
    center = ((x0 + x1) / 2, (y0 + y1) / 2)
    target = at if at is not None else center

    def place(point: Point) -> Point:
        return ((point[0] - center[0]) * scale + target[0],
                (point[1] - center[1]) * scale + target[1])

    strokes = tuple(StrokePath(
        id=stroke.id,
        points=tuple(place(p) for p in stroke.points),
        closed=stroke.closed,
        pen_lift_after=stroke.pen_lift_after,
        arrowhead=tuple(place(p) for p in stroke.arrowhead) if stroke.arrowhead else None,
        color_intent=stroke.color_intent,
        width_intent=stroke.width_intent,
    ) for stroke in asset.strokes)
    half_w, half_h = (x1 - x0) / 2 * scale, (y1 - y0) / 2 * scale
    return Asset(
        id=f"{asset.id}@{target[0]:g},{target[1]:g}x{scale:g}",
        board=asset.board,
        view_box=(target[0] - half_w, target[1] - half_h,
                  target[0] + half_w, target[1] + half_h),
        self_intersections=asset.self_intersections,
        strokes=strokes,
    )


class AssetRegistry:
    """Loads, validates and caches typed assets from a directory of JSON files."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self._cache: dict[str, Asset] = {}

    def names(self) -> list[str]:
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def load(self, name: str) -> Asset:
        if name in self._cache:
            return self._cache[name]
        path = self.directory / f"{name}.json"
        if not path.is_file():
            raise GeometryError(f"Unknown asset {name!r}: no file {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GeometryError(f"Asset {name!r} is not valid JSON: {exc}") from exc
        asset = parse_asset(data, name)
        if asset.id != name:
            raise GeometryError(f"Asset file {path.name} declares mismatched id {asset.id!r}")
        preflight_asset(asset)
        self._cache[name] = asset
        return asset

    def paths(self, name: str) -> list[list[Point]]:
        return [list(stroke.points) for stroke in self.load(name).strokes]
