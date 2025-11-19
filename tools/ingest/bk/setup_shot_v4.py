#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline v3.0 — setup_shot_v004 (FINAL)

지원 형태:
  B) S001_0010           → 영화형(EP 없음)
  C) EP01_S001_0010      → 에피소드 시리즈형

기능:
 - Episode / Sequence / Shot 생성
 - Episode 없는 영화 프로젝트 자동 처리
 - description 업데이트 (PUT)
 - 로컬 폴더 생성
 - SHOW prefix 제거된 Nuke 템플릿 생성
 - entity_type_id 기반 Kitsu API 완전 호환
"""

import argparse
import traceback
import requests
import sys
import os
from pathlib import Path

# ---------------------------------------------------
# pipeline_env
# ---------------------------------------------------
PIPELINE_ROOT = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
sys.path.append(PIPELINE_ROOT)

from core.env.pipeline_env import (
    SHOWS_DIR,
    SKYFALL_ROOT,
    get_kitsu_base_url,
    get_kitsu_token,
)

# ---------------------------------------------------
# API WRAPPERS
# ---------------------------------------------------
def kitsu_headers():
    return {
        "Authorization": f"Bearer {get_kitsu_token()}",
        "Content-Type": "application/json"
    }

def api_get(path):
    url = f"{get_kitsu_base_url()}{path}"
    r = requests.get(url, headers=kitsu_headers())
    try:
        return r.json()
    except:
        return None

def api_post(path, payload):
    url = f"{get_kitsu_base_url()}{path}"
    r = requests.post(url, json=payload, headers=kitsu_headers())
    if r.status_code not in (200, 201):
        print(f"❌ POST ERROR {path}: {r.text}")
    return r.json()

def api_put(path, payload):
    url = f"{get_kitsu_base_url()}{path}"
    r = requests.put(url, json=payload, headers=kitsu_headers())
    if r.status_code not in (200, 201):
        print(f"❌ PUT ERROR {path}: {r.text}")
    return r.json()


# ---------------------------------------------------
# PROJECT + ENTITY TYPE ID
# ---------------------------------------------------
def find_project(show_name):
    data = api_get("/data/projects")
    for p in data:
        if p.get("name") == show_name:
            return p
    raise RuntimeError(f"Project '{show_name}' not found")

def get_entity_type_id(type_name):
    data = api_get("/data/entity-types")
    for t in data:
        if t.get("name") == type_name:
            return t["id"]
    raise RuntimeError(f"Entity Type '{type_name}' not found")


# ---------------------------------------------------
# SHOT CODE PARSER  (형태 B, C 지원)
# ---------------------------------------------------

def parse_shot_code(code):
    """
    형태 C: EP01_S001_0010
    형태 B: S001_0010

    반환값: (ep, seq, shot_number)
    ep=None 이면 영화형
    """

    parts = code.split("_")

    # 형태 C
    if code.startswith("EP") and len(parts) == 3:
        ep = parts[0]         # EP01
        seq = parts[1]        # S001
        shot_number = parts[2]
        return ep, seq, shot_number

    # 형태 B
    if code.startswith("S") and len(parts) == 2:
        ep = None
        seq = parts[0]        # S001
        shot_number = parts[1]
        return ep, seq, shot_number

    raise ValueError(f"Invalid SHOT CODE format: {code}")


# ---------------------------------------------------
# CREATE OR UPDATE ENTITIES
# ---------------------------------------------------
def get_or_create_episode(project_id, ep, episode_type_id):
    if ep is None:
        return None

    existing = api_get(
        f"/data/entities?project_id={project_id}"
        f"&name={ep}&entity_type_id={episode_type_id}"
    )
    if isinstance(existing, list) and len(existing) > 0:
        return existing[0]

    return api_post("/data/entities", {
        "name": ep,
        "project_id": project_id,
        "entity_type_id": episode_type_id
    })


def get_or_create_sequence(project_id, parent_id, seq, sequence_type_id):
    query = f"/data/entities?project_id={project_id}&name={seq}&entity_type_id={sequence_type_id}"

    if parent_id:
        query += f"&parent_id={parent_id}"

    existing = api_get(query)
    if isinstance(existing, list) and len(existing) > 0:
        return existing[0]

    payload = {
        "name": seq,
        "project_id": project_id,
        "entity_type_id": sequence_type_id
    }
    if parent_id:
        payload["parent_id"] = parent_id

    return api_post("/data/entities", payload)


def get_or_create_shot(project_id, seq_id, shot_name, description, shot_type_id):
    existing = api_get(
        f"/data/entities?project_id={project_id}"
        f"&parent_id={seq_id}"
        f"&name={shot_name}&entity_type_id={shot_type_id}"
    )

    # UPDATE
    if isinstance(existing, list) and len(existing) > 0:
        shot = existing[0]
        if description and description != (shot.get("description") or ""):
            print("🟡 Updating existing description…")
            return api_put(f"/data/entities/{shot['id']}", {"description": description})
        return shot

    # CREATE
    payload = {
        "name": shot_name,
        "project_id": project_id,
        "parent_id": seq_id,
        "entity_type_id": shot_type_id,
        "description": description or ""
    }
    return api_post("/data/entities", payload)


# ---------------------------------------------------
# LOCAL FOLDERS + Nuke Template
# ---------------------------------------------------
SHOT_SUBDIRS = [
    "comp/nk",
    "comp/render",
    "comp/preview",
    "plate",
    "prep",
    "roto",
]

def create_shot_folders(show, ep, seq, shot_number):
    if ep:
        root = SHOWS_DIR / show / ep / seq / shot_number
    else:
        root = SHOWS_DIR / show / seq / shot_number

    for sub in SHOT_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)

    return root


def create_nuke_template(show, ep, seq, shot_number, root_path):
    template = SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"
    if not template.exists():
        raise RuntimeError(f"Nuke template missing: {template}")

    if ep:
        nk_name = f"{ep}_{seq}_{shot_number}_comp_v001.nk"
    else:
        nk_name = f"{seq}_{shot_number}_comp_v001.nk"

    dst = root_path / "comp/nk" / nk_name
    dst.write_text(template.read_text(), encoding="utf-8")
    return dst


# ---------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------
def setup_shot(show, shot_code, description=""):

    print(f"\n🚀 Setting up SHOT: {show} / {shot_code}")
    print(f"📝 Description: {description}")

    # ① 샷 코드 파싱 (형태 B / C)
    ep, seq, shot_number = parse_shot_code(shot_code)

    # ② Kitsu shot name
    if ep:
        kit_shot_name = f"{ep}_{seq}_{shot_number}"
    else:
        kit_shot_name = f"{seq}_{shot_number}"

    # ③ Project
    proj = find_project(show)
    project_id = proj["id"]

    # ④ entity types
    episode_type_id  = get_entity_type_id("Episode")
    sequence_type_id = get_entity_type_id("Sequence")
    shot_type_id     = get_entity_type_id("Shot")

    # ⑤ Episode (영화형은 skip)
    if ep:
        print("📌 Episode…")
        ep_obj = get_or_create_episode(project_id, ep, episode_type_id)
        print("   →", ep_obj["id"])
        parent_for_seq = ep_obj["id"]
    else:
        print("📌 No Episode (Movie mode)")
        parent_for_seq = None

    # ⑥ Sequence
    print("📌 Sequence…")
    seq_obj = get_or_create_sequence(project_id, parent_for_seq, seq, sequence_type_id)
    print("   →", seq_obj["id"])

    # ⑦ Shot
    print("📌 Shot…")
    shot_obj = get_or_create_shot(project_id, seq_obj["id"], kit_shot_name, description, shot_type_id)
    print("   →", shot_obj["id"])

    # ⑧ Local folders
    print("\n📁 Creating local folders…")
    root = create_shot_folders(show, ep, seq, shot_number)
    print("   →", root)

    # ⑨ Nuke template
    print("\n🎬 Creating Nuke template…")
    nk = create_nuke_template(show, ep, seq, shot_number, root)
    print("   →", nk)

    print("\n🎉 COMPLETE (SKYFALL v004 ingest)")


# ---------------------------------------------------
# CLI
# ---------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", required=True)
    parser.add_argument("--shot", required=True, help="SHOT CODE (S001_0010 or EP01_S001_0010)")
    parser.add_argument("--description", "-d", default="")
    args = parser.parse_args()

    try:
        setup_shot(args.show, args.shot, args.description)
    except Exception as e:
        print("\n❌ ERROR:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
