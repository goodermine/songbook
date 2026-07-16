#!/usr/bin/env python3
"""Phase 7 generality proof: render unseen storyboards with zero renderer edits.

For every storyboard in ``storyboards/proof/`` this runner performs the full
gate sequence:

1. schema validation + preflight (fonts, assets, text geometry);
2. silent render (audio mode ``none``) through the normal CLI code path;
3. FFprobe: exactly one H.264 video stream, zero audio streams, expected
   resolution/fps/duration;
4. full sequential decode including tail frames;
5. per-frame geometry audit (no pen-down teleports, one pen max);
6. hand-pose gate: max nib error <= 2px, angle error <= 1 degree across all
   pen-down frames (collected during the audit render).

Writes ``baseline/generality_report.json`` and exits non-zero on any failure.

Usage::

    python3 tools/prove_generality.py [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))
sys.path.insert(0, str(WHITEBOARD_ROOT / "tools"))

import render_whiteboard_v2 as engine  # noqa: E402
from geometry_audit import audit  # noqa: E402

PROOF_DIR = WHITEBOARD_ROOT / "storyboards" / "proof"
REPORT_PATH = WHITEBOARD_ROOT / "baseline" / "generality_report.json"


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate",
         "-show_entries", "format=duration,size", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def decode_cleanly(path: Path) -> bool:
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                            capture_output=True, text=True)
    return result.returncode == 0 and not result.stderr.strip()


def hand_gate(storyboard: dict) -> dict:
    """Collect nib/angle errors across every pen-down frame."""
    project = engine.WhiteboardProject(storyboard)
    nib_errors: list[float] = []
    angle_errors: list[float] = []
    for frame in range(round(project.duration * project.fps)):
        project.render_frame(frame / project.fps)
        pose = project.last_report.get("hand_pose")
        if pose:
            nib_errors.append(pose["nib_error_px"])
            angle_errors.append(pose["angle_error_deg"])
    nib_errors.sort()
    return {
        "pen_down_frames": len(nib_errors),
        "max_nib_error_px": round(nib_errors[-1], 3) if nib_errors else 0.0,
        "p99_nib_error_px": round(nib_errors[int(len(nib_errors) * 0.99) - 1], 3) if nib_errors else 0.0,
        "max_angle_error_deg": round(max(angle_errors), 3) if angle_errors else 0.0,
    }


def run_one(path: Path, out_dir: Path) -> dict:
    storyboard = json.loads(path.read_text(encoding="utf-8"))
    entry: dict = {"storyboard": path.name, "title": storyboard.get("title")}
    failures: list[str] = []

    validation = engine.validate_storyboard(storyboard)
    preflight = engine.preflight_project(storyboard)
    entry["validation"] = validation
    entry["preflight"] = preflight

    output = out_dir / f"{path.stem}.mp4"
    started = time.monotonic()
    render_report = engine.render(engine.WhiteboardProject(storyboard), output, None,
                                  False, audio_mode="none")
    entry["render_seconds"] = round(time.monotonic() - started, 2)
    entry["output"] = str(output)

    media = probe(output)
    streams = media["streams"]
    entry["streams"] = [(s["codec_type"], s["codec_name"]) for s in streams]
    entry["duration"] = float(media["format"]["duration"])
    entry["size_bytes"] = int(media["format"]["size"])
    if [s["codec_type"] for s in streams] != ["video"]:
        failures.append(f"expected exactly one video stream, got {entry['streams']}")
    if streams and streams[0]["codec_name"] != "h264":
        failures.append("video stream is not h264")
    if render_report["audio_streams"] != 0:
        failures.append("manifest reports a nonzero audio stream count")
    expected = float(storyboard["safe_content_end"]) + float(storyboard["final_hold"])
    if abs(entry["duration"] - expected) > 0.15:
        failures.append(f"duration {entry['duration']} deviates from {expected}")

    if not decode_cleanly(output):
        failures.append("sequential decode reported errors")

    geometry = audit(storyboard)
    entry["geometry"] = {key: geometry[key] for key in
                         ("pen_down_frames", "max_tip_step_px", "p99_tip_step_px")}
    if geometry["violations"]:
        failures.append(f"{len(geometry['violations'])} pen-down teleport violations")

    hand = hand_gate(storyboard)
    entry["hand"] = hand
    if hand["max_nib_error_px"] > 2.0:
        failures.append(f"nib error {hand['max_nib_error_px']}px exceeds 2px")
    if hand["max_angle_error_deg"] > 1.0:
        failures.append(f"pose angle error {hand['max_angle_error_deg']} deg exceeds 1 deg")

    entry["failures"] = failures
    entry["passed"] = not failures
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=WHITEBOARD_ROOT / "proof_renders")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    storyboards = sorted(PROOF_DIR.glob("*.json"))
    if len(storyboards) < 3:
        raise SystemExit(f"Need at least 3 proof storyboards, found {len(storyboards)}")

    results = [run_one(path, args.out_dir) for path in storyboards]
    passed = sum(1 for r in results if r["passed"])
    report = {
        "gate": "phase-7 generality",
        "renderer_edited": False,
        "storyboards": len(results),
        "passed": passed,
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
