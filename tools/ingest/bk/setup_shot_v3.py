#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline v3.0
setup_shot_v3.py

Episode / Sequence / Shot 생성 + Local Folder + Nuke Template
Kitsu API 구조(setup_shots_v011 기반)에 v3 환경 통합
 - NEW: 기존 Shot description 자동 UPDATE (PUT)
"""

import argparse
import traceback
import requests
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------
# pipeline_env 설정 불러오기
# ---------------------------------------------------------------
PIPELINE_ROOT = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
sys.path.append(PIPELINE_ROOT)

from core.env.pipeline_env import (
    SHOWS_DIR,
    SKYFALL_ROOT,
    get_kitsu_base_url,
    get_kitsu_token,
)

# ---------------------------------------------------------------
# KITSU API HELPERS
# ---------------------------------------------------------------

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


# ---------------------------------------------------------------
# PROJECT / ENTITY-TYPE ID 조회
# ---------------------------------------------------------------

def find_project(show_name):
    data = api_get("/data/projects")
    if not isinstance(data, list):
        raise RuntimeError("/data/projects returned invalid data")

    for p in data:
        if p.get("name") == show_name:
            return p

    raise RuntimeError(f"Project '{show_name}' not found")


def get_entity_type_id(type_name):
    data = api_get("/data/entity-types")
    if not isinstance(data, list):
        raise RuntimeError("/data/entity-types returned invalid data")

    for t in data:
        if t.get("name") == type_name:
            return t["id"]

    raise RuntimeError(f"Entity Type '{type_name}' not found")


# ---------------------------------------------------------------
# CREATE OR UPDATE EPISODE / SEQUENCE / SHOT
# ---------------------------------------------------------------

def get_or_create_episode(project_id, ep_name, ep_type_id):
    existing = api_get(
        f"/data/entities?project_id={project_id}"
        f"&name={ep_name}&entity_type_id={ep_type_id}"
    )
    if isinstance(existing, list) and len(existing) > 0:
        return existing[0]

    return api_post("/data/entities", {
        "name": ep_name,
        "project_id": project_id,
        "entity_type_id": ep_type_id
    })


def get_or_create_sequence(project_id, episode_id, seq_name, seq_type_id):
    existing = api_get(
        f"/data/entities?project_id={project_id}"
        f"&parent_id={episode_id}"
        f"&name={seq_name}&entity_type_id={seq_type_id}"
    )
    if isinstance(existing, list) and len(existing) > 0:
        return existing[0]

    return api_post("/data/entities", {
        "name": seq_name,
        "project_id": project_id,
        "parent_id": episode_id,
        "entity_type_id": seq_type_id
    })


def get_or_create_shot(project_id, sequence_id, shot_name, description, shot_type_id):
    """
    - 기존 샷이 존재하면 description 자동 UPDATE (PUT)
    - 새 샷 생성도 지원
    """

    # 1) GET existing
    existing = api_get(
        f"/data/entities?project_id={project_id}"
        f"&parent_id={sequence_id}"
        f"&name={shot_name}&entity_type_id={shot_type_id}"
    )

    if isinstance(existing, list) and len(existing) > 0:
        shot = existing[0]
        current_desc = shot.get("description") or ""
        new_desc = description or ""

        # UPDATE if changed
        if new_desc and new_desc != current_desc:
            print("🟡 Updating existing shot description…")
            update_payload = {
                "description": new_desc
            }
            updated = api_put(f"/data/entities/{shot['id']}", update_payload)
            return updated

        return shot

    # 2) CREATE new
    payload = {
        "name": shot_name,
        "project_id": project_id,
        "parent_id": sequence_id,
        "entity_type_id": shot_type_id,
        "description": description or ""
    }
    return api_post("/data/entities", payload)


# ---------------------------------------------------------------
# LOCAL FOLDER + NUKE TEMPLATE
# ---------------------------------------------------------------

SHOT_SUBDIRS = [
    "comp/nk",
    "comp/render",
    "comp/preview",
    "plate",
    "prep",
    "roto",
]

def create_shot_folders(show, ep, seq, shot):
    root = SHOWS_DIR / show / ep / seq / shot
    for sub in SHOT_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def create_nuke_template(show, ep, seq, shot, root_path: Path):
    template = SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"
    if not template.exists():
        raise RuntimeError(f"Nuke template missing: {template}")

    dst = root_path / "comp/nk" / f"{show}_{ep}_{seq}_{shot}_comp_v001.nk"
    dst.write_text(template.read_text(), encoding="utf-8")
    return dst


# ---------------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------------

def setup_shot(show, ep, seq, shot, description=""):

    print(f"\n🚀 Setting up Shot: {show}/{ep}/{seq}/{shot}")
    print(f"📝 Description: {description}")

    # PROJECT
    proj = find_project(show)
    project_id = proj["id"]

    # ENTITY TYPES
    episode_type_id  = get_entity_type_id("Episode")
    sequence_type_id = get_entity_type_id("Sequence")
    shot_type_id     = get_entity_type_id("Shot")

    # EPISODE
    print("📌 Episode…")
    ep_obj = get_or_create_episode(project_id, ep, episode_type_id)
    print("   →", ep_obj["id"])

    # SEQUENCE
    print("📌 Sequence…")
    seq_obj = get_or_create_sequence(project_id, ep_obj["id"], seq, sequence_type_id)
    print("   →", seq_obj["id"])

    # SHOT
    print("📌 Shot…")
    shot_obj = get_or_create_shot(project_id, seq_obj["id"], shot, description, shot_type_id)
    print("   →", shot_obj["id"])

    # FOLDERS
    print("\n📁 Creating local folders…")
    root = create_shot_folders(show, ep, seq, shot)
    print("   →", root)

    # TEMPLATE
    print("\n🎬 Creating Nuke template…")
    nk_path = create_nuke_template(show, ep, seq, shot, root)
    print("   →", nk_path)

    print("\n🎉 COMPLETE (SKYFALL v3 ingest + Kitsu entities)")


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", required=True)
    parser.add_argument("--ep", required=True)
    parser.add_argument("--seq", required=True)
    parser.add_argument("--shot", required=True)
    parser.add_argument(
        "--description", "-d",
        type=str,
        default="",
        help="Optional shot description"
    )
    args = parser.parse_args()

    try:
        setup_shot(args.show, args.ep, args.seq, args.shot, args.description)
    except Exception as e:
        print("\n❌ ERROR:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
