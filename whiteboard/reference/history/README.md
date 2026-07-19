# People Aren't Broken — Python Whiteboard Prototype

This proof of concept converts a deterministic five-scene storyboard into a
28-second whiteboard-style MP4 without a visual timeline editor.

## Render

```bash
python3 render_whiteboard.py --output people_arent_broken.mp4
```

Add `--preview` for an 854×480 render. The current soundtrack is synchronized
marker/chalk texture rather than narration. Replace the generated WAV with a
recorded read of `narration.txt` in the next iteration.

## What this spike tests

- Progressive path drawing
- A marker and hand following the active stroke
- A reusable scene vocabulary
- Deterministic timing from code
- FFmpeg MP4/audio composition
- No timeline editing

The next architectural step is to move scene content into validated JSON and
replace the renderer with Manim plus `manim-voiceover` once those dependencies
are available.
