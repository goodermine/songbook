#!/usr/bin/env python3
"""Slice an AI-generated sprite sheet into transparent animation frames.

Designed for flat marker-style artwork on a plain (even gradient) backdrop:
light stones / bright saturated accents / near-black ink outlines. The matte
keeps ink and subject pixels and removes backdrop-coloured pixels even inside
the protective ring around outlines, so frames sit on the board with clean
black lines and no grey halo.

Usage::

    python3 tools/slice_sheet.py sheet.png --prefix arch_fall --cols 3 --rows 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = WHITEBOARD_ROOT / "assets" / "images"


def dilate(mask: np.ndarray, rounds: int) -> np.ndarray:
    for _ in range(rounds):
        padded = np.pad(mask, 1, mode="constant")
        mask = (padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] |
                padded[1:-1, 2:] | padded[1:-1, 1:-1] | padded[:-2, :-2] |
                padded[:-2, 2:] | padded[2:, :-2] | padded[2:, 2:])
    return mask


def matte(image: Image.Image, ink_max_lum: int = 42, light_min_lum: int = 118,
          accent_sat: float = 0.30, accent_min_lum: int = 100,
          reach: int = 12) -> Image.Image:
    """Alpha-matte marker artwork off a plain dark(ish) backdrop."""
    arr = np.asarray(image.convert("RGB")).astype(np.int32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx = arr.max(axis=2)
    sat = (mx - arr.min(axis=2)) / np.maximum(mx, 1)

    subject = (lum > light_min_lum) | ((sat > accent_sat) & (lum > accent_min_lum))
    region = dilate(subject, reach)
    ink = lum <= ink_max_lum
    keep = region & (subject | ink)
    # Heal anti-aliased seams between ink and subject without re-adding backdrop.
    keep = dilate(keep, 1) & region

    alpha = (keep * 255).astype(np.uint8)
    rgba = np.dstack([np.asarray(image.convert("RGB")), alpha])
    result = Image.fromarray(rgba, "RGBA")
    result.putalpha(result.getchannel("A").filter(ImageFilter.GaussianBlur(0.8)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("--prefix", required=True, help="output name prefix, e.g. arch_fall")
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--ink-max-lum", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    sheet = matte(Image.open(args.sheet), ink_max_lum=args.ink_max_lum)
    width, height = sheet.size
    args.out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for row in range(args.rows):
        for col in range(args.cols):
            cell = sheet.crop((col * width // args.cols, row * height // args.rows,
                               (col + 1) * width // args.cols, (row + 1) * height // args.rows))
            count += 1
            path = args.out_dir / f"{args.prefix}_{count}.png"
            cell.save(path)
            print(f"wrote {path.name}")
    print(f"{count} frames from {args.sheet.name}")


if __name__ == "__main__":
    main()
