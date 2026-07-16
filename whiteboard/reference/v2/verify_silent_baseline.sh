#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
output="${1:-$project_dir/reproduced_silent.mp4}"

cd "$project_dir"

python3 -m py_compile render_whiteboard_v2.py
python3 render_whiteboard_v2.py --validate-only
python3 render_whiteboard_v2.py \
  --storyboard storyboard_v2.json \
  --silent \
  --output "$output"

ffprobe -v error \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size \
  -of json "$output"

ffmpeg -v error -i "$output" -f null -

echo "Baseline verification passed: $output"
