# People Aren't Broken — Whiteboard Renderer V2

Version two rebuilds the original prototype around a validated, JSON-driven,
single-pen timeline.

## Guarantees

- The storyboard is loaded from `storyboard_v2.json`.
- Every pencil-bearing action is validated before rendering.
- A frame can contain zero or one pencil, never two.
- Compound illustrations are timed by physical path length.
- The pencil rotates with the active path direction.
- Chalk audio is derived from the compiled drawing schedule.
- The final hold and media validation are part of the render command.
- FFmpeg output is written atomically after successful validation.

## Validate without rendering

```bash
python3 render_whiteboard_v2.py --validate-only
```

Expected result:

```json
{
  "status": "valid",
  "actions": 27,
  "pen_actions": 21,
  "pen_collisions": 0,
  "max_active_pens": 1
}
```

## Render the 720p master

```bash
python3 render_whiteboard_v2.py \
  --storyboard storyboard_v2.json \
  --output people_arent_broken_v2_final.mp4
```

## Add narration

Supply any WAV, MP3, M4A or other FFmpeg-readable narration file:

```bash
python3 render_whiteboard_v2.py \
  --storyboard storyboard_v2.json \
  --narration narration.wav \
  --output people_arent_broken_v2_narrated.mp4
```

The renderer mixes the narration above its schedule-derived chalk track and
produces a companion `.build.json` validation report.

## Render without sound

Use `--silent` to create an MP4 with no audio stream at all:

```bash
python3 render_whiteboard_v2.py \
  --storyboard storyboard_v2.json \
  --silent \
  --output people_arent_broken_v2_silent.mp4
```

`--silent` and `--narration` are mutually exclusive. The companion build report
records `"audio_mode": "silent"` and validates that the result has no audio
stream.

## Install Python dependencies

```bash
python3 -m pip install -r requirements_v2.txt
```

FFmpeg and FFprobe must also be installed and available on the system path.
