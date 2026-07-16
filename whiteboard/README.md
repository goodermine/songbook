# Whiteboard Video Engine

Programmatic whiteboard-video generator: a structured storyboard JSON goes in,
a finished MP4 comes out — no manual timeline editor. See
`docs/CLAUDE_CODE_HANDOFF.md` for the full mission, product rules and phase
plan; `docs/START_HERE.md` is the original bundle entry point.

Proof video: **People Aren't Broken. They're Rehearsed.**
(`storyboard_v2.json`, 1280x720 @ 24 fps, 28.625 s encoded).

## Layout

| Path | Purpose |
| --- | --- |
| `render_whiteboard_v2.py` | Active CLI/validator/renderer (V2.1: explicit audio modes, typed assets) |
| `asset_registry.py` | Typed `StrokePath`/`Asset` models, JSON loader, geometry preflight |
| `assets/*.json` | Asset geometry (one file per asset) — edit these, not Python |
| `tools/author_library_assets.py` | Parametric generator for the reusable doodle library |
| `storyboard_v2.json` | Active story/timing/style source of truth |
| `storyboards/smoke.json` | 3-second smoke storyboard used by the test suite |
| `timeline.py` | Physical pen-timeline compiler (stroke / arrowhead / travel events) |
| `text_strokes.py` | Hershey single-line font parser and text layout |
| `assets/fonts/futural.jhf` | Bundled Hershey Simplex stroke font (see fonts README) |
| `hand_rig.py` | Nib-anchored hand/marker sprite rig (cached 1° rotations) |
| `assets/hand/` | Generated-once hand sprite + measured metadata |
| `tools/generate_hand.py` | One-time hand sprite generator (never per frame) |
| `tools/bake_assets.py` | Provenance of the asset migration; regenerates `assets/` |
| `tools/asset_contact_sheet.py` | Diagnostic contact sheet (Phase 2 gate artifact) |
| `tools/geometry_audit.py` | Per-frame nib audit; fails on pen-down teleports (Phase 3 gate) |
| `tools/prove_generality.py` | Phase 7 runner: renders + gates all proof storyboards |
| `storyboards/proof/` | Three unseen proof storyboards (render with zero Python edits) |
| `baseline/` | Frozen-baseline evidence (versions, probe, frame hashes, contact sheet) |
| `tests/` | pytest suite (schema, pen scheduler, geometry, audio modes, integration, golden frames) |
| `reference/` | Pristine V2 renderer/master and V1 history — do not edit |
| `docs/` | Handoff, audits, hand asset spec |

## Setup

```bash
python3 -m pip install -r requirements_v2.txt   # Pillow, NumPy
sudo apt-get install ffmpeg fonts-urw-base35    # system dependencies
python3 -m pip install pytest                   # for the test suite
```

FFmpeg 6.x and the URW Bookman fonts are required; without `fonts-urw-base35`
the italic font lookup fails (a known defect — fonts are still resolved via
absolute paths until Phase 4 bundles a stroke font).

## Usage

```bash
# Preflight only
python3 render_whiteboard_v2.py --validate-only

# Default master: video-only, zero audio streams
python3 render_whiteboard_v2.py --storyboard storyboard_v2.json --output out.mp4

# Explicit audio policy
python3 render_whiteboard_v2.py --audio-mode none                       # default
python3 render_whiteboard_v2.py --audio-mode chalk                      # synthesised marker sounds
python3 render_whiteboard_v2.py --audio-mode narration --narration n.wav
python3 render_whiteboard_v2.py --audio-mode mix --narration n.wav      # narration over chalk
```

`--silent` remains as a deprecated alias for `--audio-mode none`. Every build
writes `<output>.build.json` including `audio_mode` and the probed
`audio_streams` count.

## Asset library and placement

26 assets ship in `assets/` — the original scene drawings plus a reusable
doodle library (lightbulb, speech/thought bubbles, star, heart, target, clock,
magnifier, gear, mountain+flag, question/exclamation marks, circle-highlight,
wavy underline, checkmark). Library assets are authored centred on the board;
any `draw_asset`/`draw_break` action can position and resize them with data:

```json
{"id": "idea", "type": "draw_asset", "asset": "lightbulb",
 "at": [250, 400], "scale": 0.8, "start": 3.6, "duration": 1.5,
 "requires_pen": true, "color": "ink", "width": 5}
```

Placement is preflighted: an `at`/`scale` that pushes geometry off the board
fails before rendering. `storyboards/asset_showcase.json` demos the full
library; the labelled contact sheet is `baseline/assets_contact_sheet.png`.

## Tests

```bash
cd whiteboard && python3 -m pytest
```

