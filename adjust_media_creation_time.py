# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

def adjust_media_creation_time(input_dir: Path):
    """
    フォルダ内の動画ファイルの creation_time を
    ファイル名順に並ぶように調整
    """
    # 対象動画
    files = [f for f in input_dir.iterdir() if f.suffix.lower() in [".mp4", ".mov", ".mts"]]
    files = sorted(files, key=lambda f: f.name.lower())

    print(f"処理対象ファイル: {len(files)} 件")

    # 基準日時（現在日時）から 1 秒ずつずらして設定
    base_time = datetime.now()
    
    for i, f in enumerate(files):
        new_time = base_time + timedelta(seconds=i)
        new_time_str = new_time.strftime("%Y-%m-%dT%H:%M:%S")  # ffmpeg 用の ISO 形式

        # ffmpeg で creation_time を上書き
        output_file = f.parent / f"{f.stem}_tmp{f.suffix}"
        cmd = [
            "ffmpeg", "-y", "-i", str(f),
            "-c", "copy",
            "-map", "0",
            "-metadata", f"creation_time={new_time_str}",
            str(output_file)
        ]
        subprocess.run(cmd, check=True)
        # 元ファイルを置き換え
        f.unlink()
        output_file.rename(f)
        print(f"{f.name} -> {new_time_str}")

    print("メディア作成日時の調整が完了しました。")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python adjust_media_creation_time.py /path/to/folder")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print("指定されたフォルダが存在しません")
        sys.exit(1)

    adjust_media_creation_time(folder)