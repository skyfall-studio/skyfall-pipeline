#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
from pathlib import Path
import sys

from lib.pipeline_env import SKYFALL_ROOT


def detect_render_sequence(show, ep, seq, shot):
    render_dir = Path(SKYFALL_ROOT) / "shows" / show / ep / seq / shot / "comp" / "render"
    pattern = re.compile(rf"{ep}_{seq}_{shot}_comp_beauty_v(\d+)_\d{{4}}\.exr")

    versions = set()
    for f in render_dir.glob("*.exr"):
        m = pattern.match(f.name)
        if m:
            versions.add(int(m.group(1)))

    if not versions:
        return None, None

    latest_version = f"v{max(versions):03d}"
    first_frame = 1001  # change if needed
    return latest_version, render_dir


def generate_preview(show, ep, seq, shot, lut_path, fps=24):
    version, render_dir = detect_render_sequence(show, ep, seq, shot)
    if not version:
        print("❌ No render EXR sequence found")
        return

    exr_pattern = f"{ep}_{seq}_{shot}_comp_beauty_{version}_%04d.exr"
    seq_path = render_dir / exr_pattern

    preview_dir = Path(SKYFALL_ROOT) / "shows" / show / ep / seq / shot / "comp" / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    output_path = preview_dir / f"{ep}_{seq}_{shot}_comp_{version}.mov"

    burn_show = show
    burn_code = f"{ep}_{seq}_{shot}"
    burn_info_left = f"{burn_show}  {burn_code}  {version}"
    frame_range = "1001-1263"  # optional, auto-detect next version
    burn_info_right = f"{fps}fps   F:{frame_range}"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-r", str(fps),
        "-start_number", "1001",
        "-i", str(seq_path),
        "-vf",
        f"lut3d='{lut_path}',"
        f"drawtext=text='{burn_info_left}': fontcolor=white: x=40: y=40: fontsize=34: box=1: boxcolor=0x00000080,"
        f"drawtext=text='{burn_info_right}': fontcolor=white: x=w-tw-40: y=40: fontsize=34: box=1: boxcolor=0x00000080,"
        f"drawtext=text='Frame:%{{eif\\:t+1001\\:d}}': fontcolor=white: x=(w-text_w)/2: y=h-80: fontsize=36: box=1: boxcolor=0x00000080",
        "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
        str(output_path)
    ]

    print("🎬 Rendering Preview...")
    print(" ".join(ffmpeg_cmd))
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"🎉 Preview Done → {output_path}")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: preview_v008_final.py SHOW EP SEQ SHOT LUT_PATH")
        sys.exit(1)

    show, ep, seq, shot, lut = sys.argv[1:6]
    generate_preview(show, ep, seq, shot, lut)
