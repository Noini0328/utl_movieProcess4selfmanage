# -*- coding: utf-8 -*-

import subprocess
import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, simpledialog
import flet as ft

# =========================
# frozen 対応（EXE対策）
# =========================
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


# ===== 設定 =====
TARGET_WIDTH, TARGET_HEIGHT = 1280, 720


# =========================
# 共通関数
# =========================

def get_video_duration(file: Path) -> float:
    """動画の長さ（秒）を返す。取得できない場合は0。"""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def get_media_creation_time(file: Path) -> float:
    """メディア作成日時 (UNIXタイム) を取得。なければ更新日時を返す"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_entries", "format_tags=creation_time", str(file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        creation_str = data.get("format", {}).get("tags", {}).get("creation_time")
        if creation_str:
            dt = datetime.fromisoformat(creation_str.replace("Z", "+00:00"))
            return dt.timestamp()
    except Exception:
        pass
    return file.stat().st_mtime  # 代用


def convert_video(infile: Path, outfile: Path):
    """縦横比を維持しつつ1280x720に収め、音量を正規化"""
    vf_filter = (
        f"scale='min({TARGET_WIDTH}/iw,{TARGET_HEIGHT}/ih)*iw':"
        f"'min({TARGET_WIDTH}/iw,{TARGET_HEIGHT}/ih)*ih',"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        "fps=30,format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(infile),
        "-vf", vf_filter,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2",
        str(outfile)
    ]
    subprocess.run(cmd, check=True)


# =========================
# 機能１：結合
# =========================

def concat_videos(input_dir: Path, output_file: Path):
    tmp_dir = input_dir / "tmp_concat"
    tmp_dir.mkdir(exist_ok=True)

    files = [
        f for f in input_dir.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".mts"]
        and get_video_duration(f) > 1.0
    ]

    files = sorted(files, key=get_media_creation_time)

    if not files:
        print("動画がありません")
        return

    converted_files = []
    for i, f in enumerate(files, 1):
        out = tmp_dir / f"temp_{i}.mp4"
        convert_video(f, out)
        converted_files.append(out)

    concat_list = tmp_dir / "list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in converted_files:
            f.write(f"file '{c}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy", str(output_file)
    ]
    subprocess.run(cmd, check=True)

    print("結合完了:", output_file)


# =========================
# 機能２：分割
# =========================

def split_video(input_file: Path, output_dir: Path, seconds: int):
    output_dir.mkdir(exist_ok=True)
    base = input_file.stem

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(seconds),
        "-f", "segment",
        "-reset_timestamps", "1",
        str(output_dir / f"{base}_%03d.mp4")
    ]
    subprocess.run(cmd, check=True)

    print("分割完了:", output_dir)


# =========================
# GUI
# =========================

def launch_gui():

    def concat_gui(e):
        root = tk.Tk()
        root.withdraw()
        input_dir = filedialog.askdirectory(title="入力フォルダを選択")
        if not input_dir:
            return
        output_file = filedialog.asksaveasfilename(
            title="出力ファイルを選択",
            defaultextension=".mp4",  # 拡張子を mp4 にデフォルト指定
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if not output_file:
            return
        concat_videos(Path(input_dir), Path(output_file))

    def split_gui(e):
        root = tk.Tk()
        root.withdraw()
        input_file = filedialog.askopenfilename(title="動画を選択")
        if not input_file:
            return
        seconds = simpledialog.askinteger("秒数指定", "何秒ごとに分割しますか？")
        if not seconds:
            return
        output_dir = filedialog.askdirectory(title="出力フォルダを選択")
        if not output_dir:
            return
        split_video(Path(input_file), Path(output_dir), seconds)

    def main(page: ft.Page):
        page.title = "動画処理ツール"
        
        # 画面サイズを半分に設定
        page.add(
            ft.Text("動画ツール", size=24),
            ft.ElevatedButton("フォルダ内動画を結合", on_click=concat_gui),
            ft.ElevatedButton("動画を秒数で分割", on_click=split_gui),
        )
        
        # 画面サイズを設定
        page.window_width = 600  # 幅を600に設定（お好みで調整）
        page.window_height = 400  # 高さを400に設定（お好みで調整）

        page.update()  # 画面サイズ変更を反映させるために update を呼び出す

    ft.app(target=main)  # fletでウィンドウサイズ設定


# =========================
# argparse
# =========================

def main():

    parser = argparse.ArgumentParser(
        description="動画結合 / 分割ツール"
    )

    subparsers = parser.add_subparsers(dest="mode")

    # concat
    concat_parser = subparsers.add_parser("concat", help="フォルダ内動画を結合")
    concat_parser.add_argument("input_dir")
    concat_parser.add_argument("output_file")

    # split
    split_parser = subparsers.add_parser("split", help="動画を分割")
    split_parser.add_argument("input_file")
    split_parser.add_argument("output_dir")
    split_parser.add_argument("seconds", type=int)

    # gui
    subparsers.add_parser("gui", help="GUI起動")

    args = parser.parse_args()

    if args.mode == "concat":
        concat_videos(Path(args.input_dir), Path(args.output_file))

    elif args.mode == "split":
        split_video(Path(args.input_file), Path(args.output_dir), args.seconds)

    elif args.mode == "gui" or args.mode is None:
        launch_gui()

    else:
        parser.print_help()


if __name__ == "__main__":

    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print(
        f"{'*'*8}Noini TOOLS{'*'*49}\n"
        "* Please use in own responsibly.                                   *\n"
        f"{'*'*68}"
    )
    main()
