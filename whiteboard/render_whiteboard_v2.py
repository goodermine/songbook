#!/usr/bin/env python3
"""Validated single-pen whiteboard renderer driven by storyboard_v2.json."""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

from asset_registry import (Asset, AssetRegistry, GeometryError, StrokePath,
                            preflight_asset, transform_asset)
from hand_rig import HandRigError, default_rig
from text_strokes import TextStrokeError, strokes_bounds, text_to_strokes
from timeline import PenEvent, compile_drawable, serpentine_fill, smoothed_tangent


ROOT = Path(__file__).resolve().parent
STORYBOARD_DEFAULT = ROOT / "storyboard_v2.json"
ASSET_DIR = ROOT / "assets"
IMAGE_DIR = ROOT / "assets" / "images"
AUDIO_MODES = ("none", "chalk", "narration", "mix")
PEN_PHYSICS_MODES = ("legacy", "lift")
HAND_MODES = ("procedural", "sprite")
CHROME_MODES = ("legacy", "none")

REGISTRY = AssetRegistry(ASSET_DIR)
MARKER_FONT_PATH = ROOT / "assets" / "fonts" / "PermanentMarker-Regular.ttf"
TEXT_FONTS = ("hershey", "marker")
FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/opentype/urw-base35/URWBookman-Light.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ],
    "bold": [
        "/usr/share/fonts/opentype/urw-base35/URWBookman-Demi.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ],
    "italic": [
        "/usr/share/fonts/opentype/urw-base35/URWBookman-LightItalic.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ],
}


class BuildError(RuntimeError):
    pass


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def action_progress(action: dict[str, Any], time_s: float) -> float:
    return smooth((time_s - float(action["start"])) / float(action["duration"]))


def resolve_font_path(kind: str) -> str:
    for candidate in FONT_CANDIDATES[kind]:
        if Path(candidate).is_file():
            return candidate
    raise BuildError(f"No usable {kind} font found; checked {FONT_CANDIDATES[kind]}")


@lru_cache(maxsize=64)
def load_font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    kind = "bold" if bold else "italic" if italic else "regular"
    return ImageFont.truetype(resolve_font_path(kind), size)


@lru_cache(maxsize=4)
def _marker_cap_ratio() -> float:
    """Cap-height / point-size ratio of the bundled marker font."""
    probe = ImageFont.truetype(str(MARKER_FONT_PATH), 100)
    box = probe.getbbox("H")
    return (box[3] - box[1]) / 100.0


@lru_cache(maxsize=64)
def marker_font(cap_height: int) -> ImageFont.FreeTypeFont:
    """Marker font sized so capitals stand ``cap_height`` px tall, matching
    the Hershey layout contract (y = cap top, size = cap height)."""
    if not MARKER_FONT_PATH.is_file():
        raise BuildError(f"Marker font not found: {MARKER_FONT_PATH}")
    return ImageFont.truetype(str(MARKER_FONT_PATH), max(4, round(cap_height / _marker_cap_ratio())))


@dataclass(frozen=True)
class PenPose:
    owner: str
    tip: tuple[float, float]
    tangent: tuple[float, float]
    stroke: str | None = None
    contact: bool = True  # False while the hand glides between strokes, lifted


class FrameState:
    """Collects one global pen pose and rejects any runtime collision."""

    def __init__(self, image: Image.Image) -> None:
        self.image = image
        self.draw = ImageDraw.Draw(image)
        self.pen: PenPose | None = None

    def claim_pen(self, owner: str, tip: tuple[float, float], tangent: tuple[float, float],
                  stroke: str | None = None, contact: bool = True) -> None:
        if self.pen is not None and self.pen.owner != owner:
            raise BuildError(f"Multiple active pens at runtime: {self.pen.owner!r} and {owner!r}")
        length = math.hypot(*tangent) or 1.0
        self.pen = PenPose(owner, tip, (tangent[0] / length, tangent[1] / length), stroke, contact)

    def overlay_pen(self) -> None:
        if self.pen:
            draw_marker(self.draw, self.pen.tip, self.pen.tangent)


def draw_marker(draw: ImageDraw.ImageDraw, tip: tuple[float, float], tangent: tuple[float, float]) -> None:
    # Rotate the marker with the stroke while maintaining a natural wrist offset.
    path_angle = math.atan2(tangent[1], tangent[0])
    angle = path_angle - 0.58
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx
    x, y = tip
    back = (x - dx * 88, y - dy * 88)
    marker = [
        (x + px * 6, y + py * 6),
        (back[0] + px * 10, back[1] + py * 10),
        (back[0] - px * 10, back[1] - py * 10),
        (x - px * 6, y - py * 6),
    ]
    draw.polygon(marker, fill=(64, 70, 72), outline=(26, 30, 32))
    palm = (back[0] - dx * 22, back[1] - dy * 22)
    draw.ellipse((palm[0] - 28, palm[1] - 22, palm[0] + 31, palm[1] + 24),
                 fill=(214, 164, 125), outline=(123, 82, 58), width=2)
    for offset in (-13, 0, 13):
        fx, fy = back[0] + px * offset, back[1] + py * offset
        draw.line((palm[0], palm[1], fx, fy), fill=(169, 113, 80), width=5)


def path_length(points: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def partial_path(points: list[tuple[float, float]], distance: float) -> tuple[list[tuple[float, float]], tuple[float, float], tuple[float, float]]:
    if not points:
        return [], (0.0, 0.0), (1.0, 0.0)
    if len(points) == 1:
        return points[:], points[0], (1.0, 0.0)
    output = [points[0]]
    remaining = max(0.0, distance)
    last_tangent = (points[1][0] - points[0][0], points[1][1] - points[0][1])
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        tangent = (b[0] - a[0], b[1] - a[1])
        last_tangent = tangent
        if remaining >= length:
            output.append(b)
            remaining -= length
            continue
        ratio = remaining / length if length else 0.0
        tip = (a[0] + tangent[0] * ratio, a[1] + tangent[1] * ratio)
        output.append(tip)
        return output, tip, tangent
    return output, points[-1], last_tangent


def sketch_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], width: int, seed: int) -> None:
    if len(points) < 2:
        return
    rng = random.Random(seed)
    for pass_no in range(2):
        jittered = [(x + rng.uniform(-1.7, 1.7), y + rng.uniform(-1.7, 1.7)) for x, y in points]
        draw.line(jittered, fill=color, width=max(1, width - pass_no * 2), joint="curve")


