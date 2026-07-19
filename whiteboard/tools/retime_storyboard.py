#!/usr/bin/env python3
"""Retime a storyboard's scenes to match a narration's actual pacing.

Given one boundary time per scene transition (seconds into the narration
audio), each scene window is remapped onto its narrated segment:

- action start offsets scale linearly with the scene;
- when a scene gets LONGER, action durations are preserved — drawing speed
  stays natural and the extra time becomes holds between actions;
- when a scene gets SHORTER, starts and durations compress together so pen
  windows can never collide.

Boundaries typically come from silence detection or a timestamped transcript
of the narration. The last scene is extended to ``audio_end + tail``.

Usage::

    python3 tools/retime_storyboard.py storyboards/vocal_warmup.json \
        --boundaries 10.9,28.6,44.6,62.0,71.8,88.4,109.3,122.5,136.9,154.35,166.5 \
        --audio-end 178.03 --output storyboards/vocal_warmup_narrated.json \
        --set chrome=none
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

import render_whiteboard_v2 as engine  # noqa: E402


def retime(storyboard: dict, boundaries: list[float], audio_end: float,
           tail: float = 1.6) -> dict:
    scenes = storyboard["scenes"]
    if len(boundaries) != len(scenes) - 1:
        raise SystemExit(f"Need {len(scenes) - 1} boundaries for {len(scenes)} scenes, "
                         f"got {len(boundaries)}")
    if sorted(boundaries) != boundaries:
        raise SystemExit("Boundaries must be ascending")

    starts = [0.0, *boundaries]
    ends = [*boundaries, audio_end + tail]
    for scene, new_start, new_end in zip(scenes, starts, ends):
        old_start, old_end = float(scene["start"]), float(scene["end"])
        factor = (new_end - new_start) / (old_end - old_start)
        for action in scene["actions"]:
            offset = float(action["start"]) - old_start
            action["start"] = round(new_start + offset * factor, 3)
            if factor < 1.0:
                action["duration"] = round(float(action["duration"]) * factor, 3)
        scene["start"], scene["end"] = round(new_start, 3), round(new_end, 3)

    storyboard["content_duration"] = round(ends[-1], 3)
    storyboard["safe_content_end"] = round(ends[-1] - 0.4, 3)
    return storyboard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard", type=Path)
    parser.add_argument("--boundaries", required=True,
                        help="comma-separated scene-transition times in seconds")
    parser.add_argument("--audio-end", type=float, required=True)
    parser.add_argument("--tail", type=float, default=1.6,
                        help="visual hold after the narration ends (default 1.6s)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="set a top-level storyboard field, e.g. chrome=none")
    args = parser.parse_args()

    storyboard = json.loads(args.storyboard.read_text(encoding="utf-8"))
    boundaries = [float(v) for v in args.boundaries.split(",")]
    storyboard = retime(storyboard, boundaries, args.audio_end, args.tail)
    for override in args.set:
        key, _, value = override.partition("=")
        storyboard[key] = value

    validation = engine.validate_storyboard(storyboard)
    preflight = engine.preflight_project(storyboard)
    args.output.write_text(json.dumps(storyboard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "content_duration": storyboard["content_duration"],
                      **validation, "preflight": preflight}, indent=2))


if __name__ == "__main__":
    main()
