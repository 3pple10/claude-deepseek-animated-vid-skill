#!/usr/bin/env bash
# frames.sh - deterministic ffmpeg helpers for the video-cinematic pipeline.
#   frames.sh probe clip.mp4
#   frames.sh first-frame clip.mp4 out.png
#   frames.sh mid-frame clip.mp4 out.png
#   frames.sh last-frame clip.mp4 out.png
#   frames.sh normalize in.mp4 out.mp4 WIDTH HEIGHT FPS
#   frames.sh stitch out.mp4 normalized1.mp4 normalized2.mp4 ...
set -euo pipefail
cmd="${1:-}"; shift || true

dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
has_audio() { [ -n "$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$1")" ]; }

case "$cmd" in
  probe)
    ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate:format=duration \
      -of default=nw=1 "$1" ;;
  first-frame)
    ffmpeg -v error -y -i "$1" -frames:v 1 "$2" ;;
  mid-frame)
    t=$(python3 -c "print(float('$(dur "$1")')/2)")
    ffmpeg -v error -y -ss "$t" -i "$1" -frames:v 1 "$2" ;;
  last-frame)
    ffmpeg -v error -y -sseof -0.2 -i "$1" -update 1 -q:v 2 "$2" ;;
  normalize)
    in="$1"; out="$2"; w="$3"; h="$4"; fps="$5"
    vf="scale=${w}:${h}:force_original_aspect_ratio=decrease,pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2,fps=${fps},format=yuv420p"
    if has_audio "$in"; then
      ffmpeg -v error -y -i "$in" -vf "$vf" -c:v libx264 -preset veryfast -crf 18 \
        -c:a aac -ar 48000 -ac 2 "$out"
    else
      ffmpeg -v error -y -i "$in" -f lavfi -i anullsrc=r=48000:cl=stereo -vf "$vf" -shortest \
        -c:v libx264 -preset veryfast -crf 18 -c:a aac "$out"
    fi ;;
  stitch)
    out="$1"; shift
    list=$(mktemp)
    for f in "$@"; do echo "file '$(realpath "$f")'" >> "$list"; done
    ffmpeg -v error -y -f concat -safe 0 -i "$list" -c copy "$out"
    rm -f "$list" ;;
  *)
    echo "usage: frames.sh {probe|first-frame|mid-frame|last-frame|normalize|stitch} ..." >&2
    exit 2 ;;
esac
