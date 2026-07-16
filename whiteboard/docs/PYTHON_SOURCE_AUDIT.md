# Python Whiteboard Renderer — Source Audit

Audit target: `render_whiteboard.py` (332 lines)  
Audit date: 16 July 2026  
Scope: architecture, single-pen behaviour, timing, visual authenticity, audio,
layout, portability, performance, reproducibility and failure handling.

## Executive verdict

The source is a successful visual proof of concept, but it is not yet a reusable
whiteboard animation engine. Its deterministic frame rendering and progressive
paths are sound foundations. Its central architectural weakness is that each
drawing helper independently paints its own hand. There is no global pen owner,
event scheduler or invariant preventing simultaneous markers.

The current source therefore violates the intended physical rule:

> Many completed visuals may coexist, but only one pen-bearing drawing action
> may be active at any instant.

Static schedule analysis found 17 overlapping pen windows, with as many as
three simultaneous markers.

## Verification completed

- Python compilation passed with `python3 -m py_compile`.
- The complete source was inspected line by line.
- Representative frames were rendered directly at overlapping timestamps.
- The declared pen-active timing windows were analysed independently.
- The MP4 master was decoded and representative frames were inspected.
- The initial master exhibited corrupted terminal frames; the supplied final
  video was repaired using an additional trim-and-hold encoding step.

## Findings

### P0 — There is no single-pen controller

Relevant code: lines 112–126, 141–153 and the calls throughout lines 185–267.

`reveal_text()` draws its own marker. `draw_paths_progress()` also draws its own
marker. Several scene-specific blocks draw another marker directly. Because
these helpers know nothing about one another, overlapping timing windows create
multiple hands.

Confirmed examples:

| Time window | Simultaneous pen actions | Pen count |
| --- | --- | ---: |
| 1.20–1.60 s | `PEOPLE AREN'T`, `BROKEN`, person | 3 |
| 6.50–6.70 s | heading, person, loop arrow | 3 |
| 11.55–11.75 s | heading, arrow 1, arrow 2 | 3 |
| 17.10–17.70 s | heading and `IDENTITY` | 2 |
| 20.10–20.45 s | break stroke and `FAMILIAR ≠ FIXED` | 2 |
| 24.90–25.90 s | choice path and final heading | 2 |

Impact: the result breaks the physical whiteboard illusion and makes timing
changes unsafe because a harmless overlap can silently add another hand.

Required fix: drawing primitives must return stroke state rather than painting
their own hands. A global `PenScheduler` must grant a single pen lock, render
all geometry, and overlay exactly one hand at the active stroke tip after the
scene is composed. A build-time validator must fail when `active_pen_count > 1`.

### P0 — The storyboard is not connected to the renderer

Relevant code: all content and timings are hard-coded in `render_frame()` at
lines 177–269. `storyboard.json` is never opened or validated.

Impact: editing the purported storyboard has no effect. New videos require
editing Python, making AI storyboard generation, templates and batch rendering
impossible.

Required fix: parse a versioned Pydantic storyboard schema into typed scene and
action objects. Python should implement the renderer; JSON should hold content,
layout intent, timing cues and assets.

### P0 — Narration is not part of the timeline

Relevant code: `make_chalk_audio()` at lines 272–297 creates noise only. The
render function always generates and mixes that WAV at lines 300–311.

Impact: `narration.txt` is unused, there is no voice input, no forced alignment,
no word cues and no subtitle output. Adding a voice track after rendering would
not automatically retime the drawings.

Required fix: accept a narration WAV plus word/phrase timing JSON. Scene actions
should reference semantic cues rather than absolute seconds. Chalk sound should
be mixed beneath the narration, not used as the primary audio track.

### P1 — Text is wiped on horizontally, not written

Relevant code: lines 112–126.

Text is rasterised in full and exposed with a left-to-right rectangular mask.
The marker follows the rectangle edge, not the glyph strokes.

Impact: large headings can look acceptable at normal speed, but close viewing
reveals that letters appear vertically rather than being formed by a pen.

Required fix: use single-line vector fonts or convert supported text into ordered
glyph paths. Animate those paths by length, with horizontal reveal retained only
as an explicitly named fast mode.

### P1 — The renderer is a 93-line scene monolith

Relevant code: `render_frame()` at lines 177–269.

Five scenes, layout, timing, copy and animation logic are coupled inside one
conditional chain.

Impact: reuse is low, tests are difficult and every new video increases the
risk of timing and layout regressions.

Required fix: introduce `Project`, `Scene`, `Action`, `Drawable`, `Track` and
`PenScheduler` abstractions. Each scene should compose reusable actions rather
than branch on global time.

### P1 — Hand orientation is physically incorrect

Relevant code: `draw_marker()` at lines 92–109.

The marker angle is fixed at `-0.68` radians. It does not use the tangent of the
active path.

Impact: the marker can travel sideways or backwards while maintaining the same
orientation, weakening the illusion.

Required fix: every active stroke should return its tip and tangent. Smooth the
tangent across frames, apply a configurable wrist offset, and keep the nib at
the path tip.

### P1 — The final deliverable is not fully reproducible from the script

Relevant code: lines 300–324.

The initial encoded master showed visually corrupted terminal frames. The final
video required an external FFmpeg trim plus cloned-frame hold. That repair is
not represented by `render()`.

Impact: rerunning the documented command does not guarantee the delivered
master.

