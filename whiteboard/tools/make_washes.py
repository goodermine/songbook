#!/usr/bin/env python3
"""Generate soft translucent colour-wash bands for side shading.

These are placed behind a scene's content via show_image to add gentle colour
to the margins without competing with the ink. Feathered edges + low peak
alpha keep them subtle so handwriting stays crisp.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "assets" / "images"
WASHES = {
    "wash_green": (122, 160, 120),
    "wash_teal": (31, 111, 112),
    "wash_amber": (232, 163, 61),
    "wash_orange": (202, 83, 48),
}
WIDTH, HEIGHT, PEAK = 360, 1120, 74  # peak alpha ~29%


def band(rgb: tuple[int, int, int]) -> Image.Image:
    ys = np.linspace(-1.0, 1.0, HEIGHT)[:, None]
    xs = np.linspace(-1.0, 1.0, WIDTH)[None, :]
    # Smooth elliptical falloff, feathered to zero at the edges.
    radial = np.clip(1.0 - (xs ** 2 * 0.9 + ys ** 2 * 0.85), 0.0, 1.0) ** 1.4
    alpha = (radial * PEAK).astype(np.uint8)
    rgba = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = rgb
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rgb in WASHES.items():
        band(rgb).save(OUT / f"{name}.png")
        print(f"wrote {name}.png")


if __name__ == "__main__":
    main()
