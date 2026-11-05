#!/usr/bin/env bash
# 把动画按帧切成 N 段并行渲染，再无损拼接。用法：./render_parallel.sh 4
set -euo pipefail
cd "$(dirname "$0")"

workers="${1:-4}"
python_bin=../.venv/Scripts/python
total=$(node -p "JSON.parse(require('fs').readFileSync('timeline.json','utf8')).frames.t.length")
out="parallel/n$workers"
rm -rf "$out"
mkdir -p "$out"

start=$(date +%s.%N)
for ((k = 0; k < workers; k++)); do
  first=$((total * k / workers))
  end=$((total * (k + 1) / workers))
  mkdir -p "$out/m$k"
  cp -r media/texts "$out/m$k/texts"
  CLIP_FIRST_FRAME=$first CLIP_END_FRAME=$end "$python_bin" -m manim render \
    -r 1920,1080 --fps 30 --disable_caching --progress_bar none --verbosity WARNING \
    --media_dir "$out/m$k" pulley_scene.py Pulley >"$out/log$k.txt" 2>&1 &
done
wait

: >"$out/list.txt"
for ((k = 0; k < workers; k++)); do
  clip=$(find "$out/m$k" -name 'Pulley.mp4' -not -path '*partial*')
  echo "file '$(cygpath -m "$PWD/$clip")'" >>"$out/list.txt"
done
ffmpeg -y -v error -f concat -safe 0 -i "$out/list.txt" -c copy "$out/joined.mp4"
stop=$(date +%s.%N)

node -e "console.log('workers', $workers, 'seconds', ($stop - $start).toFixed(1))"
ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$out/joined.mp4"
