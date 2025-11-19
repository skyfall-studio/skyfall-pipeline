#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline — setup_shot_v7

UNDER-BAR 규칙 기반 샷 파서:
  * A_B_C  → (EP=A, SEQ=B, SHOT=C)
  * A_B    → (EP=None, SEQ=A, SHOT=B)
  * A      → (EP=None, SEQ=None, SHOT=A)

Kitsu:
  - Episode.name  = EP (있으면)
  - Sequence.name = SEQ (있으면)
  - Shot.name     = SHOT (항상 마지막 파트, 예: 0010)

로컬 폴더:
  /shows/<SHOW>/<EP?>/<SEQ?>/<SHOT>/
  하위에 plate / prep / roto / comp/nk / comp/preview / comp/render

Nuke 템플릿:
  <SHOT_CODE>_comp_v001.nk
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

import requests

# ------------------------------------------------------------
# Pipeline ROOT
# ------------------------------------------------------------
PIPELINE_ROOT = Path(os.getenv("PIPELINE_ROOT", "/opt/pipeline")).resolve()
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from core.env.pipeline_env import SHOWS_DIR, get_kitsu_base_url, get_kitsu_headers

BASE_URL = get_kitsu_base_url().rstrip("/")
HEADERS = get_kitsu_headers()
REQ_TIMEOUT = 5

# Cache: entity type id
_ENTITY_TYPE_CACHE: Dict[str, str] = {}


# ------------------------------------------------------------
# REST API Helpers
# ------------------------------------------------------------
def api_get(path: str, params: Optional[Dict[str, Any]] = None):
    url = BASE_URL + path
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=REQ_TIMEOUT)
        if not r.ok:
            print(f"❌ GET {path} ERROR: {r.status_code} {r.text}")
            return None
        return r.json()
    except Exception as e:
        print(f"❌ GET {path} EXCEPTION: {e}")
        return None


def api_post(path: str, payload: Dict[str, Any]):
    url = BASE_URL + path
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=REQ_TIMEOUT)
        if r.status_code not in (200, 201):
            print(f"❌ POST {path} ERROR: {r.status_code} {r.text}")
            return None
        return r.json()
    except Exception as e:
        print(f"❌ POST {path} EXCEPTION: {e}")
        return None


def api_put(path: str, payload: Dict[str, Any]):
    url = BASE_URL + path
    try:
        r = requests.put(url, headers=HEADERS, json=payload, timeout=REQ_TIMEOUT)
        if r.status_code not in (200, 201):
            print(f"❌ PUT {path} ERROR: {r.status_code} {r.text}")
            return None
        return r.json()
    except Exception as e:
        print(f"❌ PUT {path} EXCEPTION: {e}")
        return None


# ------------------------------------------------------------
# Shot Code Parsing (UNDER-BAR 기준)
# ------------------------------------------------------------
def parse_shot_code(shot_code: str):
    """
    Rules:
        A_B_C  → (EP=A, SEQ=B, SHOT=C)
        A_B    → (EP=None, SEQ=A, SHOT=B)
        A      → (EP=None, SEQ=None, SHOT=A)
    """
    parts = shot_code.split("_")

    if len(parts) == 3:
        return parts[0], parts[1], parts[2]

    if len(parts) == 2:
        return None, parts[0], parts[1]

    if len(parts) == 1:
        return None, None, parts[0]

    raise ValueError(f"Invalid SHOT CODE: {shot_code}")


# ------------------------------------------------------------
# EntityType / Project lookup
# ------------------------------------------------------------
def find_project(show_name: str) -> Dict[str, Any]:
    data = api_get("/data/projects")
    if not isinstance(data, list):
        raise RuntimeError("Invalid /data/projects response")

    for p in data:
        if p.get("name") == show_name:
            return p

    raise RuntimeError(f"Project not found: {show_name}")


def get_entity_type_id(type_name: str) -> str:
    if type_name in _ENTITY_TYPE_CACHE:
        return _ENTITY_TYPE_CACHE[type_name]

    data = api_get("/data/entity-types")
    if not isinstance(data, list):
        raise RuntimeError("Invalid /data/entity-types")

    for t in data:
        if t["name"] == type_name:
            _ENTITY_TYPE_CACHE[type_name] = t["id"]
            return t["id"]

    raise RuntimeError(f"EntityType not found: {type_name}")


