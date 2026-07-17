#!/usr/bin/env python3
"""Per-frame pen diagnostics: prove the nib never teleports while pen-down.

Renders every frame of a storyboard (no FFmpeg involved), reads the per-frame
pen report and measures tip movement between consecutive pen-down frames of
the same stroke. Instant jumps — the legacy teleports of 65–120 px — show up
as steps far above what any sane drawing speed produces in 1/fps seconds.

Writes a geometry-audit JSON (a required proof artifact) with per-frame
statistics and any violations.

Usage::

    python3 tools/geometry_audit.py --storyboard storyboards/smoke.json \
        --output smoke.geometry-audit.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))

import render_whiteboard_v2 as engine  # noqa: E402

# Fallback pen-down step threshold for actions without a compiled timeline
# (text wipes, legacy mode): a teleport, not drawing, above this speed.
MAX_PEN_DOWN_PX_PER_S = 1200.0

# The smoothstep easing peaks at 1.5x the mean speed mid-stroke; 1.75 leaves
# margin for frame quantisation while still catching every legacy teleport,
# which sits at 10-50x the mean.
EASING_HEADROOM = 1.75


def action_thresholds(storyboard: dict, project) -> dict[str, float]:
    """Per-action pen-down step limits derived from each compiled timeline."""
    thresholds = {}
    if project.pen_physics != "lift":
        return thresholds  # write_text still compiles physically, but keep legacy audits global
    for action in engine.flatten_actions(storyboard):
        if action["type"] in {"draw_asset", "draw_break"}:
            _, stats = engine.compile_drawable(
                engine.action_asset(action, (project.width, project.height)),
                float(action["duration"]), bool(action.get("arrowheads")))
        elif action["type"] == "write_text":
            _, stats = engine.text_timeline(
                action["text"], float(action["x"]), float(action["y"]),
                float(action["size"]), float(action["duration"]),
                (project.width, project.height))
        else:
            continue
        thresholds[action["id"]] = EASING_HEADROOM * stats["draw_px_per_s"] / project.fps
    return thresholds


def audit(storyboard: dict) -> dict:
    engine.validate_storyboard(storyboard)
    engine.preflight_project(storyboard)
    project = engine.WhiteboardProject(storyboard)
    fps = project.fps
    frames = round(project.duration * fps)
    default_threshold = MAX_PEN_DOWN_PX_PER_S / fps
    thresholds = action_thresholds(storyboard, project)

    reports = []
    for frame in range(frames):
        project.render_frame(frame / fps)
        reports.append(project.last_report)

    steps = []
    violations = []
    pen_down_frames = 0
    for previous, current in zip(reports, reports[1:]):
        if current["pen"] == "down":
            pen_down_frames += 1
        same_stroke = (previous["pen"] == "down" and current["pen"] == "down"
                       and previous["owner"] == current["owner"]
                       and previous["stroke"] == current["stroke"])
        if not same_stroke:
            continue
        step = math.dist(previous["tip"], current["tip"])
        steps.append(step)
        threshold = thresholds.get(current["owner"], default_threshold)
        if step > threshold:
            violations.append({
                "time": current["time"],
                "owner": current["owner"],
                "stroke": current["stroke"],
                "step_px": round(step, 1),
                "threshold_px": round(threshold, 1),
            })

    steps.sort()
    return {
        "pen_physics": project.pen_physics,
        "fps": fps,
        "frames": frames,
        "pen_down_frames": pen_down_frames,
        "measured_steps": len(steps),
        "max_tip_step_px": round(steps[-1], 2) if steps else 0.0,
        "p99_tip_step_px": round(steps[int(len(steps) * 0.99) - 1], 2) if steps else 0.0,
        "default_step_threshold_px": round(default_threshold, 2),
        "action_step_thresholds_px": {k: round(v, 2) for k, v in thresholds.items()},
        "violations": violations,
        "max_active_pens": 1,  # a second runtime claim raises inside render_frame
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, default=engine.STORYBOARD_DEFAULT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    storyboard = json.loads(args.storyboard.read_text(encoding="utf-8"))
    result = audit(storyboard)
    result["storyboard"] = str(args.storyboard)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if result["violations"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
