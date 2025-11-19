import os
import re
import nuke
from apps.nuke.scripts.context import parse_from_script_path

# ----------------------------------------------------
# 시퀀스 탐색 (subfolder 포함)
# ----------------------------------------------------
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

    if not frames:
        return None

    frames.sort()
    return {
        "folder": folder_path,
        "prefix": prefix,
        "ext": ext,
        "first": frames[0],
        "last": frames[-1],
    }


# ----------------------------------------------------
# MOV 메타데이터 기반 정확한 FPS/총프레임 계산
# ----------------------------------------------------
def detect_mov_range(read):
    """
    MOV 길이치 측정 로직 (정확도 높은 순서):

    1) input/framecount  (가장 정확함)
    2) input/timecode + input/framerate 조합
    3) duration(sec) × fps
    4) metadata가 없으면 기본값 (24fps, length=1)
    """

    read["reload"].execute()  # metadata refresh

    # 1) framecount 메타데이터
    fc = read.metadata("input/framecount")
    fps = read.metadata("input/framerate")
    if fps is None:
        fps = read.metadata("input/frame_rate")

    if fps is None:
        fps = 24

    if fc:
        return float(fps), int(fc)

    # 2) timecode 기반 길이 계산 (예: "00:03:26:02")
    tc = read.metadata("input/timecode")
    if tc:
        try:
            hh, mm, ss, ff = [int(x) for x in tc.split(":")]
            total_frames = int(hh * 3600 * fps + mm * 60 * fps + ss * fps + ff)
            return float(fps), total_frames
        except:
            pass

    # 3) duration(sec) 기반
    dur = read.metadata("input/duration")
    if dur:
        try:
            return float(fps), int(float(dur) * float(fps))
        except:
            pass

    # 4) fallback
    return float(fps), 1


# ----------------------------------------------------
# Colorspace Auto Detect
# ----------------------------------------------------
def detect_colorspace(fname):
    lname = fname.lower()
    if lname.endswith(".exr"):
        return "ACES - ACEScg"
    if lname.endswith(".dpx"):
        return "Cineon"
    return "default"


# ----------------------------------------------------
# Popup
# ----------------------------------------------------
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


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
def run():
    try:
        show, ep, seq, shot, root = parse_from_script_path()
        plate_dir = root + "/plate"

        if not os.path.exists(plate_dir):
            nuke.message(f"Plate folder not found:\n{plate_dir}")
            return

        # EP vs Non-EP naming rule
        shot_pattern = f"{ep}_{seq}_{shot}" if ep.startswith("EP") else f"{seq}_{shot}"

        seq_candidates = []
        mov_candidates = []

        # ─────────────────────────────────
        # 1) top-level 직접 검색
        # ─────────────────────────────────
        top_seq = find_sequence(plate_dir, shot_pattern)
        if top_seq:
            seq_candidates.append(top_seq)

        # ─────────────────────────────────
        # 2) 모든 subfolder 검사
        # ─────────────────────────────────
        for entry in os.listdir(plate_dir):
            sub = os.path.join(plate_dir, entry)
            if os.path.isdir(sub):
                info = find_sequence(sub, shot_pattern)
                if info:
                    seq_candidates.append(info)

        # ─────────────────────────────────
        # 3) MOV 검색
        # ─────────────────────────────────
        for rootdir, dirs, files in os.walk(plate_dir):
            for f in files:
                if f.startswith(shot_pattern) and f.lower().endswith(".mov"):
                    mov_candidates.append(os.path.join(rootdir, f))

        selected = None
        selected_type = None

        # ─────────────────────────────────
        # 시퀀스 우선
        # ─────────────────────────────────
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

        # ─────────────────────────────────
        # READ Node 생성
        # ─────────────────────────────────
        if selected_type == "seq":
            folder = selected["folder"]
            prefix = selected["prefix"]
            ext = selected["ext"]
            first = selected["first"]
            last = selected["last"]

            read = nuke.createNode("Read")
            read["file"].setValue(f"{folder}/{prefix}.%04d{ext}")
            read["first"].setValue(first)
            read["last"].setValue(last)
            read["colorspace"].setValue(detect_colorspace(prefix+ext))

            # 이름 자동
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

        # ─────────────────────────────────
        # MOV 처리
        # ─────────────────────────────────
        movfile = selected
        read = nuke.createNode("Read")
        read["file"].setValue(movfile)
        read.setName("Read_Plate_mov")
        read["colorspace"].setValue("default")
        read.autoplace()

        fps, frames = detect_mov_range(read)

        read["first"].setValue(1)
        read["last"].setValue(frames)
        read["fps"].setValue(fps)

        nuke.message(f"Plate Loaded (MOV):\n{movfile}\nFPS: {fps}\nFrames: {frames}")

    except Exception as e:
        nuke.message(f"Plate Loader Error:\n{e}")
