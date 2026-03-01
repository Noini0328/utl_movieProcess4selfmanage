# -*- coding: utf-8 -*-

import subprocess
import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import flet as ft

# =========================
# frozen 対応（EXE対策）
# =========================
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

TARGET_WIDTH, TARGET_HEIGHT = 1280, 720


# =========================
# 共通関数
# =========================

def get_video_duration(file: Path) -> float:
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
    
def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False

def get_media_creation_time(file: Path) -> float:
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
    return file.stat().st_mtime


# =========================
# 動画変換
# =========================

def convert_video(infile: Path, outfile: Path):

    vf_filter = (
        f"scale='min({TARGET_WIDTH}/iw,{TARGET_HEIGHT}/ih)*iw':"
        f"'min({TARGET_WIDTH}/iw,{TARGET_HEIGHT}/ih)*ih',"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        "fps=30,format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y", "-i", str(infile),
        "-vf", vf_filter,
        "-af", "dynaudnorm",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2",
        str(outfile)
    ]

    subprocess.run(cmd, check=True)


# =========================
# 結合
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
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_file)
    ]

    subprocess.run(cmd, check=True)

    print("結合完了:", output_file)


# =========================
# 分割
# =========================

def split_video(input_file: Path, output_dir: Path, seconds: int):

    output_dir.mkdir(exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(seconds),
        "-f", "segment",
        "-reset_timestamps", "1",
        str(output_dir / f"{input_file.stem}_%03d.mp4")
    ]

    subprocess.run(cmd, check=True)

    print("分割完了:", output_dir)


# =========================
# クレジット追加
# =========================
def add_credit(input_file, text_file, align, color, fontsize, output_file):
    """
    input_file : 入力動画
    text_file  : クレジットテキストファイル（改行ごとに1行）
    align      : left, center, right
    color      : #RRGGBB
    fontsize   : int
    output_file: 出力動画
    """
    fontsize = int(fontsize)  

    # ファイル存在チェック
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"入力ファイルがありません: {input_file}")
    if not os.path.isfile(text_file):
        raise FileNotFoundError(f"テキストファイルがありません: {text_file}")
    if align not in ("left", "center", "right"):
        raise ValueError("alignはleft, center, rightのいずれかです")

    # 動画情報取得
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", "-select_streams", "v:0", input_file],
        capture_output=True, text=True, check=True
    )
    import json
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    video_width = int(info["streams"][0]["width"])
    video_height = int(info["streams"][0]["height"])

    # クレジット行読み込み
    with open(text_file, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") if line.strip() else " " for line in f]

    line_height  = int(fontsize * 1.5)
    total_text_h = len(lines) * line_height

    # スクロール範囲：開始3秒～終了3秒前
    scroll_start = 3.0
    scroll_end   = duration - 3.0
    scroll_dur   = scroll_end - scroll_start
    scroll_dist  = video_height + total_text_h
    speed        = scroll_dist / scroll_dur  # px/sec

    # 色変換
    ffmpeg_color = "0x" + color.lstrip("#").upper()

    # x座標
    if align == "left":
        x_expr = "50"
    elif align == "right":
        x_expr = "w-tw-50"
    else:
        x_expr = "(w-tw)/2"

    # enable 式
    enable_expr = f"gte(t\\,{scroll_start})*lte(t\\,{scroll_end})"

    # drawtext フィルタ作成
    filters = []
    for i, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace(",", "\\,")
        y_offset = i * line_height
        y_expr = f"h-{speed:.4f}*(t-{scroll_start})+{y_offset}"
        filters.append(
            f"drawtext=text='{escaped}':fontsize={fontsize}:fontcolor={ffmpeg_color}:x={x_expr}:y={y_expr}:enable='{enable_expr}'"
        )

    vf = ",".join(filters)

    # 実行
    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf", vf,
        "-codec:a", "copy",
        output_file
    ]

    print(f"Running ffmpeg... Lines: {len(lines)}, Speed: {speed:.2f}px/s")
    subprocess.run(cmd, check=True)
    print(f"Done! Output: {output_file}")





# =========================
# GUI
# =========================