The golden-frame test is environment-pinned (Pillow 12.3.0, NumPy 2.4.6, URW
Bookman fonts); it skips with a message on other environments instead of
failing. Integration tests render the smoke storyboard end-to-end in all four
audio modes and assert stream counts and clean decodes.

## Phase status

- [x] **Phase 0 — Freeze and measure**: baseline reproduced and recorded
  (`baseline/BASELINE.md`), smoke storyboard added, test suite green.
- [x] **Phase 1 — Explicit audio policy**: `--audio-mode none|chalk|narration|mix`,
  `none` default, no WAV synthesised in `none` mode, manifest reports
  `audio_streams`.
- [x] **Phase 2 — Typed stroke geometry**: `asset_registry.py` with
  `StrokePath`/`Asset` models; all 11 assets baked to `assets/*.json` with
  closed/pen-lift/view-box/arrowhead metadata (`tools/bake_assets.py`);
  geometry preflight (empty paths, NaN, zero-length segments, board clipping,
  view-box mismatch, undeclared discontinuities, self-intersection policy)
  runs before FFmpeg; diagnostic contact sheet at
  `baseline/assets_contact_sheet.png`. Golden frames stayed byte-identical
  through the migration.
- [x] **Phase 3 — Physical timeline**: `timeline.py` compiles drawable actions
  into contiguous `stroke`/`arrowhead`/`travel` events (pen-up travel at 2.5×
  drawing speed, ≥80 ms visible lifts, speed warnings outside 200–2000 px/s).
  Opt-in per storyboard via `"pen_physics": "lift"` — the frozen V2 baseline
  keeps `legacy` and stays byte-identical. In lift mode: the hand lifts
  instead of teleporting, arrowheads are physically traced, the identity-break
  erase mask shares the accent line's partial progress, and the marker angle
  is smoothed over the trailing 22 px of path. Every frame reports
  action/stroke/tip/tangent/pen state (`WhiteboardProject.last_report`);
  `tools/geometry_audit.py` turns that into a proof artifact — smoke (lift):
  **0 violations**; main storyboard (legacy): 72 teleports up to 106 px
  (`baseline/*.geometry-audit.json`).
- [x] **Phase 4 — True stroke text**: bundled Hershey Simplex
  (`assets/fonts/futural.jhf`, ASCII 32–126) parsed by `text_strokes.py`;
  the new `write_text` action lays glyphs out as ordered strokes and compiles
  them through the same physical timeline as illustrations — the nib follows
  letterforms and lifts between disconnected glyph components. At 50 %
  progress only the first half of the ordered glyph strokes exists (gate
  test). Overflowing or unsupported text fails preflight before rendering.
  The raster wipe survives only as `draw_text`/`fast_reveal_text`.
- [x] **Phase 5 — Hand/marker rig**: illustrated right hand holding a dark
  marker, generated **once** by `tools/generate_hand.py` and committed under
  `assets/hand/` with measured nib anchor, native pen angle and wrist anchor.
  `hand_rig.py` rotates around the nib anchor (not the image centre) with 1°
  quantised cached rotations; the barrel keeps a natural base angle and sways
  at most ±10° with the stroke direction. Opt-in via `"hand": "sprite"`
  (default `procedural` keeps the baseline). Gates enforced by tests: nib
  error ≤ 2 px for 100 % of poses, commanded/rendered angle within 1°,
  bounded wrist, hand visible only while a pen is down. Open aesthetic
  choices (skin tone, left/right, style) remain owner-swappable — replace the
  sprite + metadata, not code.
- [ ] **Phase 6 — Rendering/illustration quality** (supersampling/Cairo
  antialiasing, explicit transition policy, 9:16 templates, cohesive doodle
  vocabulary — largely aesthetic; traced arrowheads and progressive break
  erasure already landed with Phase 3). Open owner decisions: hand style/skin
  tone/handedness, type personality.
- [x] **Phase 7 — Generality proof**: three unseen 30–35 s storyboards
  (`storyboards/proof/`) — *Habits Compound*, *React or Respond*, *Practice
  Makes Patterns* — plus a hand-authored JSON asset (`assets/checkmark.json`)
  render **3/3 with zero renderer edits** via `tools/prove_generality.py`.
  Per video: one H.264 stream, zero audio streams, clean tail decode, zero
  pen collisions, zero pen-down teleports, max nib error 0.68 px (≤2 px
  gate), max pose-angle error 0.49° (≤1° gate). Report:
  `baseline/generality_report.json`.

Non-negotiable product rules (one hand, one pen-down stroke, nib on the stroke
front, no teleporting, silent = zero audio streams, storyboards not Python for
new videos) are listed in `docs/CLAUDE_CODE_HANDOFF.md` §7 and enforced
incrementally by the test suite.
