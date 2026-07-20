#!/usr/bin/env python3
"""Generate soft pastel watercolour blobs for scattered background shading.

Placed behind a scene's content via show_image, several per scene at random
positions and sizes, they read as loose pastel watercolour washes without
competing with the ink. Low peak alpha + feathered edges keep them subtle.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "assets" / "images"
# Pale, low-saturation pastels — the pale-green watercolour family.
WASHES = {
    "wash_green": (178, 206, 168),
    "wash_mint": (190, 216, 202),
    "wash_sage": (196, 214, 180),
    "wash_sky": (192, 210, 214),
    "wash_peach": (234, 208, 186),
    "wash_amber": (232, 216, 172),
}
W, H, PEAK = 520, 440, 60  # native blob size, peak alpha ~24%


def blob(rgb: tuple[int, int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    ys = np.linspace(-1.0, 1.0, H)[:, None]
    xs = np.linspace(-1.0, 1.0, W)[None, :]
    # Base soft ellipse, warped by a couple of low-frequency lobes for an
    # irregular watercolour edge.
    warp = (0.14 * np.sin(3.1 * xs + rng.uniform(0, 6)) +
            0.12 * np.cos(2.6 * ys + rng.uniform(0, 6)))
    radial = np.clip(1.0 - (xs ** 2 + ys ** 2) * (1.0 + warp), 0.0, 1.0) ** 1.5
    alpha = (radial * PEAK).astype(np.uint8)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = rgb
    rgba[..., 3] = alpha
    img = Image.fromarray(rgba, "RGBA")
    return Image.fromarray(np.asarray(img), "RGBA").filter(ImageFilter.GaussianBlur(6))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (name, rgb) in enumerate(WASHES.items()):
        blob(rgb, i * 7 + 1).save(OUT / f"{name}.png")
        print(f"wrote {name}.png")


if __name__ == "__main__":
    main()
