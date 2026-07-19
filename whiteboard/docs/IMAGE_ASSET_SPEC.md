# Image asset spec — AI-generated artwork for slides

The engine can place raster artwork (e.g. ChatGPT/DALL-E images) on slides
with the `show_image` action. Images are *placed artwork*: they fade in, no
hand appears over them, and the marker never pretends to draw them — the
physical rules stay honest. Use stroke assets for anything the hand should
draw; use images for hero illustrations the pen can't do justice.

## Drop-in workflow

1. Generate the image (see prompts below).
2. Save it as a **transparent PNG** into `whiteboard/assets/images/<name>.png`
   (snake_case name, no spaces).
3. Reference it from any storyboard:

```json
{"id": "hero", "type": "show_image", "image": "arch_hero",
 "at": [540, 800], "height": 620, "start": 3.0, "duration": 1.2,
 "requires_pen": false}
```

`at` is the image centre on the board; `height` is the rendered height in
board pixels (width follows the aspect ratio). Preflight fails before
rendering if the file is missing or the placed image leaves the board.

## Generation rules (give these to ChatGPT)

- **Transparent background** — no scene, no backdrop, no drop shadow onto a
  background. The board supplies the paper.
- **No text in the image.** All words are hand-written by the engine's stroke
  font; baked-in text will clash and can't be animated.
- **One subject per image**, centred, with ~5 % margin inside the canvas.
- **Palette** (match the board): ink `#262B2E`, teal `#1F6F70`, marker orange
  `#CA5330`, warm paper cream `#F9F7F0` for highlights only. Muted, flat.
- **Style**: consistent across the whole set — flat vector-like marker
  illustration, confident 4–8 px line work, minimal shading, no gradients,
  no photorealism (it fights the hand-drawn strokes around it).
- **Size**: 1024–1536 px on the long edge, PNG.
- No real people's likenesses; no medical imagery; faces stylised only.

### Prompt template

> Flat vector-style marker illustration of **[SUBJECT]**, single subject
> centred on a fully transparent background, muted palette of charcoal
> `#262B2E`, teal `#1F6F70` and burnt orange `#CA5330`, confident uniform
> line weight, minimal flat shading, no gradients, no text, no background
> elements, PNG with transparency.

## Suggested set for the SDH snippet series

| File name | Subject |
| --- | --- |
| `arch_hero.png` | Stone arch with a subtly glowing wedge keystone at the crown |
| `arch_falling.png` | The same arch mid-collapse, stones separating, keystone free |
| `two_chairs.png` | Two simple facing armchairs, angled toward each other — the dialogue |
| `presence_triad.png` | Three icons in a row: an eye, a sound wave, an hourglass (eyes / voice / pause) |
| `signal_compass.png` | A hand compass with the needle glowing teal — "the signal is your compass" |
| `question_path.png` | A winding path made of question marks leading to a keyhole |
| `iceberg_mind.png` | An iceberg: small crown above the waterline, vast mass below — conscious/unconscious |
| `open_ground.png` | A person standing in open ground where ruins of an arch lie behind them |
| `book_cover.png` | A hardcover book standing upright, plain cover, teal spine (title added by the engine) |

Keep the whole set in one ChatGPT conversation so the style stays uniform,
and regenerate any image that drifts. Import needs no calibration — unlike
the hand sprite, images have no anchors; drop the PNG in and reference it.
