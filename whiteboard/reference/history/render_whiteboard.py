#!/usr/bin/env python3
"""Dependency-light whiteboard animation prototype using Pillow and FFmpeg."""

from __future__ import annotations

import argparse
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


W, H = 1280, 720
FPS = 24
DURATION = 28.0
PAPER = (249, 247, 240)
INK = (38, 43, 46)
FAINT = (118, 120, 116)
ACCENT = (202, 83, 48)
TEAL = (31, 111, 112)
FONT_REGULAR = "/usr/share/fonts/opentype/urw-base35/URWBookman-Light.otf"
FONT_BOLD = "/usr/share/fonts/opentype/urw-base35/URWBookman-Demi.otf"
FONT_ITALIC = "/usr/share/fonts/opentype/urw-base35/URWBookman-LightItalic.otf"


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def smooth(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def progress(t: float, start: float, duration: float) -> float:
    return smooth((t - start) / duration)


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_ITALIC if italic else FONT_REGULAR
    return ImageFont.truetype(path, size)


def paper_texture() -> Image.Image:
    rng = random.Random(17)
    image = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(image)
    for _ in range(2400):
        x, y = rng.randrange(W), rng.randrange(H)
        shade = rng.choice([(228, 225, 216), (241, 237, 228), (255, 253, 247)])
        d.point((x, y), fill=shade)
    for y in range(16, H, 34):
        d.line((0, y, W, y), fill=(246, 243, 235), width=1)
    return image


BASE = paper_texture()


def partial_polyline(points: list[tuple[float, float]], p: float) -> tuple[list[tuple[float, float]], tuple[float, float]]:
    if not points:
        return [], (0, 0)
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    target = clamp(p) * total
    out = [points[0]]
    for a, b, length in zip(points, points[1:], lengths):
        if target >= length:
            out.append(b)
            target -= length
        else:
            ratio = target / length if length else 0
            tip = (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
            out.append(tip)
            return out, tip
    return out, points[-1]


def sketch_line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color=INK, width=6, seed=1) -> None:
    if len(points) < 2:
        return
    rng = random.Random(seed)
    for pass_no in range(2):
        jittered = [(x + rng.uniform(-1.7, 1.7), y + rng.uniform(-1.7, 1.7)) for x, y in points]
        draw.line(jittered, fill=color, width=max(1, width - pass_no * 2), joint="curve")


def draw_marker(draw: ImageDraw.ImageDraw, x: float, y: float, angle: float = -0.68) -> None:
    # The marker nib sits exactly on (x, y); the hand follows behind it.
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx
    tip = (x, y)
    back = (x - dx * 88, y - dy * 88)
    marker = [
        (tip[0] + px * 6, tip[1] + py * 6),
        (back[0] + px * 10, back[1] + py * 10),
        (back[0] - px * 10, back[1] - py * 10),
        (tip[0] - px * 6, tip[1] - py * 6),
    ]
    draw.polygon(marker, fill=(64, 70, 72), outline=(26, 30, 32))
    palm = (back[0] - dx * 22, back[1] - dy * 22)
    draw.ellipse((palm[0] - 28, palm[1] - 22, palm[0] + 31, palm[1] + 24), fill=(214, 164, 125), outline=(123, 82, 58), width=2)
    for offset in (-13, 0, 13):
        fx, fy = back[0] + px * offset, back[1] + py * offset
        draw.line((palm[0], palm[1], fx, fy), fill=(169, 113, 80), width=5)


def reveal_text(base: Image.Image, text: str, xy: tuple[int, int], size: int, p: float,
                color=INK, bold=False, italic=False, hand=True) -> tuple[float, float]:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    f = font(size, bold=bold, italic=italic)
    ld.text(xy, text, font=f, fill=(*color, 255), stroke_width=0)
    bbox = ld.textbbox(xy, text, font=f)
    reveal_x = bbox[0] + (bbox[2] - bbox[0]) * clamp(p)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle((bbox[0] - 5, bbox[1] - 8, reveal_x, bbox[3] + 8), fill=255)
    base.alpha_composite(Image.composite(layer, Image.new("RGBA", (W, H)), mask))
    if hand and 0.02 < p < 0.99:
        draw_marker(ImageDraw.Draw(base), reveal_x + 4, (bbox[1] + bbox[3]) / 2 + 8)
    return reveal_x, (bbox[1] + bbox[3]) / 2


def person_paths(cx: float, cy: float) -> list[list[tuple[float, float]]]:
    head = [(cx + math.cos(a) * 35, cy - 105 + math.sin(a) * 35) for a in np.linspace(-math.pi / 2, 3 * math.pi / 2, 36)]
    return [
        head,
        [(cx, cy - 70), (cx, cy + 15)],
        [(cx, cy - 35), (cx - 55, cy - 2)],
        [(cx, cy - 35), (cx + 55, cy - 2)],
        [(cx, cy + 15), (cx - 48, cy + 83)],
        [(cx, cy + 15), (cx + 48, cy + 83)],
    ]


def draw_paths_progress(draw: ImageDraw.ImageDraw, paths, p, color=INK, width=6, seed=20, marker=True):
    p = clamp(p)
    slot = p * len(paths)
    active_tip = None
    for i, path in enumerate(paths):
        pp = clamp(slot - i)
        if pp > 0:
            partial, tip = partial_polyline(path, pp)
            sketch_line(draw, partial, color=color, width=width, seed=seed + i)
            if 0 < pp < 1:
                active_tip = tip
    if marker and active_tip:
        draw_marker(draw, *active_tip)


def arrow_path(x1, y1, x2, y2, bend=0.0, samples=45):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    nx, ny = -(y2 - y1), x2 - x1
    length = math.hypot(nx, ny) or 1
    cx, cy = mx + nx / length * bend, my + ny / length * bend
    pts = []
    for u in np.linspace(0, 1, samples):
        x = (1-u)**2*x1 + 2*(1-u)*u*cx + u*u*x2
        y = (1-u)**2*y1 + 2*(1-u)*u*cy + u*u*y2
        pts.append((x, y))
    return pts


def arrow_head(draw, tip, prev, color=INK, width=6, seed=1):
    a = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
    size = 23
    left = (tip[0] - math.cos(a - .55) * size, tip[1] - math.sin(a - .55) * size)
    right = (tip[0] - math.cos(a + .55) * size, tip[1] - math.sin(a + .55) * size)
    sketch_line(draw, [left, tip, right], color=color, width=width, seed=seed)


def render_frame(t: float) -> Image.Image:
    image = BASE.convert("RGBA")
    d = ImageDraw.Draw(image)
    # Persistent footer and progress thread.
    d.text((55, 665), "A WHITEBOARD THOUGHT EXPERIMENT", font=font(19, italic=True), fill=FAINT)
    d.line((55, 640, 1225, 640), fill=(224, 220, 210), width=2)
    d.line((55, 640, 55 + 1170 * clamp(t / DURATION), 640), fill=TEAL, width=4)

    if t < 5.2:
        reveal_text(image, "PEOPLE AREN'T", (92, 72), 61, progress(t, .2, 1.4), bold=True)
        reveal_text(image, "BROKEN", (690, 72), 74, progress(t, 1.2, 1.2), color=ACCENT, bold=True)
        draw_paths_progress(d, person_paths(390, 370), progress(t, 1.0, 2.2), seed=100)
        # Crack lines tempt the viewer toward the label.
        cracks = [[(390, 268), (374, 293), (392, 310)], [(392, 310), (370, 337)], [(392, 310), (414, 339)]]
        draw_paths_progress(d, cracks, progress(t, 2.1, 1.0), color=ACCENT, width=4, seed=140, marker=False)
        # Cross out the diagnosis.
        cross = [[(665, 105), (1025, 160)], [(1010, 92), (685, 175)]]
        draw_paths_progress(d, cross, progress(t, 3.1, 1.0), color=ACCENT, width=9, seed=160)
        reveal_text(image, "That label explains nothing.", (670, 235), 38, progress(t, 3.8, .9), italic=True, hand=False)

    elif t < 10.2:
        reveal_text(image, "THEY'RE REHEARSED.", (120, 72), 70, progress(t, 5.2, 1.5), bold=True)
        draw_paths_progress(d, person_paths(640, 365), progress(t, 5.3, 1.8), seed=200)
        loop = []
        for a in np.linspace(-.55, math.pi * 1.73, 100):
            loop.append((640 + math.cos(a) * 235, 360 + math.sin(a) * 190))
        pp = progress(t, 6.5, 2.6)
        partial, tip = partial_polyline(loop, pp)
        sketch_line(d, partial, color=TEAL, width=8, seed=230)
        if pp > .95:
            arrow_head(d, loop[-1], loop[-4], color=TEAL, width=8, seed=231)
        elif pp > .02:
            draw_marker(d, *tip)
        for i, word in enumerate(["trigger", "reaction", "relief", "repeat"]):
            a = -.42 + i * 1.55
            x, y = 640 + math.cos(a) * 290, 360 + math.sin(a) * 225
            if t > 7.0 + i * .55:
                d.text((x - 40, y - 14), word, font=font(25, italic=True), fill=FAINT)

    elif t < 16.2:
        reveal_text(image, "A REACTION REPEATED", (128, 82), 59, progress(t, 10.2, 1.8), bold=True)
        reveal_text(image, "BECOMES A PATTERN.", (290, 492), 62, progress(t, 14.0, 1.45), color=TEAL, bold=True)
        x_positions = [205, 420, 635, 850, 1065]
        for i, x in enumerate(x_positions):
            p = progress(t, 11.0 + i * .55, .75)
            path = arrow_path(x - 75, 310, x + 75, 310, bend=-28)
            partial, tip = partial_polyline(path, p)
            sketch_line(d, partial, color=INK if i < 4 else TEAL, width=6, seed=300 + i)
            if p > .95:
                arrow_head(d, path[-1], path[-4], color=INK if i < 4 else TEAL, width=6, seed=320+i)
            elif p > .05:
                draw_marker(d, *tip)
            if p > .4:
                d.ellipse((x - 18, 348, x + 18, 384), outline=ACCENT, width=5)

    elif t < 21.7:
        reveal_text(image, "A PATTERN CAN FEEL LIKE", (135, 78), 53, progress(t, 16.2, 1.5), bold=True)
        reveal_text(image, "IDENTITY", (430, 180), 87, progress(t, 17.1, 1.2), color=ACCENT, bold=True)
        box = [[(330, 160), (950, 160), (950, 395), (330, 395), (330, 160)]]
        draw_paths_progress(d, box, progress(t, 17.7, 1.6), color=INK, width=7, seed=400)
        reveal_text(image, "THIS IS JUST WHO I AM", (382, 320), 35, progress(t, 18.5, 1.2), italic=True, hand=False)
        # Break open the identity box.
        break_paths = [[(640, 158), (610, 210), (662, 255), (620, 312), (650, 395)]]
        draw_paths_progress(d, break_paths, progress(t, 19.4, .9), color=PAPER, width=18, seed=420, marker=False)
        draw_paths_progress(d, break_paths, progress(t, 19.55, .9), color=ACCENT, width=5, seed=421)
        reveal_text(image, "FAMILIAR ≠ FIXED", (462, 475), 54, progress(t, 20.1, 1.0), color=TEAL, bold=True)

    else:
        reveal_text(image, "INTERRUPT THE REHEARSAL.", (105, 70), 60, progress(t, 21.7, 1.5), bold=True)
        # Old loop on left.
        loop = [(345 + math.cos(a)*125, 330 + math.sin(a)*115) for a in np.linspace(0, math.pi*2, 80)]
        partial, _ = partial_polyline(loop, progress(t, 22.0, 1.1))
        sketch_line(d, partial, color=FAINT, width=6, seed=500)
        # Pause interrupts it.
        pp = progress(t, 22.7, .7)
        if pp > 0:
            h = 110 * pp
            sketch_line(d, [(322, 275), (322, 275+h)], color=ACCENT, width=14, seed=510)
            sketch_line(d, [(370, 275), (370, 275+h)], color=ACCENT, width=14, seed=511)
        # New path moves upward and right.
        path = [(465, 425), (540, 395), (615, 420), (700, 340), (790, 355), (875, 250), (1010, 215)]
        p = progress(t, 23.6, 2.3)
        partial, tip = partial_polyline(path, p)
        sketch_line(d, partial, color=TEAL, width=9, seed=530)
        if p > .95:
            arrow_head(d, path[-1], path[-2], color=TEAL, width=9, seed=531)
        elif p > .02:
            draw_marker(d, *tip)
        reveal_text(image, "PRACTICE A DIFFERENT RESPONSE.", (390, 470), 36, progress(t, 24.9, 1.4), color=TEAL, bold=True)
        reveal_text(image, "Repetition built the pattern.", (425, 545), 27, progress(t, 26.0, .7), italic=True, hand=False)
        reveal_text(image, "Repetition can build the way out.", (425, 582), 27, progress(t, 26.5, .8), color=ACCENT, italic=True, hand=False)

    return image.convert("RGB")


def make_chalk_audio(path: Path) -> None:
    rate = 48_000
    n = int(DURATION * rate)
    rng = np.random.default_rng(42)
    audio = np.zeros(n, dtype=np.float32)
    draw_windows = [(0.3,4.8),(5.2,9.8),(10.2,15.8),(16.2,21.2),(21.7,27.5)]
    for start, end in draw_windows:
        a, b = int(start*rate), int(end*rate)
        noise = rng.normal(0, 1, b-a).astype(np.float32)
        kernel = np.ones(24, dtype=np.float32) / 24
        textured = noise - np.convolve(noise, kernel, mode="same")
        envelope = np.sin(np.linspace(0, math.pi, b-a)) ** .35
        audio[a:b] += textured * envelope * .026
    # Soft taps at conceptual beats.
    for beat in [3.2, 6.5, 10.2, 16.2, 21.7, 23.6, 27.2]:
        a = int(beat*rate)
        length = int(.12*rate)
        x = np.linspace(0, .12, length, endpoint=False)
        tap = np.sin(2*math.pi*150*x) * np.exp(-x*42) * .12
        audio[a:a+length] += tap.astype(np.float32)
    pcm = (np.clip(audio, -.95, .95) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def render(output: Path, preview: bool = False) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    audio = output.with_suffix(".wav")
    make_chalk_audio(audio)
    scale_w, scale_h = (854, 480) if preview else (W, H)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{scale_w}x{scale_h}",
        "-r", str(FPS), "-i", "-", "-i", str(audio),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_number in range(round(DURATION * FPS)):
            frame = render_frame(frame_number / FPS)
            if preview:
                frame = frame.resize((scale_w, scale_h), Image.Resampling.LANCZOS)
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise SystemExit("FFmpeg render failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("people_arent_broken.mp4"))
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    render(args.output, args.preview)
