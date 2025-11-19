# ============================================================
# SKYFALL Plate Loader - ffprobe Bundled Version (FINAL)
# pipeline layout:
# /Users/pd/skyfall-dev/pipeline/tools/ffprobe
# /Users/pd/skyfall-dev/pipeline/apps/nuke/scripts/plate_loader.py
# ============================================================

import os
import re
import json
import subprocess
import platform
import nuke
from apps.nuke.scripts.context import parse_from_script_path


# ------------------------------------------------------------
# ffprobe 경로 자동 선택 (SKYFALL 전용)
# ------------------------------------------------------------
def get_ffprobe_path():
    """
    SKYFALL ffprobe 번들 자동 선택
    plate_loader.py → apps/nuke/scripts
    => ../../../tools/ffprobe
    """

    root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )

    base = os.path.join(root, "tools", "ffprobe")
    sysname = platform.system().lower()

    if "darwin" in sysname:     # macOS
        return os.path.join(base, "mac", "ffprobe")
    elif "linux" in sysname:
        return os.path.join(base, "linux", "ffprobe")
    elif "windows" in sysname:
        return os.path.join(base, "win", "ffprobe.exe")
    else:
        return "ffprobe"


# ------------------------------------------------------------
# ffprobe 기반 MOV FPS + 총프레임 계산
# ------------------------------------------------------------
def probe_mov_frames(filepath):
    ffprobe = get_ffprobe_path()

    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-count_frames",
        "-show_entries", "stream=nb_read_frames,r_frame_rate",
        "-of", "json",
        filepath
    ]

    try:
        out = subprocess.check_output(cmd).decode("utf-8")
        data = json.loads(out)

        stream = data["streams"][0]

        total_frames = int(stream["nb_read_frames"])
        fps_str = stream["r_frame_rate"]

        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        return fps, total_frames

    except Exception as e:
        nuke.tprint(f"[SKYFALL][ffprobe error] {e}")
        return 24.0, 1


# ------------------------------------------------------------
# 시퀀스 탐색
# ------------------------------------------------------------
def find_sequence(folder_path, shot_pattern):
    if not os.path.exists(folder_path):
        return None

    files = os.listdir(folder_path)

    seq_files = [
        f for f in files
        if f.startswith(shot_pattern) and re.search(r"\.\d+\.", f)
    ]

    if not seq_files:
        return None

    sample = seq_files[0]
    m = re.match(r"(.+?)\.(\d+)(\.[^.]+)$", sample)
    if not m:
        return None

    prefix, frame, ext = m.groups()

    frames = []
    for f in seq_files:
        mm = re.match(rf"{re.escape(prefix)}\.(\d+){re.escape(ext)}", f)
        if mm:
            frames.append(int(mm.group(1)))

    frames.sort()
    return {
        "folder": folder_path,
        "prefix": prefix,
        "ext": ext,
        "first": frames[0],
        "last": frames[-1],
    }


# ------------------------------------------------------------
# Colorspace 자동 감지
# ------------------------------------------------------------
def detect_colorspace(fname):
    lname = fname.lower()
    if lname.endswith(".exr"):
        return "ACES - ACEScg"
    if lname.endswith(".dpx"):
        return "Cineon"
    return "default"


# ------------------------------------------------------------
# Popup
# ------------------------------------------------------------
def popup_select(title, options):
    msg = title + "\n\n"
    for i, opt in enumerate(options):
        msg += f"{i+1}. {opt}\n"

    ret = nuke.getInput(msg, "1")
    try:
        idx = int(ret) - 1
        return options[idx]
    except:
        return None


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def run():
    try:
        show, ep, seq, shot, rootdir = parse_from_script_path()
        plate_dir = rootdir + "/plate"

        if not os.path.exists(plate_dir):
            nuke.message(f"Plate folder not found:\n{plate_dir}")
            return

        shot_pattern = f"{ep}_{seq}_{shot}" if ep.startswith("EP") else f"{seq}_{shot}"

        seq_candidates = []
        mov_candidates = []

        # 시퀀스 top-level
        top_seq = find_sequence(plate_dir, shot_pattern)
        if top_seq:
            seq_candidates.append(top_seq)

        # 시퀀스 subfolders
        for entry in os.listdir(plate_dir):
            sub = os.path.join(plate_dir, entry)
            if os.path.isdir(sub):
                info = find_sequence(sub, shot_pattern)
                if info:
                    seq_candidates.append(info)

        # MOV 탐색
        for rootdir, dirs, files in os.walk(plate_dir):
            for f in files:
                if f.startswith(shot_pattern) and f.lower().endswith(".mov"):
                    mov_candidates.append(os.path.join(rootdir, f))

        selected = None
        selected_type = None

        # 시퀀스 우선
        if seq_candidates:

            def ver_priority(c):
                folder = os.path.basename(c["folder"])
                if "_plate_v" in folder: return 0
                if "_org_v" in folder: return 1
                return 2

            seq_candidates.sort(key=ver_priority)

            if len(seq_candidates) > 1:
                vlist = [os.path.basename(c["folder"]) for c in seq_candidates]
                choice = popup_select("Select Plate Version", vlist)
                if choice:
                    for c in seq_candidates:
                        if os.path.basename(c["folder"]) == choice:
                            selected = c
                            selected_type = "seq"
                            break

            if not selected:
                selected = seq_candidates[0]
                selected_type = "seq"

        elif mov_candidates:
            mov_candidates.sort()
            selected = mov_candidates[0]
            selected_type = "mov"

        else:
            nuke.message("No plate sequence or mov found.")
            return

        # 시퀀스 로딩
        if selected_type == "seq":
            folder = selected["folder"]
            prefix = selected["prefix"]
            ext   = selected["ext"]
            first = selected["first"]
            last  = selected["last"]

            read = nuke.createNode("Read")
            read["file"].setValue(f"{folder}/{prefix}.%04d{ext}")
            read["first"].setValue(first)
            read["last"].setValue(last)
            read["colorspace"].setValue(detect_colorspace(prefix + ext))

            if "_plate_v" in prefix:
                ver = re.search(r"plate_v(\d+)", prefix).group(1)
                read.setName(f"Read_Plate_v{ver}")
            elif "_org_v" in prefix:
                ver = re.search(r"org_v(\d+)", prefix).group(1)
                read.setName(f"Read_Org_v{ver}")
            else:
                read.setName("Read_Plate")

            read.autoplace()
            nuke.message(f"Plate Loaded:\n{folder}/{prefix}.xxxx{ext}")
            return

        # MOV 로딩 (ffprobe)
        movfile = selected

        read = nuke.createNode("Read")
        read["file"].setValue(movfile)
        read.setName("Read_Plate_mov")
        read["colorspace"].setValue("default")
        read.autoplace()

        fps, frames = probe_mov_frames(movfile)

        read["first"].setValue(1)
        read["last"].setValue(frames)

        root = nuke.root()
        root["fps"].setValue(fps)
        root["first_frame"].setValue(1)
        root["last_frame"].setValue(frames)

        nuke.message(
            f"Plate Loaded (MOV):\n{movfile}\nFPS: {fps}\nFrames: {frames}"
        )

    except Exception as e:
        nuke.message(f"Plate Loader Error:\n{e}")