def compound_paths(state: FrameState, owner: str, paths: list[list[tuple[float, float]]], p: float,
                   color: tuple[int, int, int], width: int, seed: int,
                   arrowheads: bool = False, last_color: tuple[int, int, int] | None = None,
                   arrowhead_paths: list[list[tuple[float, float]] | None] | None = None) -> None:
    """Draw compound paths at uniform physical velocity with one global pen."""
    lengths = [path_length(path) for path in paths]
    target = clamp(p) * sum(lengths)
    active_claimed = False
    for index, (path, length) in enumerate(zip(paths, lengths)):
        path_color = last_color if last_color and index == len(paths) - 1 else color
        if target >= length:
            sketch_line(state.draw, path, path_color, width, seed + index)
            if arrowheads and arrowhead_paths and arrowhead_paths[index]:
                sketch_line(state.draw, arrowhead_paths[index], path_color, width, seed + 100 + index)
            target -= length
            continue
        if target > 0:
            partial, tip, tangent = partial_path(path, target)
            sketch_line(state.draw, partial, path_color, width, seed + index)
            state.claim_pen(owner, tip, tangent)
            active_claimed = True
        break
    if 0.0 < p < 1.0 and not active_claimed:
        raise BuildError(f"Pen action {owner!r} produced no active stroke")


@lru_cache(maxsize=64)
def cached_text_layer(width: int, height: int, text: str, x: int, y: int, size: int,
                      color: tuple[int, int, int], bold: bool, italic: bool) -> tuple[Image.Image, tuple[int, int, int, int]]:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    selected_font = load_font(size, bold, italic)
    draw.text((x, y), text, font=selected_font, fill=(*color, 255))
    return layer, draw.textbbox((x, y), text, font=selected_font)


def draw_text_action(state: FrameState, action: dict[str, Any], p: float, color: tuple[int, int, int], width: int, height: int) -> None:
    layer, bbox = cached_text_layer(width, height, action["text"], int(action["x"]), int(action["y"]),
                                    int(action["size"]), color, bool(action.get("bold")), bool(action.get("italic")))
    reveal_x = bbox[0] + (bbox[2] - bbox[0]) * clamp(p)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rectangle((bbox[0] - 5, bbox[1] - 8, reveal_x, bbox[3] + 8), fill=255)
    state.image.alpha_composite(Image.composite(layer, Image.new("RGBA", (width, height)), mask))
    if 0.0 < p < 1.0:
        state.claim_pen(action["id"], (reveal_x + 4, (bbox[1] + bbox[3]) / 2 + 8), (1.0, 0.0))


def fade_text(state: FrameState, action: dict[str, Any], p: float, color: tuple[int, int, int],
              width: int, height: int, caption_font: str = "serif") -> None:
    x = round(resolve_text_x(action, width, "marker" if caption_font == "marker" else "serif"))
    if caption_font == "marker":
        layer, _ = marker_text_layer(width, height, action["text"], x,
                                     int(action["y"]), int(action["size"]), color)
    else:
        layer, _ = cached_text_layer(width, height, action["text"], x, int(action["y"]),
                                     int(action["size"]), color, bool(action.get("bold")), bool(action.get("italic")))
    alpha = layer.getchannel("A").point(lambda value: int(value * clamp(p)))
    copy = layer.copy()
    copy.putalpha(alpha)
    state.image.alpha_composite(copy)


def load_asset(name: str):
    """Fetch a typed asset from the registry; geometry lives in assets/*.json."""
    try:
        return REGISTRY.load(name)
    except GeometryError as exc:
        raise BuildError(str(exc)) from exc


@lru_cache(maxsize=512)
def placed_asset(name: str, at: tuple[float, float] | None, scale: float,
                 board: tuple[int, int] | None = None) -> Asset:
    """Asset repositioned/rescaled per the action's `at`/`scale` fields."""
    asset = load_asset(name)
    if at is None and scale == 1.0:
        return asset
    try:
        return transform_asset(asset, at, scale, board)
    except GeometryError as exc:
        raise BuildError(str(exc)) from exc


def action_placement(action: dict[str, Any]) -> tuple[tuple[float, float] | None, float]:
    at = action.get("at")
    if at is not None:
        if not (isinstance(at, (list, tuple)) and len(at) == 2):
            raise BuildError(f"Action {action.get('id')!r}: 'at' must be an [x, y] pair")
        at = (float(at[0]), float(at[1]))
    return at, float(action.get("scale", 1.0))


def action_asset(action: dict[str, Any], board: tuple[int, int] | None = None) -> Asset:
    at, scale = action_placement(action)
    return placed_asset(action["asset"], at, scale, board)


@lru_cache(maxsize=512)
def compiled_events(asset_name: str, at: tuple[float, float] | None, scale: float,
                    duration: float, arrowheads: bool,
                    board: tuple[int, int] | None = None) -> tuple[PenEvent, ...]:
    """Cache one physical timeline per placed asset + duration + arrowheads."""
    events, _stats = compile_drawable(placed_asset(asset_name, at, scale, board),
                                      duration, arrowheads)
    return tuple(events)


