# /Users/pd/skyfall-dev/pipeline/apps/nuke/scripts/plate_loader.py

import nuke
import os
import re
from glob import glob

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _get_show_ep_seq_shot():
    """현재 Nuke 스크립트 경로에서 show/ep/seq/shot 추출."""
    script = nuke.root().name()
    if not script or script == "Root":
        raise RuntimeError("Save the script first before loading plate.")

    parts = script.split("/")
    # .../shows/BBI/EP01/S001/0010/comp/nk/{file}.nk
    try:
        show = parts[-6]
        ep   = parts[-5]
        seq  = parts[-4]
        shot = parts[-3]
    except:
        raise RuntimeError("Script path is not within SKYFALL show folder.")

    return show, ep, seq, shot


def _get_plate_dir(show, ep, seq, shot):
    """플레이트 폴더 경로 구성."""
    base = f"/Volumes/skyfall/shows/{show}/{ep}/{seq}/{shot}/plate"
    if not os.path.isdir(base):
        raise RuntimeError(f"Plate folder not found:\n{base}")
    return base


def _find_sequences(directory):
    """
    디렉토리 내에서 시퀀스 (같은 prefix.####.ext) 찾기.
    subfolder 구조도 지원.
    """
    sequences = []

    # 1) 플레이트 루트에서 직접 검색
    exr_list = glob(os.path.join(directory, "*.exr"))
    dpx_list = glob(os.path.join(directory, "*.dpx"))

    if exr_list or dpx_list:
        sequences.append(directory)

    # 2) subfolder 검색 (EP01_S001_0010_v001/EP01_S001_0010_v001.####.exr)
    for root, dirs, files in os.walk(directory):
        exrs = [f for f in files if f.lower().endswith(".exr")]
        dpxs = [f for f in files if f.lower().endswith(".dpx")]
        if exrs or dpxs:
            sequences.append(root)

    # 경로 정렬
    sequences = sorted(list(set(sequences)))
    return sequences


def _detect_sequence_range(seq_dir):
    """
    시퀀스 디렉토리에서 first/last 범위 계산.
    """
    files = sorted(
        f for f in os.listdir(seq_dir)
        if re.search(r"\.(\d+)\.(exr|dpx)$", f.lower())
    )

    if not files:
        raise RuntimeError(f"No valid sequence files in:\n{seq_dir}")

    # 프레임 번호 추출
    frames = []
    for f in files:
        m = re.search(r"\.(\d+)\.(exr|dpx)$", f.lower())
        if m:
            frames.append(int(m.group(1)))

    if not frames:
        raise RuntimeError(f"Failed to parse frame numbers:\n{seq_dir}")

    return min(frames), max(frames)


# ------------------------------------------------------------
# MOV metadata FPS/Frame 계산
# ------------------------------------------------------------
def detect_mov_range(read):
    """
    MOV 길이 계산 (정확도 순)
    1) input/framecount
    2) timecode + fps
    3) duration × fps
    """

    read["reload"].execute()

    fps = (
        read.metadata("input/frame_rate")
        or read.metadata("input/framerate")
        or read.metadata("input/frame_rate_num")
        or 24.0
    )
    fps = float(fps)

    # framecount 최우선
    fc = read.metadata("input/framecount")
    if fc:
        return fps, int(fc)

    # timecode 기반
    tc = read.metadata("input/timecode")
    if tc:
        try:
            hh, mm, ss, ff = [int(x) for x in tc.split(":")]
            total = int(hh * 3600 * fps + mm * 60 * fps + ss * fps + ff)
            return fps, total
        except:
            pass

    # duration 기반
    dur = read.metadata("input/duration")
    if dur:
        try:
            total = int(float(dur) * fps)
            return fps, total
        except:
            pass

    return fps, 1


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def run():
    """
    SKYFALL Plate Loader 엔트리 포인트.
    """

    try:
        show, ep, seq, shot = _get_show_ep_seq_shot()
    except Exception as e:
        nuke.message(f"Plate Loader Error:\n{e}")
        return

    try:
        plate_dir = _get_plate_dir(show, ep, seq, shot)
    except Exception as e:
        nuke.message(f"Plate Loader Error:\n{e}")
        return

    # --------------------------------------------------------
    # 1) 먼저 시퀀스 있는지 확인 (우선 적용)
    # --------------------------------------------------------
    seq_dirs = _find_sequences(plate_dir)

    if seq_dirs:
        # 여러 개라면 선택 팝업
        if len(seq_dirs) > 1:
            sel = nuke.choice("Select Plate Version",
                              "Multiple plate sequences found.\nSelect one:",
                              seq_dirs)
            seq_dir = seq_dirs[sel]
        else:
            seq_dir = seq_dirs[0]

        try:
            first, last = _detect_sequence_range(seq_dir)
        except Exception as e:
            nuke.message(f"Plate Loader Error:\n{e}")
            return

        # prefix 찾기
        sample = sorted(os.listdir(seq_dir))[0]
        prefix = sample.split(".")[0]
        ext = sample.split(".")[-1]

        read = nuke.createNode("Read")
        read.setName("Read_Plate")
        read["file"].setValue(f"{seq_dir}/{prefix}.%04d.{ext}")
        read["first"].setValue(first)
        read["last"].setValue(last)
        read["colorspace"].setValue("default")
        read.autoplace()

        nuke.message(
            f"Plate Loaded (Sequence):\n{seq_dir}\nFrames: {first}-{last}"
        )
        return

    # --------------------------------------------------------
    # 2) 시퀀스 없으면 MOV 검사
    # --------------------------------------------------------
    movs = glob(os.path.join(plate_dir, "*.mov"))
    if not movs:
        nuke.message(f"Plate Loader Error:\nNo sequence or MOV found:\n{plate_dir}")
        return

    # MOV 여러 개면 선택
    movfile = movs[0]
    if len(movs) > 1:
        sel = nuke.choice("Select MOV",
                          "Multiple MOV files found.\nSelect one:",
                          movs)
        movfile = movs[sel]

    read = nuke.createNode("Read")
    read.setName("Read_Plate")
    read["file"].setValue(movfile)
    read["colorspace"].setValue("default")
    read.autoplace()

    fps, frames = detect_mov_range(read)

    # Read 노드 frame_rate knob 또는 root fps fallback
    if "frame_rate" in read.knobs():
        read["frame_rate"].setValue(fps)
    else:
        nuke.root()["fps"].setValue(fps)

    read["first"].setValue(1)
    read["last"].setValue(frames)

    nuke.message(
        f"Plate Loaded (MOV):\n{movfile}\nFPS: {fps}\nFrames: {frames}"
    )
