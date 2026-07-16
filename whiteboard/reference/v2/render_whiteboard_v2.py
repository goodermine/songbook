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
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
STORYBOARD_DEFAULT = ROOT / "storyboard_v2.json"
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


@dataclass(frozen=True)
class PenPose:
    owner: str
    tip: tuple[float, float]
    tangent: tuple[float, float]


class FrameState:
    """Collects one global pen pose and rejects any runtime collision."""

    def __init__(self, image: Image.Image) -> None:
        self.image = image
        self.draw = ImageDraw.Draw(image)
        self.pen: PenPose | None = None

    def claim_pen(self, owner: str, tip: tuple[float, float], tangent: tuple[float, float]) -> None:
        if self.pen is not None and self.pen.owner != owner:
            raise BuildError(f"Multiple active pens at runtime: {self.pen.owner!r} and {owner!r}")
        length = math.hypot(*tangent) or 1.0
        self.pen = PenPose(owner, tip, (tangent[0] / length, tangent[1] / length))

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


def arrow_head(draw: ImageDraw.ImageDraw, path: list[tuple[float, float]], color: tuple[int, int, int], width: int, seed: int) -> None:
    if len(path) < 2:
        return
    tip, previous = path[-1], path[-2]
    angle = math.atan2(tip[1] - previous[1], tip[0] - previous[0])
    size = 23
    left = (tip[0] - math.cos(angle - .55) * size, tip[1] - math.sin(angle - .55) * size)
    right = (tip[0] - math.cos(angle + .55) * size, tip[1] - math.sin(angle + .55) * size)
    sketch_line(draw, [left, tip, right], color, width, seed)


def compound_paths(state: FrameState, owner: str, paths: list[list[tuple[float, float]]], p: float,
                   color: tuple[int, int, int], width: int, seed: int,
                   arrowheads: bool = False, last_color: tuple[int, int, int] | None = None) -> None:
    """Draw compound paths at uniform physical velocity with one global pen."""
    lengths = [path_length(path) for path in paths]
    target = clamp(p) * sum(lengths)
    active_claimed = False
    for index, (path, length) in enumerate(zip(paths, lengths)):
        path_color = last_color if last_color and index == len(paths) - 1 else color
        if target >= length:
            sketch_line(state.draw, path, path_color, width, seed + index)
            if arrowheads:
                arrow_head(state.draw, path, path_color, width, seed + 100 + index)
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


def fade_text(state: FrameState, action: dict[str, Any], p: float, color: tuple[int, int, int], width: int, height: int) -> None:
    layer, _ = cached_text_layer(width, height, action["text"], int(action["x"]), int(action["y"]),
                                 int(action["size"]), color, bool(action.get("bold")), bool(action.get("italic")))
    alpha = layer.getchannel("A").point(lambda value: int(value * clamp(p)))
    copy = layer.copy()
    copy.putalpha(alpha)
    state.image.alpha_composite(copy)


def person_paths(cx: float, cy: float) -> list[list[tuple[float, float]]]:
    head = [(cx + math.cos(a) * 35, cy - 105 + math.sin(a) * 35) for a in np.linspace(-math.pi / 2, 3 * math.pi / 2, 36)]
    return [head, [(cx, cy - 70), (cx, cy + 15)], [(cx, cy - 35), (cx - 55, cy - 2)],
            [(cx, cy - 35), (cx + 55, cy - 2)], [(cx, cy + 15), (cx - 48, cy + 83)],
            [(cx, cy + 15), (cx + 48, cy + 83)]]


def quadratic_arrow(x1: float, y1: float, x2: float, y2: float, bend: float = 0.0, samples: int = 45) -> list[tuple[float, float]]:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    nx, ny = -(y2 - y1), x2 - x1
    length = math.hypot(nx, ny) or 1.0
    cx, cy = mx + nx / length * bend, my + ny / length * bend
    return [((1-u)**2*x1 + 2*(1-u)*u*cx + u*u*x2,
             (1-u)**2*y1 + 2*(1-u)*u*cy + u*u*y2) for u in np.linspace(0, 1, samples)]


def asset_paths(name: str) -> list[list[tuple[float, float]]]:
    if name == "person_one":
        return person_paths(390, 370)
    if name == "person_two":
        return person_paths(640, 365)
    if name == "cracks":
        return [[(390, 268), (374, 293), (392, 310)], [(392, 310), (370, 337)], [(392, 310), (414, 339)]]
    if name == "cross_out":
        return [[(665, 105), (1025, 160)], [(1010, 92), (685, 175)]]
    if name == "rehearsal_loop":
        return [[(640 + math.cos(a) * 235, 360 + math.sin(a) * 190) for a in np.linspace(-.55, math.pi * 1.73, 100)]]
    if name == "reaction_arrows":
        return [quadratic_arrow(x - 75, 310, x + 75, 310, -28) for x in [205, 420, 635, 850, 1065]]
    if name == "identity_box":
        return [[(330, 160), (950, 160), (950, 395), (330, 395), (330, 160)]]
    if name == "identity_break":
        return [[(640, 158), (610, 210), (662, 255), (620, 312), (650, 395)]]
    if name == "old_loop":
        return [[(345 + math.cos(a) * 125, 330 + math.sin(a) * 115) for a in np.linspace(0, math.pi * 2, 80)]]
    if name == "pause_symbol":
        return [[(322, 275), (322, 385)], [(370, 275), (370, 385)]]
    if name == "choice_path":
        return [[(465, 425), (540, 395), (615, 420), (700, 340), (790, 355), (875, 250), (1010, 215)]]
    raise BuildError(f"Unknown asset {name!r}")


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


