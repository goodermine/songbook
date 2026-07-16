"""Nib-anchored hand/marker sprite rig.

Loads the generated-once hand sprite plus its measured metadata (nib anchor,
native pen angle, wrist anchor) and poses it at the active stroke tip:

- transforms rotate around the **nib anchor**, not the image centre, so the
  visible nib sits on the stroke front by construction;
- rotations are quantised to 1 degree and cached, so at most 360 rotated
  sprites ever exist (nothing is regenerated per frame);
- the marker barrel does NOT point along every path segment: the wrist keeps
  a natural base angle and follows the stroke direction only within a bounded
  ±``MAX_WRIST_DEVIATION_DEG`` window, like a real writer.

``draw()`` composites the sprite and returns pose diagnostics (commanded vs
rendered angle, nib placement error) for the hand-quality gates.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image

HAND_DIR = Path(__file__).resolve().parent / "assets" / "hand"
DEFAULT_NAME = "hand_right_marker"

BASE_BARREL_DEG = 54.0          # natural resting barrel direction (screen, y down)
MAX_WRIST_DEVIATION_DEG = 10.0  # bounded, smoothed variation around the base
DEVIATION_GAIN = 0.15           # fraction of the tangent swing passed to the wrist
ANGLE_QUANTUM_DEG = 1.0


class HandRigError(RuntimeError):
    pass


def _wrap_degrees(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


class HandRig:
    def __init__(self, directory: Path = HAND_DIR, name: str = DEFAULT_NAME) -> None:
        sprite_path = directory / f"{name}.png"
        metadata_path = directory / f"{name}.json"
        if not sprite_path.is_file() or not metadata_path.is_file():
            raise HandRigError(f"Hand rig asset missing: {sprite_path} / {metadata_path}. "
                               f"Generate it once with tools/generate_hand.py")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.sprite = Image.open(sprite_path).convert("RGBA")
        self.nib = (float(metadata["nib"][0]), float(metadata["nib"][1]))
        self.pen_angle_deg = float(metadata["pen_angle_deg"])
        self.wrist = (float(metadata["wrist"][0]), float(metadata["wrist"][1]))
        if not (0 <= self.nib[0] < self.sprite.width and 0 <= self.nib[1] < self.sprite.height):
            raise HandRigError(f"Nib anchor {self.nib} lies outside the sprite")

    def commanded_angle(self, tangent: tuple[float, float]) -> float:
        """Barrel direction for a stroke tangent: base angle plus bounded sway."""
        if abs(tangent[0]) < 1e-12 and abs(tangent[1]) < 1e-12:
            return BASE_BARREL_DEG
        # The barrel trails the nib the way the legacy marker did (~0.58 rad
        # behind the stroke direction, pointing back from the tip).
        desired = math.degrees(math.atan2(tangent[1], tangent[0]) - 0.58) + 180.0
        deviation = _wrap_degrees(desired - BASE_BARREL_DEG) * DEVIATION_GAIN
        deviation = max(-MAX_WRIST_DEVIATION_DEG, min(MAX_WRIST_DEVIATION_DEG, deviation))
        return BASE_BARREL_DEG + deviation

    @lru_cache(maxsize=512)
    def _rotated(self, quantized_deg: float) -> Image.Image:
        # PIL rotates counterclockwise on screen; in y-down coordinates a
        # rotate(theta) maps a direction angle phi to phi - theta.
        theta = self.pen_angle_deg - quantized_deg
        return self.sprite.rotate(theta, center=self.nib,
                                  resample=Image.Resampling.BICUBIC)

    def draw(self, image: Image.Image, tip: tuple[float, float],
             tangent: tuple[float, float]) -> dict:
        commanded = self.commanded_angle(tangent)
        quantized = round(commanded / ANGLE_QUANTUM_DEG) * ANGLE_QUANTUM_DEG
        rotated = self._rotated(quantized)
        paste_x = round(tip[0] - self.nib[0])
        paste_y = round(tip[1] - self.nib[1])
        image.alpha_composite(rotated, (paste_x, paste_y))
        rendered_nib = (paste_x + self.nib[0], paste_y + self.nib[1])
        return {
            "commanded_angle_deg": commanded,
            "rendered_angle_deg": quantized,
            "angle_error_deg": abs(_wrap_degrees(commanded - quantized)),
            "nib_error_px": math.dist(tip, rendered_nib),
            "wrist_deviation_deg": _wrap_degrees(quantized - BASE_BARREL_DEG),
        }


@lru_cache(maxsize=1)
def default_rig() -> HandRig:
    return HandRig()