Required fix: render to a temporary path, validate frame count and tail frames,
apply the final hold inside the declared pipeline, then atomically publish the
output. Preserve FFmpeg diagnostics instead of suppressing all normal context.

### P1 — Layout is fixed to one canvas and can overflow

Relevant code: constants at lines 17–27 and literal coordinates throughout
lines 177–267.

All coordinates assume 1280×720. There is no safe-area system, collision check,
text fitting, responsive layout or vertical format.

Impact: copy changes can clip without raising an error. The prototype already
required a manual font/position correction for the final heading.

Required fix: use normalized anchors, bounding-box constraints and preflight
checks. Text actions should support `fit`, `wrap` and `fail_on_overflow`. Render
16:9 and 9:16 from separate layout templates sharing the same semantic scene.

### P1 — Platform-specific fonts have no fallback

Relevant code: lines 25–27 and 43–45.

The renderer depends on absolute Linux font paths.

Impact: it will fail on Windows, macOS, another container or a clean deployment.

Required fix: bundle licensed fonts or resolve them through a project asset
registry. Fail during preflight with a useful message when an asset is missing.

### P2 — Drawing duration is divided by path count, not path length

Relevant code: lines 141–153.

Each subpath receives an equal fraction of the animation, regardless of its
length. A long circular head and a short limb therefore receive equal time.

Impact: pen velocity changes abruptly and compound figures feel mechanical.

Required fix: allocate time by total geometric length, with optional per-stroke
weights and pen-up travel duration.

### P2 — Audio timing is duplicated and hard-coded

Relevant code: lines 272–291.

Chalk windows and beat taps manually repeat scene timing information already
embedded elsewhere.

Impact: changing a scene can desynchronise sound without any warning.

Required fix: derive sound events from the same compiled action timeline used
for visual rendering.

### P2 — Rendering does unnecessary work per frame

Relevant code: lines 112–123 and 177–269.

Every text call allocates full-frame RGBA layers and masks. Fonts are reloaded
repeatedly. Paths and layout geometry are recalculated for each frame.

Impact: acceptable for a 28-second prototype, but inefficient for batches,
4K output or multiple formats.

Required fix: cache fonts, text layers, path geometry, bounding boxes and static
scene backgrounds. Use dirty-region or layer compositing where worthwhile.

### P2 — Process handling is too thin for unattended generation

Relevant code: lines 300–324.

There is no explicit FFmpeg preflight, timeout, captured diagnostic log,
`BrokenPipeError` explanation, temporary output, cancellation handling or
post-render media validation.

Impact: failures will be difficult for an agent or non-technical user to
diagnose, and a partial file can remain at the requested output path.

Required fix: validate dependencies and assets before rendering, capture
stderr, render atomically, validate with FFprobe, and return a structured build
report.

### P2 — No dependency manifest, tests or schema tests

The project has no `pyproject.toml`, pinned dependency range or automated test
suite.

Minimum required tests:

- `max_active_pens <= 1` for every frame/event interval.
- No text or drawable outside the safe area.
- Every cue resolves to an audio timestamp.
- Every referenced asset and font exists.
- Every scene has a legal duration and transition.
- Deterministic frame hashes for representative timestamps.
- FFprobe confirms codec, resolution, duration, audio and expected frame count.

## What is already good

- The output is deterministic for the same inputs.
- Seeded sketch jitter stays stable instead of flickering frame to frame.
- `partial_polyline()` provides a useful path-length reveal primitive.
- Frame piping avoids writing hundreds of temporary images.
- The paper palette and restrained accent colours are visually coherent.
- Preview rendering and H.264/AAC output are sensible prototype choices.
- The code proved that a timeline-free Python workflow can create a complete
  visual narrative.

## Recommended replacement architecture

1. `StoryboardModel` validates JSON content and asset references.
2. `TimelineCompiler` resolves narration cues and action dependencies.
3. `PenScheduler` serialises every pen-bearing action.
4. Non-pen tracks may animate concurrently: fades, camera movement, highlights
   and already-completed visuals.
5. Drawables return geometry plus `StrokeState(tip, tangent, active)`.
6. `FrameComposer` draws all layers, then overlays exactly one hand.
7. `AudioMixer` derives chalk events from compiled drawing actions and mixes
   them beneath narration.
8. `BuildValidator` checks pen count, overflow, assets, cues and final media.

Suggested action model:

```json
{
  "type": "draw_text",
  "text": "PEOPLE AREN'T BROKEN",
  "cue": "people_arent_broken",
  "duration": 1.6,
  "requires_pen": true,
  "after": null
}
```

If two pen actions request overlapping cues, the compiler should serialise them
according to priority or reject the storyboard. It should never silently draw
another hand.

## Definition of done for engine version 1

- Exactly zero or one visible marker at every frame.
- Storyboard JSON is the source of truth.
- Narration cues drive the timeline.
- Text follows real glyph strokes for the main whiteboard mode.
- Hand angle follows the active path tangent.
- Preflight catches overflow and missing assets before rendering.
- One command produces the validated final MP4 without undocumented repair.
- The same semantic storyboard renders through 16:9 and 9:16 templates.
- Three different 60-second scripts render with under 15 minutes of human
  correction each.

## Recommended decision

Do not add more scenes or AI generation to the current monolithic renderer.
Preserve it as a visual prototype and refactor the engine boundary first. The
single-pen scheduler, storyboard compiler and narration-cue timeline are the
three foundational changes; every later automation feature depends on them.