@lru_cache(maxsize=64)
def load_image_asset(name: str, height: int) -> Image.Image:
    """Load a raster image asset (e.g. AI-generated artwork) scaled to height.

    Images live as transparent PNGs under assets/images/ and are shown with
    fade actions — they are placed artwork, not pen drawings, so no hand ever
    appears over them (rule 6).
    """
    path = IMAGE_DIR / f"{name}.png"
    if not path.is_file():
        raise BuildError(f"Unknown image asset {name!r}: no file {path}")
    image = Image.open(path).convert("RGBA")
    if image.width == 0 or image.height == 0:
        raise BuildError(f"Image asset {name!r} is empty")
    scale = height / image.height
    return image.resize((max(1, round(image.width * scale)), height),
                        Image.Resampling.LANCZOS)


def show_image(state: FrameState, action: dict[str, Any], p: float) -> None:
    """Fade in a raster image centred on the action's `at` point."""
    height = int(action.get("height", 400))
    image = load_image_asset(action["image"], height)
    at = action.get("at")
    if not (isinstance(at, (list, tuple)) and len(at) == 2):
        raise BuildError(f"Action {action.get('id')!r}: show_image requires \"at\": [x, y]")
    layer = image.copy()
    alpha = layer.getchannel("A").point(lambda value: int(value * clamp(p)))
    layer.putalpha(alpha)
    state.image.alpha_composite(layer, (round(float(at[0]) - image.width / 2),
                                        round(float(at[1]) - image.height / 2)))


