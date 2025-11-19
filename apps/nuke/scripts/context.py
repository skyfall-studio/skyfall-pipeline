import os
import nuke

# ----------------------------------------------------
# 경로 파싱
# ----------------------------------------------------
def parse_from_script_path():
    script_path = nuke.root().name()

    if script_path == "Root":
        raise RuntimeError("스크립트가 아직 저장되지 않았습니다.\nFile → Save As 후 실행하세요.")

    parts = script_path.split("/")

    # 최소 경로 구조 검사
    # .../SHOW/EP/SEQ/SHOT/comp/nk/file.nk → 최소 8개
    if len(parts) < 8:
        raise RuntimeError(f"경로 구조가 잘못되었습니다:\n{script_path}")

    show = parts[-8]
    ep   = parts[-7]
    seq  = parts[-6]
    shot = parts[-5]

    # comp/nk 제거한 샷 루트 /Volumes/.../SHOW/EP/SEQ/SHOT
    shot_root = "/".join(parts[:-3])

    return show, ep, seq, shot, shot_root


# ----------------------------------------------------
# Shot Root
# ----------------------------------------------------
def get_shot_root():
    _, _, _, _, root = parse_from_script_path()
    return root


# ----------------------------------------------------
# Plate Path (fix: shows 중복 제거)
# ----------------------------------------------------
def get_plate_path():
    show, ep, seq, shot, root = parse_from_script_path()

    plate_dir = f"{root}/plate"   # <-- 이게 정답

    if not os.path.exists(plate_dir):
        raise RuntimeError(f"Plate folder not found:\n{plate_dir}")

    # 이미지 검색
    for f in os.listdir(plate_dir):
        if f.lower().endswith((".exr", ".dpx", ".jpg", ".png")):
            return f"{plate_dir}/{f}"

    raise RuntimeError(f"Plate folder exists but no valid image found:\n{plate_dir}")


# ----------------------------------------------------
# Kitsu URL (기존 유지)
# ----------------------------------------------------
def get_kitsu_shot_url():
    show, ep, seq, shot, _ = parse_from_script_path()
    return f"http://10.10.10.150:5000/project/{show}/shots/{ep}-{seq}-{shot}"
