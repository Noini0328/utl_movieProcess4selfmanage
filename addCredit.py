#!/usr/bin/env python3
"""
Usage:
  python add_credits.py <input.mp4> <text.txt> <left|center|right> <#RRGGBB> <fontsize> <output.mp4>

修正点:
  - enable式: between(t,A,B) → gte(t\\,A)*lte(t\\,B)  (コンマのパース問題を回避)
  - y式: if() を除去し線形式のみ使用 (drawtextはif()非対応)
"""

import sys
import subprocess
import json
import os


def get_video_info(input_file):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", "-select_streams", "v:0", input_file],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    width    = info["streams"][0]["width"]
    height   = info["streams"][0]["height"]
    return duration, width, height


def hex_to_ffmpeg_color(hex_color):
    return "0x" + hex_color.lstrip("#").upper()


def escape_drawtext(text):
    """drawtext フィルタ用エスケープ"""
    text = text.replace("\\", "\\\\")   # バックスラッシュ (最初に処理)
    text = text.replace("'",  "\u2019") # シングルクォートは全角代替
    text = text.replace(":",  "\\:")
    text = text.replace(",",  "\\,")
    text = text.replace("[",  "\\[")
    text = text.replace("]",  "\\]")
    text = text.replace("%",  "\\%")
    return text


def main():
    if len(sys.argv) != 7:
        print("Usage: python add_credits.py <input.mp4> <text.txt> <left|center|right> <#RRGGBB> <fontsize> <output.mp4>")
        sys.exit(1)

    input_file  = sys.argv[1]
    text_file   = sys.argv[2]
    alignment   = sys.argv[3].lower()
    color       = sys.argv[4]
    fontsize    = int(sys.argv[5])
    output_file = sys.argv[6]

    if alignment not in ("left", "center", "right"):
        print("Error: alignment must be left, center, or right")
        sys.exit(1)
    if not os.path.isfile(input_file):
        print(f"Error: input file not found: {input_file}")
        sys.exit(1)
    if not os.path.isfile(text_file):
        print(f"Error: text file not found: {text_file}")
        sys.exit(1)

    print("Getting video info...")
    duration, video_width, video_height = get_video_info(input_file)
    print(f"  Duration: {duration:.2f}s  Resolution: {video_width}x{video_height}")

    if duration <= 10:
        print("Error: video must be longer than 10 seconds")
        sys.exit(1)

    with open(text_file, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    line_height  = int(fontsize * 1.5)
    total_text_h = len(lines) * line_height

    scroll_start = 3.0
    scroll_end   = duration - 3.0
    scroll_dur   = scroll_end - scroll_start

    # 画面下端から登場し、テキスト全体が画面上に消え切るまでの距離
    scroll_dist  = video_height + total_text_h
    speed        = scroll_dist / scroll_dur   # px/sec

    ffmpeg_color = hex_to_ffmpeg_color(color)

    if alignment == "left":
        x_expr = "50"
    elif alignment == "right":
        x_expr = "w-tw-50"
    else:
        x_expr = "(w-tw)/2"

    # ★ enable: between() はコンマがフィルタ区切りと衝突するため
    #           gte(t\,A)*lte(t\,B) 形式を使用
    enable_expr = f"gte(t\\,{scroll_start})*lte(t\\,{scroll_end})"

    # ★ y: if() は drawtext 非対応のため除去
    #       t = scroll_start のとき y = h (画面下端)
    #       t が進むにつれ上にスクロール
    #       enable で表示期間外は描画しないので t < scroll_start でも問題なし

    filters = []
    for i, line in enumerate(lines):
        text    = line if line.strip() else " "
        escaped = escape_drawtext(text)
        y_offset = i * line_height
        y_expr  = f"h-{speed:.4f}*(t-{scroll_start})+{y_offset}"

        filters.append(
            f"drawtext=text='{escaped}'"
            f":fontsize={fontsize}"
            f":fontcolor={ffmpeg_color}"
            f":x={x_expr}"
            f":y={y_expr}"
            f":enable='{enable_expr}'"
        )

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf", vf,
        "-codec:a", "copy",
        output_file
    ]

    print("Running ffmpeg...")
    print(f"  Lines: {len(lines)}, Speed: {speed:.2f}px/s")
    subprocess.run(cmd, check=True)
    print(f"Done! Output: {output_file}")


if __name__ == "__main__":
    main()