class WhiteboardProject:
    def __init__(self, storyboard: dict[str, Any]) -> None:
        self.storyboard = storyboard
        self.width = int(storyboard["width"])
        self.height = int(storyboard["height"])
        self.fps = int(storyboard["fps"])
        self.duration = float(storyboard["content_duration"])
        self.style = {name: tuple(value) for name, value in storyboard["style"].items()}
        self.base = paper_texture(self.width, self.height, self.style["paper"])

    def active_scene(self, time_s: float) -> dict[str, Any]:
        for scene in self.storyboard["scenes"]:
            if float(scene["start"]) <= time_s < float(scene["end"]):
                return scene
        return self.storyboard["scenes"][-1]

    def render_frame(self, time_s: float) -> Image.Image:
        image = self.base.convert("RGBA")
        state = FrameState(image)
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
            if action_type == "draw_text":
                draw_text_action(state, action, p, color, self.width, self.height)
            elif action_type == "fade_text":
                fade_text(state, action, p, color, self.width, self.height)
            elif action_type == "fade_labels":
                for label_index, label in enumerate(action["labels"]):
                    local = clamp(p * len(action["labels"]) - label_index)
                    synthetic = {**action, **label, "id": f"{action['id']}_{label_index}", "italic": True}
                    fade_text(state, synthetic, local, color, self.width, self.height)
            elif action_type == "fade_asset" and action["asset"] == "reaction_dots":
                for dot_index, x in enumerate([205, 420, 635, 850, 1065]):
                    local = clamp(p * 5 - dot_index)
                    if local > 0:
                        alpha_color = tuple(round(channel * local + self.style["paper"][i] * (1-local)) for i, channel in enumerate(color))
                        state.draw.ellipse((x - 18, 348, x + 18, 384), outline=alpha_color, width=5)
            elif action_type in {"draw_asset", "draw_break"}:
                paths = asset_paths(action["asset"])
                if action_type == "draw_break":
                    compound_paths(state, f"{action['id']}_erase", paths, 1.0, self.style["paper"], 18, 800 + index)
                compound_paths(state, action["id"], paths, p, color, int(action.get("width", 6)), 1000 + index,
                               bool(action.get("arrowheads")), self.style.get(action.get("last_color", "")))
            else:
                raise BuildError(f"Unsupported action type {action_type!r}")
        state.overlay_pen()
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
           silent: bool = False) -> dict[str, Any]:
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
        if not silent:
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
        if silent:
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video),
                "-filter_complex",
                f"[0:v]trim=end={safe_end},setpts=PTS-STARTPTS,"
                f"tpad=stop_mode=clone:stop_duration={hold}[v]",
                "-map", "[v]", "-an", "-t", str(final_duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(final_temp),
            ]
        elif narration:
            if not narration.is_file():
                raise BuildError(f"Narration file not found: {narration}")
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-i", str(narration), "-i", str(chalk),
                "-filter_complex",
                f"[0:v]trim=end={safe_end},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={hold}[v];"
                f"[1:a]aresample=48000,volume=1.0,apad,atrim=end={safe_end},asetpts=PTS-STARTPTS[n];"
                f"[2:a]volume=0.18,atrim=end={safe_end},asetpts=PTS-STARTPTS[c];"
                f"[n][c]amix=inputs=2:duration=longest:normalize=0,apad=pad_dur={hold}[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(final_duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final_temp),
            ]
        else:
            final_command = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-i", str(chalk),
                "-filter_complex",
                f"[0:v]trim=end={safe_end},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={hold}[v];"
                f"[1:a]atrim=end={safe_end},asetpts=PTS-STARTPTS,apad=pad_dur={hold}[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(final_duration),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final_temp),
            ]
        run_checked(final_command)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                                "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(final_temp)],
                               capture_output=True, text=True, check=True)
        media = json.loads(probe.stdout)
        stream_types = [stream.get("codec_type") for stream in media.get("streams", [])]
        if "video" not in stream_types:
            raise BuildError("Final media validation failed: expected a video stream")
        if silent and "audio" in stream_types:
            raise BuildError("Final media validation failed: silent output contains an audio stream")
        if not silent and "audio" not in stream_types:
            raise BuildError("Final media validation failed: expected an audio stream")
        final_temp.replace(output)
    return {"output": str(output), "duration": final_duration, "resolution": list(scale), "fps": project.fps,
            "audio_mode": "silent" if silent else "narration+chalk" if narration else "chalk",
            "narration": str(narration) if narration else None, "media": media}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_DEFAULT)
    parser.add_argument("--output", type=Path, default=ROOT / "people_arent_broken_v2.mp4")
    audio = parser.add_mutually_exclusive_group()
    audio.add_argument("--narration", type=Path)
    audio.add_argument("--silent", action="store_true", help="Render a video-only MP4 with no audio stream")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    storyboard = json.loads(args.storyboard.read_text(encoding="utf-8"))
    validation = validate_storyboard(storyboard)
    if args.validate_only:
        print(json.dumps({"status": "valid", **validation}, indent=2))
        return
    result = render(WhiteboardProject(storyboard), args.output, args.narration, args.preview, args.silent)
    report = {"status": "succeeded", "validation": validation, **result}
    report_path = args.output.with_suffix(".build.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