# ------------------------------------------------------------
# Entity create / update
# ------------------------------------------------------------
def get_or_create_entity(
    project_id: str,
    type_name: str,
    name: str,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
    nb_frames: Optional[int] = None,
):
    etype_id = get_entity_type_id(type_name)

    params = {
        "project_id": project_id,
        "entity_type_id": etype_id,
        "name": name,
    }
    if parent_id:
        params["parent_id"] = parent_id

    existing = api_get("/data/entities", params=params)
    if isinstance(existing, list) and existing:
        ent = existing[0]
        ent_id = ent["id"]

        update: Dict[str, Any] = {}
        if description is not None and (ent.get("description") or "") != description:
            update["description"] = description
        if nb_frames is not None and ent.get("nb_frames") != nb_frames:
            update["nb_frames"] = nb_frames

        if update:
            print(f"🟡 Updating existing {type_name}: {name}")
            updated = api_put(f"/data/entities/{ent_id}", update)
            return updated or ent

        return ent

    payload: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "project_id": project_id,
        "entity_type_id": etype_id,
        "status": "running",
    }
    if parent_id:
        payload["parent_id"] = parent_id
    if description:
        payload["description"] = description
    if nb_frames is not None:
        payload["nb_frames"] = nb_frames

    created = api_post("/data/entities", payload)
    if not created:
        raise RuntimeError(f"Failed creating {type_name}: {name}")
    return created


# ------------------------------------------------------------
# Local folders
# ------------------------------------------------------------
def get_shot_folder(show: str, ep: Optional[str], seq: Optional[str], shot: str) -> Path:
    """
    로컬 샷 폴더:
      시리즈물: /shows/SHOW/EP/SEQ/SHOT
      영화형:  /shows/SHOW/SEQ/SHOT
      단일:    /shows/SHOW/SHOT
    """
    root = SHOWS_DIR / show
    if ep:
        root = root / ep
    if seq:
        root = root / seq
    return root / shot


def create_shot_folders(shot_root: Path):
    subdirs = [
        "plate",
        "prep",
        "roto",
        "comp/nk",
        "comp/preview",
        "comp/render",
    ]
    for s in subdirs:
        (shot_root / s).mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Nuke template
# ------------------------------------------------------------
def create_nuke_template(show: str, shot_code: str, shot_root: Path) -> Path:
    """
    템플릿:
      /shows/<SHOW>/config/env/nuke_template.nk (있으면)
    아웃풋:
      <shot_code>_comp_v001.nk  (shot_code = 전체, 예: EP03_S001_0010)
    """
    tpl = SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"
    out = shot_root / "comp" / "nk" / f"{shot_code}_comp_v001.nk"
    out.parent.mkdir(parents=True, exist_ok=True)

    if tpl.exists():
        data = tpl.read_text(encoding="utf-8")
        data = data.replace("{SHOT_CODE}", shot_code)
        out.write_text(data, encoding="utf-8")
    else:
        out.write_text(f"# SKYFALL template\n# SHOT_CODE={shot_code}\n", encoding="utf-8")

    return out


# ------------------------------------------------------------
# Main setup
# ------------------------------------------------------------
def setup_shot(
    show: str,
    shot_code: str,
    description: Optional[str] = None,
    duration: Optional[int] = None,
):
    print(f"\n🚀 Setting up SHOT: {show} / {shot_code}")
    if description:
        print(f"📝 Description: {description}")
    if duration is not None:
        print(f"⏱ nb_frames={duration}")

    # UNDER-BAR 기준 파싱
    ep, seq, shot = parse_shot_code(shot_code)

    # 1) Project
    project = find_project(show)
    pid = project["id"]

    # 2) Episode
    episode_id: Optional[str] = None
    if ep:
        ep_ent = get_or_create_entity(pid, "Episode", ep)
        episode_id = ep_ent["id"]
        print("📌 Episode →", episode_id)
    else:
        print("📌 Episode → (none)")

    # 3) Sequence
    sequence_id: Optional[str] = None
    if seq:
        seq_ent = get_or_create_entity(pid, "Sequence", seq, parent_id=episode_id)
        sequence_id = seq_ent["id"]
        print("📌 Sequence →", sequence_id)
    else:
        print("📌 Sequence → (none)")

    # 4) Shot
    #   🔑 여기서 name = shot (마지막 파트, 예: 0010)
    parent_id = sequence_id or episode_id
    shot_ent = get_or_create_entity(
        pid,
        "Shot",
        shot,  # <-- NAME = 마지막 파트
        parent_id=parent_id,
        description=description,
        nb_frames=duration,
    )
    print("📌 Shot →", shot_ent["id"])

    # 5) 로컬 폴더
    shot_root = get_shot_folder(show, ep, seq, shot)
    print("\n📁 Creating local folders…")
    print("   →", shot_root)
    shot_root.mkdir(parents=True, exist_ok=True)
    create_shot_folders(shot_root)

    # 6) Nuke template
    nk = create_nuke_template(show, shot_code, shot_root)
    print("\n🎬 Creating Nuke template…")
    print("   →", nk)

    print("\n🎉 COMPLETE (SKYFALL v7 ingest)")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SKYFALL Shot Setup v7")
    parser.add_argument("--show", required=True, help="Show name (e.g. GEN, BBF)")
    parser.add_argument(
        "--shot",
        required=True,
        help="Shot code (EP03_S001_0010 / S001_0010 / 0010 등)",
    )
    parser.add_argument("--description", default="", help="Optional description")
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Optional nb_frames (duration)",
    )

    args = parser.parse_args()
    desc = args.description if args.description else None
    setup_shot(args.show, args.shot, desc, args.duration)
