#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline v3
setup_shot_v5.py  (v5.1)

- Shot Code 하나로 ingest (EP 있는 형태/없는 형태 자동 판별)
- Episode / Sequence / Shot Kitsu 자동 생성/업데이트 (v3 스타일)
- 로컬 폴더 생성 (plate/prep/roto/comp/nk,render,preview)
- 쇼 템플릿(nuke_template.nk) → 샷 템플릿 comp_v001.nk 자동 복사
"""

import os
import sys
import argparse
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

import requests

# ------------------------------------------------------------------
# PIPELINE ROOT & ENV
# ------------------------------------------------------------------

PIPELINE_ROOT = Path(os.getenv("PIPELINE_ROOT", "/opt/pipeline")).resolve()
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from core.env.pipeline_env import (
    SHOWS_DIR,
    get_kitsu_base_url,
    get_kitsu_headers,
)

# ------------------------------------------------------------------
# HTTP HELPER
# ------------------------------------------------------------------


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{get_kitsu_base_url().rstrip('/')}{path}"
    r = requests.get(url, headers=get_kitsu_headers(), params=params)
    if not r.ok:
        print(f"❌ GET ERROR {path}: {r.status_code} {r.text}")
        return None
    try:
        return r.json()
    except Exception:
        return None


def api_post(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{get_kitsu_base_url().rstrip('/')}{path}"
    r = requests.post(url, headers=get_kitsu_headers(), json=payload)
    if r.status_code not in (200, 201):
        print(f"❌ POST ERROR {path}: {r.status_code} {r.text}")
        return None
    try:
        return r.json()
    except Exception:
        return None


def api_put(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{get_kitsu_base_url().rstrip('/')}{path}"
    r = requests.put(url, headers=get_kitsu_headers(), json=payload)
    if r.status_code not in (200, 201):
        print(f"❌ PUT ERROR {path}: {r.status_code} {r.text}")
        return None
    try:
        return r.json()
    except Exception:
        return None


# ------------------------------------------------------------------
# PROJECT / ENTITY-TYPE
# ------------------------------------------------------------------


def find_project(show_name: str) -> Dict[str, Any]:
    data = api_get("/data/projects")
    if not isinstance(data, list):
        raise RuntimeError("/data/projects returned invalid data")

    for p in data:
        if p.get("name") == show_name:
            return p

    raise RuntimeError(f"Project '{show_name}' not found")


def get_entity_type_id(type_name: str) -> str:
    data = api_get("/data/entity-types")
    if not isinstance(data, list):
        raise RuntimeError("/data/entity-types returned invalid data")

    for t in data:
        if t.get("name") == type_name:
            return t["id"]

    raise RuntimeError(f"EntityType '{type_name}' not found")


# ------------------------------------------------------------------
# ENTITY HELPERS (Episode / Sequence / Shot)
# ------------------------------------------------------------------


def get_or_create_episode(project_id: str, episode_name: str, episode_type_id: str) -> Dict[str, Any]:
    """
    Episode 엔티티 생성 or 조회
    """
    params = {
        "project_id": project_id,
        "name": episode_name,
        "entity_type_id": episode_type_id,
    }
    existing = api_get("/data/entities", params=params)

    if isinstance(existing, list) and existing:
        return existing[0]

    payload = {
        "name": episode_name,
        "project_id": project_id,
        "entity_type_id": episode_type_id,
    }
    created = api_post("/data/entities", payload)
    if not created:
        raise RuntimeError("Episode creation failed")
    return created


def get_or_create_sequence(
    project_id: str,
    episode_id: Optional[str],
    sequence_name: str,
    sequence_type_id: str,
) -> Dict[str, Any]:
    """
    Sequence 엔티티 생성 or 조회
    parent_id = Episode.id (시리즈일 경우)
    """
    params = {
        "project_id": project_id,
        "name": sequence_name,
        "entity_type_id": sequence_type_id,
    }
    if episode_id:
        params["parent_id"] = episode_id

    existing = api_get("/data/entities", params=params)

    if isinstance(existing, list) and existing:
        return existing[0]

    payload = {
        "name": sequence_name,
        "project_id": project_id,
        "entity_type_id": sequence_type_id,
    }
    if episode_id:
        payload["parent_id"] = episode_id

    created = api_post("/data/entities", payload)
    if not created:
        raise RuntimeError("Sequence creation failed")
    return created


def get_or_create_shot(
    project_id: str,
    sequence_id: str,
    shot_name: str,
    description: Optional[str],
    duration: Optional[int],
    shot_type_id: str,
) -> Dict[str, Any]:
    """
    - 기존 샷 있으면: description / nb_frames 업데이트
    - 없으면 새로 생성
    """
    params = {
        "project_id": project_id,
        "parent_id": sequence_id,
        "name": shot_name,
        "entity_type_id": shot_type_id,
    }
    existing = api_get("/data/entities", params=params)

    if isinstance(existing, list) and existing:
        shot = existing[0]
        shot_id = shot["id"]

        update: Dict[str, Any] = {}
        if description and description != (shot.get("description") or ""):
            update["description"] = description
        if duration is not None and duration != shot.get("nb_frames"):
            update["nb_frames"] = duration

        if update:
            print("🟡 Updating existing shot…")
            updated = api_put(f"/data/entities/{shot_id}", update)
            return updated or shot

        return shot

    # 새 생성
    payload: Dict[str, Any] = {
        "name": shot_name,
        "project_id": project_id,
        "entity_type_id": shot_type_id,
        "parent_id": sequence_id,
    }
    if description:
        payload["description"] = description
    if duration is not None:
        payload["nb_frames"] = duration

    created = api_post("/data/entities", payload)
    if not created:
        raise RuntimeError("Shot creation failed")
    return created


# ------------------------------------------------------------------
# SHOT CODE PARSER & PATH
# ------------------------------------------------------------------


def parse_shot_code(code: str):
    """
    형태 C (시리즈):
      EP01_S001_0010 → ep='EP01', seq='S001', shot='0010'
    형태 B (영화):
      S001_0010      → ep=None,   seq='S001', shot='0010'
    """
    parts = code.split("_")
    if code.startswith("EP") and len(parts) == 3:
        ep, seq, shot = parts
        return ep, seq, shot

    if code.startswith("S") and len(parts) == 2:
        seq, shot = parts
        return None, seq, shot

    raise ValueError(f"Invalid SHOT CODE format: {code}")


def get_shot_folder(show: str, ep: Optional[str], seq: str, shot: str) -> Path:
    base = SHOWS_DIR / show
    if ep:
        base = base / ep
    return base / seq / shot


# ------------------------------------------------------------------
# LOCAL FOLDER STRUCTURE
# ------------------------------------------------------------------


def create_shot_folders(shot_root: Path):
    """
    SKYFALL 표준 샷 구조:

    <SHOW>/<EP>/<SEQ>/<SHOT>/
        plate/
        prep/
        roto/
        comp/
            nk/
            render/
            preview/
    """
    subdirs = [
        "plate",
        "prep",
        "roto",
        "comp/nk",
        "comp/render",
        "comp/preview",
    ]
    for s in subdirs:
        (shot_root / s).mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# Nuke Template Copy
# ------------------------------------------------------------------


def create_shot_template(show: str, shot_folder: Path, shot_code: str) -> Path:
    """
    /shows/<SHOW>/config/env/nuke_template.nk → 복사해서
    /shows/<SHOW>/<EP>/SXXX/####/comp/nk/<SHOTCODE>_comp_v001.nk 생성
    """
    show_template = SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"

    comp_dir = shot_folder / "comp" / "nk"
    comp_dir.mkdir(parents=True, exist_ok=True)

    shot_template = comp_dir / f"{shot_code}_comp_v001.nk"

    # 이미 있으면 덮어쓰지 않고 그대로 사용
    if shot_template.exists():
        return shot_template

    if show_template.exists():
        data = show_template.read_text(encoding="utf-8", errors="ignore")
        # 필요한 경우 템플릿 내에 샷 코드 치환
        data = data.replace("{SHOT_CODE}", shot_code)
        shot_template.write_text(data, encoding="utf-8")
    else:
        # 쇼 템플릿이 아예 없으면 간단한 헤더만 있는 스크립트 생성
        shot_template.write_text(
            f"# SKYFALL comp template\n# SHOW={show}, SHOT={shot_code}\n",
            encoding="utf-8",
        )

    return shot_template


# ------------------------------------------------------------------
# MAIN LOGIC
# ------------------------------------------------------------------


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
        print(f"⏱ Duration: {duration}")

    # 1) Shot code 파싱
    ep, seq, shot = parse_shot_code(shot_code)

    # 2) Project & Entity Types
    project = find_project(show)
    project_id = project["id"]

    episode_type_id = get_entity_type_id("Episode")
    sequence_type_id = get_entity_type_id("Sequence")
    shot_type_id = get_entity_type_id("Shot")

    # 3) Episode (optional)
    episode_id: Optional[str] = None
    if ep:
        ep_entity = get_or_create_episode(project_id, ep, episode_type_id)
        episode_id = ep_entity["id"]
        print("📌 Episode →", episode_id)

    # 4) Sequence
    seq_entity = get_or_create_sequence(project_id, episode_id, seq, sequence_type_id)
    sequence_id = seq_entity["id"]
    print("📌 Sequence →", sequence_id)

    # 5) Shot
    shot_entity = get_or_create_shot(
        project_id, sequence_id, shot_code, description, duration, shot_type_id
    )
    shot_id = shot_entity["id"]
    print("📌 Shot →", shot_id)

    # 6) Local Folders
    shot_folder = get_shot_folder(show, ep, seq, shot)
    print(f"\n📁 Creating local folders…\n   → {shot_folder}")
    shot_folder.mkdir(parents=True, exist_ok=True)
    create_shot_folders(shot_folder)

    # 7) Nuke Template
    tmpl = create_shot_template(show, shot_folder, shot_code)
    print(f"\n🎬 Creating Nuke template…\n   → {tmpl}")

    print("\n🎉 COMPLETE (SKYFALL v5 ingest)")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="SKYFALL v3 Shot Ingest (v5.1)")
    parser.add_argument("--show", required=True, help="Show name (e.g. BBH, GEN)")
    parser.add_argument(
        "--shot",
        required=True,
        help="Shot code (EP01_S001_0010 or S001_0010)",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Optional shot description",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Optional duration (nb_frames)",
    )

    args = parser.parse_args()

    try:
        setup_shot(
            args.show,
            args.shot,
            args.description if args.description else None,
            args.duration,
        )
    except Exception as e:
        print("\n❌ ERROR:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
