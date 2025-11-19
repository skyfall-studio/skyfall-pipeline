#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline — setup_shot_v6
--------------------------------
- EP_S_SSSS 형태 자동 파싱
- Episode / Sequence 자동 생성 (Kitsu API)
- Shot 생성 + description 업데이트
- 기존 샷 재생성 시 description overwrite
- Local folder structure 생성
- Nuke template 생성
- Duration(frame length)은 무시 (필드 없음)

Author: SKYFALL
Version: v6
"""

import os
import sys
import uuid
import json
from pathlib import Path
import requests
from datetime import datetime

# ------------------------------------------------------------
# Load Pipeline ENV
# ------------------------------------------------------------
PIPELINE_ROOT = Path(os.getenv("PIPELINE_ROOT", "/opt/pipeline")).resolve()
sys.path.append(str(PIPELINE_ROOT))

from core.env.pipeline_env import (
    SKYFALL_ROOT,
    SHOWS_DIR,
    get_kitsu_base_url,
    get_kitsu_headers
)

# Request settings
REQ_TIMEOUT = 4
BASE_URL = get_kitsu_base_url()


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------
def log(msg):
    print(msg)


def parse_shot_code(shot_code: str):
    """
    EP04_S003_0010 → ("EP04", "S003", "0010")
    형태 B (영화): 0010 → ("", "", "0010")
    """
    parts = shot_code.split("_")

    if len(parts) == 3:
        return parts[0], parts[1], parts[2]

    if len(parts) == 1:
        return "", "", parts[0]

    raise ValueError(f"Invalid SHOT CODE format: {shot_code}")


# ------------------------------------------------------------
# Kitsu basic calls
# ------------------------------------------------------------
def kitsu_get(url):
    try:
        r = requests.get(BASE_URL + url, headers=get_kitsu_headers(), timeout=REQ_TIMEOUT)
        if r.status_code != 200:
            log(f"❌ GET ERROR {url}: {r.text}")
            return None
        return r.json()
    except Exception as e:
        log(f"❌ GET EXCEPTION {url}: {e}")
        return None


def kitsu_post(url, payload):
    try:
        r = requests.post(BASE_URL + url, headers=get_kitsu_headers(), json=payload, timeout=REQ_TIMEOUT)
        if r.status_code not in (200, 201):
            log(f"❌ POST ERROR: {r.text}")
            return None
        return r.json()
    except Exception as e:
        log(f"❌ POST EXCEPTION: {e}")
        return None


def kitsu_put(url, payload):
    try:
        r = requests.put(BASE_URL + url, headers=get_kitsu_headers(), json=payload, timeout=REQ_TIMEOUT)
        if r.status_code not in (200, 201):
            log(f"❌ PUT ERROR {url}: {r.text}")
            return None
        return r.json()
    except Exception as e:
        log(f"❌ PUT EXCEPTION {url}: {e}")
        return None


# ------------------------------------------------------------
# Kitsu wrapper functions
# ------------------------------------------------------------
def find_project_id(show: str):
    data = kitsu_get("/data/projects")
    if not data:
        return None

    for p in data:
        if p["name"] == show:
            return p["id"]
    return None


def find_or_create_episode(project_id: str, ep: str):
    if not ep:
        return None

    data = kitsu_get("/data/episodes")
    if data:
        for e in data:
            if e["name"] == ep and e["project_id"] == project_id:
                return e["id"]

    payload = {
        "id": str(uuid.uuid4()),
        "name": ep,
        "project_id": project_id,
        "description": "",
    }
    out = kitsu_post("/data/episodes", payload)
    return out["id"] if out else None


def find_or_create_sequence(project_id: str, ep_id: str, seq: str):
    if not seq:
        return None

    data = kitsu_get("/data/sequences")
    if data:
        for s in data:
            if s["name"] == seq and s["project_id"] == project_id:
                return s["id"]

    payload = {
        "id": str(uuid.uuid4()),
        "name": seq,
        "project_id": project_id,
        "episode_id": ep_id,
        "description": "",
    }
    out = kitsu_post("/data/sequences", payload)
    return out["id"] if out else None


def find_shot(project_id: str, seq_id: str, shot: str):
    data = kitsu_get("/data/shots")
    if not data:
        return None

    for s in data:
        if s["name"] == shot and s["project_id"] == project_id:
            return s
    return None


def create_shot(project_id: str, seq_id: str, shot: str, description: str):
    payload = {
        "id": str(uuid.uuid4()),
        "name": shot,
        "project_id": project_id,
        "sequence_id": seq_id,
        "description": description,
        "status": "running",
    }
    return kitsu_post("/data/shots", payload)


def update_shot_desc(shot_id, description):
    payload = {"description": description}
    return kitsu_put(f"/data/entities/{shot_id}", payload)


# ------------------------------------------------------------
# Local folder creation
# ------------------------------------------------------------
def create_local_folders(show, ep, seq, shot):
    shot_root = SHOWS_DIR / show / ep / seq / shot
    folders = [
        shot_root / "plate",
        shot_root / "prep",
        shot_root / "roto",
        shot_root / "comp" / "nk",
        shot_root / "comp" / "preview",
        shot_root / "comp" / "render",
    ]

    for f in folders:
        f.mkdir(parents=True, exist_ok=True)

    return shot_root


# ------------------------------------------------------------
# Nuke template creation
# ------------------------------------------------------------
def create_nuke_script(show, ep, seq, shot, shot_root):
    show_template = SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"
    out_path = shot_root / "comp" / "nk" / f"{ep}_{seq}_{shot}_comp_v001.nk"

    if show_template.exists():
        txt = show_template.read_text()
        Path(out_path).write_text(txt)
    else:
        Path(out_path).write_text(f"# Empty template\n# {show} {ep} {seq} {shot}")

    return out_path


# ------------------------------------------------------------
# Main setup flow
# ------------------------------------------------------------
def setup_shot(show, shot_code, description, duration):
    ep, seq, shot = parse_shot_code(shot_code)

    print(f"\n🚀 Setting up SHOT: {show} / {shot_code}")
    print(f"📝 Description: {description}")

    if duration:
        print("⏱ DURATION detected but ignored (no frame fields in Kitsu)")

    # Find project
    project_id = find_project_id(show)
    if not project_id:
        print("❌ PROJECT NOT FOUND")
        return

    # Episode
    ep_id = find_or_create_episode(project_id, ep)
    print(f"📌 Episode → {ep_id}")

    # Sequence
    seq_id = find_or_create_sequence(project_id, ep_id, seq)
    print(f"📌 Sequence → {seq_id}")

    # Shot
    existing = find_shot(project_id, seq_id, shot)
    if existing:
        print(f"📌 Shot exists → {existing['id']}")
        update_shot_desc(existing["id"], description)
        shot_id = existing["id"]
    else:
        new_shot = create_shot(project_id, seq_id, shot, description)
        if not new_shot:
            print("❌ FAILED creating shot")
            return
        shot_id = new_shot["id"]
        print(f"📌 Shot → {shot_id}")

    # Local folders
    shot_root = create_local_folders(show, ep, seq, shot)
    print(f"\n📁 Creating local folders…")
    print(f"   → {shot_root}")

    # Nuke template
    out_nk = create_nuke_script(show, ep, seq, shot, shot_root)
    print(f"\n🎬 Creating Nuke template…")
    print(f"   → {out_nk}")

    print("\n🎉 COMPLETE (SKYFALL v6 ingest)")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--show", required=True)
    parser.add_argument("--shot", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--duration", default=None)

    args = parser.parse_args()

    setup_shot(
        args.show,
        args.shot,
        args.description,
        args.duration
    )