@lru_cache(maxsize=128)
def marker_text_layer(width: int, height: int, text: str, x: int, y: int, size: int,
                      color: tuple[int, int, int]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Rasterise a string in the bundled marker font; (x, y) is the cap-top."""
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = marker_font(size)
    # Anchor so the capital letters' top lands on y, like the stroke font.
    cap_box = font.getbbox("H")
    draw.text((x - font.getbbox(text)[0] + 1, y - cap_box[1]), text, font=font, fill=(*color, 255))
    bbox = layer.getbbox()
    if bbox is None:
        raise BuildError(f"Marker text {text!r} rendered no pixels")
    return layer, bbox


@lru_cache(maxsize=128)
def marker_text_plan(text: str, x: float, y: float, size: float, duration: float,
                     board: tuple[int, int]) -> tuple[tuple[PenEvent, ...], dict[str, Any]]:
    """Physical reveal plan for marker text: Hershey skeletons fitted to the
    rasterised glyphs' bounding box act as the brush path the nib follows."""
    layer, bbox = marker_text_layer(board[0], board[1], text, round(x), round(y),
                                    round(size), (0, 0, 0))
    if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > board[0] or bbox[3] > board[1]:
        raise BuildError(f"Marker text {text!r} bounds {bbox} leave the "
                         f"{board[0]}x{board[1]} board")
    try:
        skeleton = text_to_strokes(text, 0.0, 0.0, 100.0)
    except TextStrokeError as exc:
        raise BuildError(str(exc)) from exc
    sx0, sy0, sx1, sy1 = strokes_bounds(skeleton)
    span_x, span_y = max(sx1 - sx0, 1e-6), max(sy1 - sy0, 1e-6)
    fit_x = (bbox[2] - bbox[0]) / span_x
    fit_y = (bbox[3] - bbox[1]) / span_y
    fitted = [[(bbox[0] + (px - sx0) * fit_x, bbox[1] + (py - sy0) * fit_y)
               for px, py in stroke] for stroke in skeleton]
    strokes = []
    for index, points in enumerate(fitted):
        is_last = index == len(fitted) - 1
        gap = 0.0 if is_last else math.dist(points[-1], fitted[index + 1][0])
        strokes.append(StrokePath(
            id=f"glyph_{index}", points=tuple(points),
            closed=math.dist(points[0], points[-1]) <= 1e-6,
            pen_lift_after=(not is_last) and gap > 1e-6,
        ))
    asset = Asset(id="marker_text", board=board, view_box=strokes_bounds(fitted),
                  self_intersections="allow", strokes=tuple(strokes))
    events, stats = compile_drawable(asset, duration, False)
    return tuple(events), stats


def draw_marker_text(state: FrameState, action: dict[str, Any], time_s: float,
                     color: tuple[int, int, int], board: tuple[int, int]) -> None:
    """Reveal marker-font text through a brush mask following the fitted
    skeleton; the nib rides the brush front. Completed text is composited in
    full so no glyph pixel is ever left behind."""
    size = float(action["size"])
    x = resolve_text_x(action, board[0], "marker")
    layer, _bbox = marker_text_layer(board[0], board[1], action["text"],
                                     round(x), round(float(action["y"])),
                                     round(size), color)
    duration = float(action["duration"])
    tau = time_s - float(action["start"])
    if tau >= duration:
        state.image.alpha_composite(layer)
        return
    events, _stats = marker_text_plan(action["text"], x, float(action["y"]),
                                      size, duration, board)
    brush = max(16, round(size * 0.72))
    mask = Image.new("L", (board[0], board[1]), 0)
    mask_draw = ImageDraw.Draw(mask)

    def paint(points: list[tuple[float, float]]) -> None:
        if len(points) >= 2:
            mask_draw.line(points, fill=255, width=brush, joint="curve")
        half = brush / 2
        for px, py in (points[0], points[-1]):
            mask_draw.ellipse((px - half, py - half, px + half, py + half), fill=255)

    for event in events:
        if event.kind == "travel":
            if event.start < tau < event.end:
                fraction = smooth((tau - event.start) / event.duration)
                origin, target = event.points[0], event.points[1]
                position = (origin[0] + (target[0] - origin[0]) * fraction,
                            origin[1] + (target[1] - origin[1]) * fraction)
                state.claim_pen(action["id"], position,
                                (target[0] - origin[0], target[1] - origin[1]),
                                stroke=f"travel:{event.stroke_index}", contact=False)
            continue
        if tau <= event.start:
            continue
        points = list(event.points)
        if tau >= event.end:
            paint(points)
            continue
        fraction = smooth((tau - event.start) / event.duration)
        partial, tip, _tan = partial_path(points, fraction * path_length(points))
        paint(partial)
        state.claim_pen(action["id"], tip, smoothed_tangent(partial),
                        stroke=f"marker:{event.stroke_index}")
    revealed = layer.copy()
    revealed.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    state.image.alpha_composite(revealed)


@lru_cache(maxsize=256)
def fill_timeline(polygon: tuple[tuple[float, float], ...], width: int, duration: float,
                  board: tuple[int, int]) -> tuple[tuple[PenEvent, ...], dict[str, Any]]:
    """Physical colouring-in plan: serpentine marker passes over a polygon."""
    try:
        rows = serpentine_fill(list(polygon), spacing=width * 0.8, inset=width * 0.55)
    except ValueError as exc:
        raise BuildError(str(exc)) from exc
    if not rows:
        raise BuildError(f"Fill polygon {polygon[:3]}... produced no passes; "
                         f"region too small for width {width}")
    strokes = []
    for index, points in enumerate(rows):
        is_last = index == len(rows) - 1
        gap = 0.0 if is_last else math.dist(points[-1], rows[index + 1][0])
        strokes.append(StrokePath(
            id=f"pass_{index}", points=tuple(points), closed=False,
            pen_lift_after=(not is_last) and gap > 1e-6,
        ))
    xs = [p[0] for row in rows for p in row]
    ys = [p[1] for row in rows for p in row]
    asset = Asset(id="fill", board=board, view_box=(min(xs), min(ys), max(xs), max(ys)),
                  self_intersections="allow", strokes=tuple(strokes))
    try:
        preflight_asset(asset)
    except GeometryError as exc:
        raise BuildError(f"Fill region failed preflight: {exc}") from exc
    events, stats = compile_drawable(asset, duration, False)
    return tuple(events), stats


def action_fill_polygon(action: dict[str, Any],
                        board: tuple[int, int] | None = None) -> tuple[tuple[float, float], ...]:
    """Fill region for a draw_fill action: inline polygon, or an asset stroke.

    With ``"asset"`` (plus optional ``"stroke_id"``, ``"at"``, ``"scale"``)
    the region is the asset's closed stroke at its placed position — so the
    hand can colour in a drawn shape without anyone computing coordinates.
    """
    if "asset" in action:
        placed = action_asset(action, board)
        stroke_id = action.get("stroke_id")
        candidates = [s for s in placed.strokes
                      if (s.id == stroke_id if stroke_id else s.closed)]
        if not candidates:
            raise BuildError(f"Action {action.get('id')!r}: no "
                             f"{'stroke ' + repr(stroke_id) if stroke_id else 'closed stroke'} "
                             f"to fill in asset {action['asset']!r}")
        return candidates[0].points
    polygon = action.get("polygon")
    if not (isinstance(polygon, list) and len(polygon) >= 3):
        raise BuildError(f"Action {action.get('id')!r}: draw_fill requires \"polygon\" "
                         f"with at least 3 [x, y] points, or an \"asset\" reference")
    return tuple((float(p[0]), float(p[1])) for p in polygon)


@lru_cache(maxsize=256)
def measured_text_width(text: str, size: int, kind: str,
                        bold: bool = False, italic: bool = False) -> float:
    if kind == "hershey":
        bounds = strokes_bounds(text_to_strokes(text, 0.0, 0.0, float(size)))
        return bounds[2] - bounds[0]
    if kind == "marker":
        box = marker_font(size).getbbox(text)
        return box[2] - box[0]
    box = load_font(size, bold, italic).getbbox(text)
    return box[2] - box[0]


def resolve_text_x(action: dict[str, Any], board_width: int, kind: str) -> float:
    """Text anchor: explicit x, or measured centre with `"align": "center"`."""
    if action.get("align") == "center":
        width = measured_text_width(action["text"], round(float(action["size"])), kind,
                                    bool(action.get("bold")), bool(action.get("italic")))
        return (board_width - width) / 2
    return float(action["x"])


@lru_cache(maxsize=256)
def text_timeline(text: str, x: float, y: float, size: float, duration: float,
                  board: tuple[int, int]) -> tuple[tuple[PenEvent, ...], dict[str, Any]]:
    """Lay out a string as glyph strokes and compile its physical timeline.

    The synthetic asset goes through the same geometry preflight as
    illustration assets, so overflowing or unsupported text fails before any
    frame renders.
    """
    try:
        polylines = text_to_strokes(text, x, y, size)
    except TextStrokeError as exc:
        raise BuildError(str(exc)) from exc
    strokes = []
    for index, points in enumerate(polylines):
        is_last = index == len(polylines) - 1
        gap = 0.0 if is_last else math.dist(points[-1], polylines[index + 1][0])
        strokes.append(StrokePath(
            id=f"glyph_{index}",
            points=tuple(points),
            closed=math.dist(points[0], points[-1]) <= 1e-6,
            pen_lift_after=(not is_last) and gap > 1e-6,
        ))
    asset = Asset(id="text", board=board, view_box=strokes_bounds(polylines),
                  self_intersections="allow", strokes=tuple(strokes))
    try:
        preflight_asset(asset)
    except GeometryError as exc:
        raise BuildError(f"Text {text!r} failed geometry preflight: {exc}") from exc
    events, stats = compile_drawable(asset, duration, False)
    return tuple(events), stats


def draw_events(state: FrameState, owner: str, events: tuple[PenEvent, ...], tau: float,
                color: tuple[int, int, int], width: int, seed_base: int,
                last_color: tuple[int, int, int] | None = None, claim: bool = True) -> None:
    """Render a compiled physical timeline at local action time ``tau``.

    Completed pen-down events are drawn in full; the active pen-down event is
    drawn partially with the pen claimed at its front; travel events draw
    nothing and claim nothing — the hand is lifted between strokes instead of
    teleporting. Seeds match the legacy renderer so the sketch texture of a
    finished frame is unchanged.
    """
    stroke_indices = [event.stroke_index for event in events if event.kind == "stroke"]
    last_index = stroke_indices[-1] if stroke_indices else -1
    for event in events:
        if event.kind == "travel":
            # The hand stays visible while it glides, lifted, to the next
            # stroke — no teleporting, no drawing, no contact.
            if claim and event.start < tau < event.end:
                fraction = smooth((tau - event.start) / event.duration)
                origin, target = event.points[0], event.points[1]
                position = (origin[0] + (target[0] - origin[0]) * fraction,
                            origin[1] + (target[1] - origin[1]) * fraction)
                state.claim_pen(owner, position,
                                (target[0] - origin[0], target[1] - origin[1]),
                                stroke=f"travel:{event.stroke_index}", contact=False)
            continue
        if tau <= event.start:
            continue
        event_color = last_color if last_color and event.stroke_index == last_index else color
        seed = seed_base + event.stroke_index + (100 if event.kind == "arrowhead" else 0)
        points = list(event.points)
        if tau >= event.end:
            sketch_line(state.draw, points, event_color, width, seed)
            continue
        fraction = smooth((tau - event.start) / event.duration)
        partial, tip, _tangent = partial_path(points, fraction * path_length(points))
        sketch_line(state.draw, partial, event_color, width, seed)
        if claim:
            state.claim_pen(owner, tip, smoothed_tangent(partial),
                            stroke=f"{event.kind}:{event.stroke_index}")


def paper_texture(width: int, height: int, paper: tuple[int, int, int]) -> Image.Image:
    rng = random.Random(17)
    image = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(image)
    for _ in range(round(width * height / 384)):
        draw.point((rng.randrange(width), rng.randrange(height)),
                   fill=rng.choice([(228, 225, 216), (241, 237, 228), (255, 253, 247)]))
    for y in range(16, height, 34):
        draw.line((0, y, width, y), fill=(246, 243, 235), width=1)
    return image


def flatten_actions(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    return [action for scene in storyboard["scenes"] for action in scene["actions"]]


def validate_storyboard(storyboard: dict[str, Any]) -> dict[str, Any]:
    required = {"version", "width", "height", "fps", "content_duration", "safe_content_end", "final_hold", "style", "scenes"}
    missing = sorted(required - storyboard.keys())
    if missing:
        raise BuildError(f"Storyboard is missing keys: {missing}")
    if storyboard["version"] != 2:
        raise BuildError("Only storyboard version 2 is supported")
    if storyboard.get("pen_physics", "legacy") not in PEN_PHYSICS_MODES:
        raise BuildError(f"pen_physics must be one of {PEN_PHYSICS_MODES}")
    if storyboard.get("hand", "procedural") not in HAND_MODES:
        raise BuildError(f"hand must be one of {HAND_MODES}")
    if storyboard.get("chrome", "legacy") not in CHROME_MODES:
        raise BuildError(f"chrome must be one of {CHROME_MODES}")
    if storyboard.get("text_font", "hershey") not in TEXT_FONTS:
        raise BuildError(f"text_font must be one of {TEXT_FONTS}")
    if storyboard.get("caption_font", "serif") not in ("serif", "marker"):
        raise BuildError("caption_font must be 'serif' or 'marker'")
    actions = flatten_actions(storyboard)
    ids = [action["id"] for action in actions]
    if len(ids) != len(set(ids)):
        raise BuildError("Action ids must be unique")
    for action in actions:
        if float(action["duration"]) <= 0:
            raise BuildError(f"Action {action['id']!r} has a non-positive duration")
        if float(action["start"]) < 0 or float(action["start"]) + float(action["duration"]) > float(storyboard["content_duration"]):
            raise BuildError(f"Action {action['id']!r} lies outside the content timeline")
    pen_actions = sorted((a for a in actions if a.get("requires_pen")), key=lambda a: float(a["start"]))
    collisions = []
    for previous, current in zip(pen_actions, pen_actions[1:]):
        previous_end = float(previous["start"]) + float(previous["duration"])
        if float(current["start"]) < previous_end - 1e-9:
            collisions.append((previous["id"], current["id"], previous_end - float(current["start"])))
    if collisions:
        raise BuildError(f"Single-pen invariant failed: {collisions}")
    for scene in storyboard["scenes"]:
        if float(scene["start"]) >= float(scene["end"]):
            raise BuildError(f"Scene {scene['id']!r} has an invalid range")
        for action in scene["actions"]:
            if float(action["start"]) < float(scene["start"]) - 1e-9 or float(action["start"]) + float(action["duration"]) > float(scene["end"]) + 1e-9:
                raise BuildError(f"Action {action['id']!r} lies outside scene {scene['id']!r}")
    return {"actions": len(actions), "pen_actions": len(pen_actions), "pen_collisions": 0, "max_active_pens": 1}


def preflight_project(storyboard: dict[str, Any]) -> dict[str, Any]:
    """Fail on missing fonts/assets and bad geometry before any frame renders."""
    for kind in FONT_CANDIDATES:
        resolve_font_path(kind)
    board = (int(storyboard["width"]), int(storyboard["height"]))
    names = set()
    images = 0
    for action in flatten_actions(storyboard):
        if action["type"] == "show_image":
            height = int(action.get("height", 400))
            image = load_image_asset(action["image"], height)
            at = action.get("at")
            if not (isinstance(at, (list, tuple)) and len(at) == 2):
                raise BuildError(f"Action {action['id']!r}: show_image requires \"at\": [x, y]")
            if (at[0] - image.width / 2 < 0 or at[0] + image.width / 2 > board[0]
                    or at[1] - height / 2 < 0 or at[1] + height / 2 > board[1]):
                raise BuildError(f"Action {action['id']!r}: image {action['image']!r} at {at} "
                                 f"({image.width}x{height}) leaves the {board[0]}x{board[1]} board")
            images += 1
            continue
        if action["type"] not in {"draw_asset", "draw_break"}:
            continue
        names.add(action["asset"])
        placed = action_asset(action, board)
        # Un-placed actions inherit the asset's authored coordinates, so the
        # boards must match. Explicitly placed actions are board-agnostic:
        # the transform recentres them and the bounds check below governs.
        if action.get("at") is None and placed.board != board:
            raise BuildError(f"Asset {action['asset']!r} was authored for board {placed.board}, "
                             f"storyboard is {board}; place it with \"at\" or match boards")
        try:
            preflight_asset(placed)
        except GeometryError as exc:
            raise BuildError(f"Action {action['id']!r}: {exc}") from exc
        x0, y0, x1, y1 = placed.view_box
        if x0 < 0 or y0 < 0 or x1 > board[0] or y1 > board[1]:
            raise BuildError(f"Action {action['id']!r}: placed asset {action['asset']!r} "
                             f"bounds {placed.view_box} leave the {board[0]}x{board[1]} board")
    text_actions = 0
    text_font_default = storyboard.get("text_font", "hershey")
    for action in flatten_actions(storyboard):
        if action["type"] == "draw_fill":
            fill_timeline(action_fill_polygon(action, board), int(action.get("width", 18)),
                          float(action["duration"]), board)
        if action["type"] == "write_text":
            if action.get("font", text_font_default) == "marker":
                marker_text_plan(action["text"], resolve_text_x(action, board[0], "marker"),
                                 float(action["y"]),
                                 float(action["size"]), float(action["duration"]), board)
            else:
                text_timeline(action["text"], resolve_text_x(action, board[0], "hershey"),
                              float(action["y"]),
                              float(action["size"]), float(action["duration"]), board)
            text_actions += 1
    if storyboard.get("hand", "procedural") == "sprite":
        try:
            default_rig()
        except HandRigError as exc:
            raise BuildError(str(exc)) from exc
    return {"assets": len(names), "text_actions": text_actions, "fonts": "ok"}


class WhiteboardProject:
    def __init__(self, storyboard: dict[str, Any]) -> None:
        self.storyboard = storyboard
        self.width = int(storyboard["width"])
        self.height = int(storyboard["height"])
        self.fps = int(storyboard["fps"])
        self.duration = float(storyboard["content_duration"])
        self.style = {name: tuple(value) for name, value in storyboard["style"].items()}
        self.pen_physics = storyboard.get("pen_physics", "legacy")
        self.hand = storyboard.get("hand", "procedural")
        self.chrome = storyboard.get("chrome", "legacy")
        self.text_font = storyboard.get("text_font", "hershey")
        self.caption_font = storyboard.get("caption_font", "serif")
        self.base = paper_texture(self.width, self.height, self.style["paper"])
        self.last_report: dict[str, Any] | None = None

    def active_scene(self, time_s: float) -> dict[str, Any]:
        for scene in self.storyboard["scenes"]:
            if float(scene["start"]) <= time_s < float(scene["end"]):
                return scene
        return self.storyboard["scenes"][-1]

    def render_frame(self, time_s: float) -> Image.Image:
        image = self.base.convert("RGBA")
        state = FrameState(image)
        if self.chrome == "legacy":
            state.draw.text((55, 665), "A WHITEBOARD THOUGHT EXPERIMENT", font=load_font(19, italic=True), fill=self.style["faint"])
            state.draw.line((55, 640, 1225, 640), fill=(224, 220, 210), width=2)
            state.draw.line((55, 640, 55 + 1170 * clamp(time_s / self.duration), 640), fill=self.style["teal"], width=4)
        scene = self.active_scene(time_s)
        for index, action in enumerate(scene["actions"]):
            p = action_progress(action, time_s)
            if p <= 0:
                continue
            color = self.style[action.get("color", "ink")]
            action_type = action["type"]
            if action_type in {"draw_text", "fast_reveal_text"}:
                # Raster wipe reveal — legacy behaviour, not handwriting.
                draw_text_action(state, action, p, color, self.width, self.height)
            elif action_type == "fade_text":
                fade_text(state, action, p, color, self.width, self.height, self.caption_font)
            elif action_type == "write_text":
                if action.get("font", self.text_font) == "marker":
                    draw_marker_text(state, action, time_s, color, (self.width, self.height))
                else:
                    events, _stats = text_timeline(action["text"],
                                                   resolve_text_x(action, self.width, "hershey"),
                                                   float(action["y"]),
                                                   float(action["size"]), float(action["duration"]),
                                                   (self.width, self.height))
                    tau = time_s - float(action["start"])
                    draw_events(state, action["id"], events, tau, color, int(action.get("width", 3)),
                                3000 + index)
            elif action_type == "fade_labels":
                for label_index, label in enumerate(action["labels"]):
                    local = clamp(p * len(action["labels"]) - label_index)
                    synthetic = {**action, **label, "id": f"{action['id']}_{label_index}", "italic": True}
                    fade_text(state, synthetic, local, color, self.width, self.height, self.caption_font)
            elif action_type == "draw_fill":
                events, _stats = fill_timeline(action_fill_polygon(action, (self.width, self.height)),
                                               int(action.get("width", 18)),
                                               float(action["duration"]),
                                               (self.width, self.height))
                draw_events(state, action["id"], events, time_s - float(action["start"]),
                            color, int(action.get("width", 18)), 5000 + index)
            elif action_type == "show_image":
                show_image(state, action, p)
            elif action_type == "fade_asset" and action["asset"] == "reaction_dots":
                for dot_index, x in enumerate([205, 420, 635, 850, 1065]):
                    local = clamp(p * 5 - dot_index)
                    if local > 0:
                        alpha_color = tuple(round(channel * local + self.style["paper"][i] * (1-local)) for i, channel in enumerate(color))
                        state.draw.ellipse((x - 18, 348, x + 18, 384), outline=alpha_color, width=5)
            elif action_type in {"draw_asset", "draw_break"}:
                if self.pen_physics == "lift":
                    at, scale = action_placement(action)
                    events = compiled_events(action["asset"], at, scale, float(action["duration"]),
                                             bool(action.get("arrowheads")),
                                             (self.width, self.height))
                    tau = time_s - float(action["start"])
                    if action_type == "draw_break":
                        # Erase mask and accent line share identical partial
                        # progress: paper never appears ahead of the nib.
                        draw_events(state, action["id"], events, tau, self.style["paper"], 18,
                                    800 + index, claim=False)
                    draw_events(state, action["id"], events, tau, color, int(action.get("width", 6)),
                                1000 + index, self.style.get(action.get("last_color", "")))
                else:
                    asset = action_asset(action, (self.width, self.height))
                    paths = [list(stroke.points) for stroke in asset.strokes]
                    arrowhead_paths = [list(stroke.arrowhead) if stroke.arrowhead else None
                                       for stroke in asset.strokes]
                    if action_type == "draw_break":
                        compound_paths(state, f"{action['id']}_erase", paths, 1.0, self.style["paper"], 18, 800 + index)
                    compound_paths(state, action["id"], paths, p, color, int(action.get("width", 6)), 1000 + index,
                                   bool(action.get("arrowheads")), self.style.get(action.get("last_color", "")),
                                   arrowhead_paths)
            else:
                raise BuildError(f"Unsupported action type {action_type!r}")
        pen = state.pen
        hand_pose = None
        # A lifted hand hovers slightly up-left of the board point it glides over.
        anchor = None if pen is None else (
            pen.tip if pen.contact else (pen.tip[0] + 5, pen.tip[1] - 14))
        if pen and self.hand == "sprite":
            hand_pose = default_rig().draw(state.image, anchor, pen.tangent)
        elif pen:
            draw_marker(state.draw, anchor, pen.tangent)
        self.last_report = {
            "time": time_s,
            "scene": scene["id"],
            "pen": ("down" if pen.contact else "travel") if pen else "up",
            "owner": pen.owner if pen else None,
            "stroke": pen.stroke if pen else None,
            "tip": list(pen.tip) if pen else None,
            "tangent": list(pen.tangent) if pen else None,
            "hand_pose": hand_pose,
        }
        return state.image.convert("RGB")


def make_chalk_audio(path: Path, storyboard: dict[str, Any]) -> None:
    rate = 48_000
    duration = float(storyboard["content_duration"])
    audio = np.zeros(int(duration * rate), dtype=np.float32)
    rng = np.random.default_rng(42)
    for action in flatten_actions(storyboard):
        if not action.get("requires_pen"):
            continue
        start = int(float(action["start"]) * rate)
        end = min(len(audio), int((float(action["start"]) + float(action["duration"])) * rate))
        count = max(0, end - start)
        if not count:
            continue
        noise = rng.normal(0, 1, count).astype(np.float32)
        texture = noise - np.convolve(noise, np.ones(24, dtype=np.float32) / 24, mode="same")
        envelope = np.sin(np.linspace(0, math.pi, count)) ** .35
        audio[start:end] += texture * envelope * .026
    for scene in storyboard["scenes"]:
        beat = int(float(scene["start"]) * rate)
        length = min(int(.12 * rate), len(audio) - beat)
        if length <= 0:
            continue
        x = np.linspace(0, length / rate, length, endpoint=False)
        audio[beat:beat+length] += (np.sin(2 * math.pi * 150 * x) * np.exp(-x * 42) * .10).astype(np.float32)
    pcm = (np.clip(audio, -.95, .95) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


def run_checked(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise BuildError(f"Command failed ({result.returncode}): {' '.join(command[:4])}\n{result.stderr[-4000:]}")


def render(project: WhiteboardProject, output: Path, narration: Path | None, preview: bool,
           audio_mode: str = "none") -> dict[str, Any]:
    if audio_mode not in AUDIO_MODES:
        raise BuildError(f"Unknown audio mode {audio_mode!r}; expected one of {AUDIO_MODES}")
    if audio_mode in {"narration", "mix"}:
        if narration is None:
            raise BuildError(f"Audio mode {audio_mode!r} requires --narration")
        if not narration.is_file():
            raise BuildError(f"Narration file not found: {narration}")
    elif narration is not None:
        raise BuildError(f"Audio mode {audio_mode!r} does not accept --narration")
    preflight_project(project.storyboard)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise BuildError("FFmpeg and FFprobe are required")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    scale = (854, 480) if preview else (project.width, project.height)
    with tempfile.TemporaryDirectory(prefix="whiteboard-v2-", dir=output.parent) as temporary:
        temp = Path(temporary)
        raw_video = temp / "raw.mp4"
        chalk = temp / "chalk.wav"
        final_temp = temp / "final.mp4"
        if audio_mode in {"chalk", "mix"}:
            make_chalk_audio(chalk, project.storyboard)
        command = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                   "-s", f"{scale[0]}x{scale[1]}", "-r", str(project.fps), "-i", "-",
                   "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", str(raw_video)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        assert process.stdin is not None
        try:
            for frame_number in range(round(project.duration * project.fps)):
                frame = project.render_frame(frame_number / project.fps)
                if preview:
                    frame = frame.resize(scale, Image.Resampling.LANCZOS)
                process.stdin.write(frame.tobytes())
        except BrokenPipeError as exc:
            diagnostic = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
            raise BuildError(f"FFmpeg stopped accepting frames: {diagnostic[-4000:]}") from exc
        finally:
            process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        if process.wait() != 0:
            raise BuildError(f"FFmpeg frame render failed: {stderr[-4000:]}")
        safe_end = float(project.storyboard["safe_content_end"])
        hold = float(project.storyboard["final_hold"])
        final_duration = safe_end + hold
        video_filter = (f"[0:v]trim=end={safe_end},setpts=PTS-STARTPTS,"
                        f"tpad=stop_mode=clone:stop_duration={hold}[v]")
        video_codec = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
        if audio_mode == "none":
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video),
                "-filter_complex", video_filter,
                "-map", "[v]", "-an", "-t", str(final_duration),
                *video_codec, "-movflags", "+faststart", str(final_temp),
            ]
        elif audio_mode == "chalk":
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-i", str(chalk),
                "-filter_complex",
                f"{video_filter};"
                f"[1:a]atrim=end={safe_end},asetpts=PTS-STARTPTS,apad=pad_dur={hold}[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(final_duration),
                *video_codec, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final_temp),
            ]
        elif audio_mode == "narration":
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-i", str(narration),
                "-filter_complex",
                f"{video_filter};"
                f"[1:a]aresample=48000,volume=1.0,apad,atrim=end={safe_end},asetpts=PTS-STARTPTS,"
                f"apad=pad_dur={hold}[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(final_duration),
                *video_codec, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final_temp),
            ]
        else:  # mix
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-i", str(narration), "-i", str(chalk),
                "-filter_complex",
                f"{video_filter};"
                f"[1:a]aresample=48000,volume=1.0,apad,atrim=end={safe_end},asetpts=PTS-STARTPTS[n];"
                f"[2:a]volume=0.18,atrim=end={safe_end},asetpts=PTS-STARTPTS[c];"
                f"[n][c]amix=inputs=2:duration=longest:normalize=0,apad=pad_dur={hold}[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(final_duration),
                *video_codec, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final_temp),
            ]
        run_checked(final_command)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                                "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(final_temp)],
                               capture_output=True, text=True, check=True)
        media = json.loads(probe.stdout)
        stream_types = [stream.get("codec_type") for stream in media.get("streams", [])]
        audio_streams = stream_types.count("audio")
        expected_audio = 0 if audio_mode == "none" else 1
        if stream_types.count("video") != 1:
            raise BuildError("Final media validation failed: expected exactly one video stream")
        if audio_streams != expected_audio:
            raise BuildError(f"Final media validation failed: audio mode {audio_mode!r} expects "
                             f"{expected_audio} audio stream(s), found {audio_streams}")
        final_temp.replace(output)
    return {"output": str(output), "duration": final_duration, "resolution": list(scale), "fps": project.fps,
            "audio_mode": audio_mode, "audio_streams": audio_streams,
            "narration": str(narration) if narration else None, "media": media}