def launch_gui():



    def main(page: ft.Page):

        ffmpeg_ok = check_ffmpeg()

        if ffmpeg_ok:
            ffmpeg_status = ft.Text(
                "✅ ffmpeg が利用可能です（PATH OK）",
                color=ft.Colors.GREEN,
                weight="bold"
            )
        else:
            ffmpeg_status = ft.Text(
                "❌ ffmpeg が見つかりません。インストール＆PATH設定を確認してください。",
                color=ft.Colors.RED,
                weight="bold"
            )

        page.title = "動画処理ツール"
        page.window_width = 950
        page.window_height = 750
        page.theme_mode = ft.ThemeMode.LIGHT

        def toggle_theme(e):
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
                page.theme = ft.Theme(
                    color_scheme=ft.ColorScheme(
                        primary=ft.Colors.GREEN,
                        background=ft.Colors.BLACK,
                        on_background=ft.Colors.GREEN,
                        surface=ft.Colors.BLACK,
                        on_surface=ft.Colors.GREEN,
                    )
                )
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
                page.theme = ft.Theme()
            page.update()

        theme_switch = ft.Switch(label="ダークモード", on_change=toggle_theme)

        def select_file(field, save=False, folder=False):
            root = tk.Tk()
            root.withdraw()
            if folder:
                path = filedialog.askdirectory()
            elif save:
                path = filedialog.asksaveasfilename(defaultextension=".mp4")
            else:
                path = filedialog.askopenfilename()
            if path:
                field.value = path
                field.border_color = ft.Colors.GREEN
                page.update()

        # ===== 結合 =====
        concat_in = ft.TextField(label="入力フォルダ", expand=True)
        concat_out = ft.TextField(label="出力ファイル", expand=True)

        concat_btn = ft.ElevatedButton("結合実行",
            on_click=lambda e: concat_videos(
                Path(concat_in.value), Path(concat_out.value))
        )

        concat_ui = ft.Column([
            ft.Row([concat_in,
                ft.ElevatedButton("参照",
                    on_click=lambda e: select_file(concat_in, folder=True))]),
            ft.Row([concat_out,
                ft.ElevatedButton("保存先",
                    on_click=lambda e: select_file(concat_out, save=True))]),
            concat_btn
        ])

        # ===== 分割 =====
        split_in = ft.TextField(label="入力動画", expand=True)
        split_out = ft.TextField(label="出力フォルダ", expand=True)
        split_sec = ft.TextField(label="秒数", value="10")

        split_btn = ft.ElevatedButton("分割実行",
            on_click=lambda e: split_video(
                Path(split_in.value),
                Path(split_out.value),
                int(split_sec.value))
        )

        split_ui = ft.Column([
            ft.Row([split_in,
                ft.ElevatedButton("参照",
                    on_click=lambda e: select_file(split_in))]),
            ft.Row([split_out,
                ft.ElevatedButton("参照",
                    on_click=lambda e: select_file(split_out, folder=True))]),
            split_sec,
            split_btn
        ])

        # ===== クレジット =====
        credit_in = ft.TextField(label="入力動画", expand=True)
        credit_txt = ft.TextField(label="テキストファイル", expand=True)
        credit_out = ft.TextField(label="出力動画", expand=True)
        align = ft.Dropdown(label="位置", value="center",
            options=[ft.dropdown.Option("left"),
                     ft.dropdown.Option("center"),
                     ft.dropdown.Option("right")])
        color = ft.TextField(label="カラーコード", value="#FFFFFF")
        size = ft.TextField(label="フォントサイズ", value="36")

        credit_btn = ft.ElevatedButton("クレジット追加",
            on_click=lambda e: add_credit(
                credit_in.value,
                credit_txt.value,
                align.value,
                color.value,
                size.value,
                credit_out.value)
        )

        credit_ui = ft.Column([
            ft.Row([credit_in,
                ft.ElevatedButton("参照",
                    on_click=lambda e: select_file(credit_in))]),
            ft.Row([credit_txt,
                ft.ElevatedButton("参照",
                    on_click=lambda e: select_file(credit_txt))]),
            ft.Row([credit_out,
                ft.ElevatedButton("保存先",
                    on_click=lambda e: select_file(credit_out, save=True))]),
            align, color, size,
            credit_btn
        ])


        page.add(
            ft.Column([
                ft.Row([
                    ft.Text("🎬 動画処理ツール", size=26),
                    theme_switch
                    ]),
                ffmpeg_status,  # ← ここに追加
                ft.Divider()
            ]),
            ft.Tabs(tabs=[
                ft.Tab(text="結合", content=concat_ui),
                ft.Tab(text="分割", content=split_ui),
                ft.Tab(text="クレジット", content=credit_ui),
            ])
        )

    ft.app(target=main)


# =========================
# メイン
# =========================

if __name__ == "__main__":
    launch_gui()