def resolve_audio_mode(args: argparse.Namespace) -> str:
    """Map CLI flags to an explicit audio mode; `none` is the project default."""
    mode = args.audio_mode
    if args.silent:
        if mode not in (None, "none"):
            raise BuildError("--silent conflicts with --audio-mode " + mode)
        mode = "none"
    if mode is None:
        # Legacy `--narration FILE` without a mode meant narration mixed over chalk.
        mode = "mix" if args.narration else "none"
    if mode in {"narration", "mix"} and not args.narration:
        raise BuildError(f"--audio-mode {mode} requires --narration FILE")
    if mode in {"none", "chalk"} and args.narration:
        raise BuildError(f"--audio-mode {mode} does not accept --narration")
    return mode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_DEFAULT)
    parser.add_argument("--output", type=Path, default=ROOT / "people_arent_broken_v2.mp4")
    parser.add_argument("--audio-mode", choices=AUDIO_MODES, default=None,
                        help="Audio policy for the master: none (default, no audio stream), "
                             "chalk (synthesised marker sounds), narration (supplied file only), "
                             "mix (narration over chalk)")
    parser.add_argument("--narration", type=Path,
                        help="Narration audio file; required by --audio-mode narration/mix")
    parser.add_argument("--silent", action="store_true",
                        help="Deprecated alias for --audio-mode none")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    audio_mode = resolve_audio_mode(args)
    storyboard = json.loads(args.storyboard.read_text(encoding="utf-8"))
    validation = validate_storyboard(storyboard)
    preflight = preflight_project(storyboard)
    if args.validate_only:
        print(json.dumps({"status": "valid", **validation, "preflight": preflight}, indent=2))
        return
    result = render(WhiteboardProject(storyboard), args.output, args.narration, args.preview, audio_mode)
    report = {"status": "succeeded", "validation": validation, **result}
    report_path = args.output.with_suffix(".build.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
