#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL – Shot Setup (v011, self-contained)

- Kitsu(Zou)에 Episode / Sequence / Shot 생성
- 로컬 디렉토리 트리 생성
- 쇼별 Nuke 템플릿(.nk) 복사해서 샷용 스크립트 생성
- ⚠️ Task 생성은 하지 않음 (Kitsu 웹 UI에서 수동 생성)

사용 예:
python3 setup_shots_v011.py \
  --show BBG --ep EP03 --seq S001 --shot 0010 --description "plate test"
"""

import os
import sys
import json
import argparse
from pathlib import Path

import requests


# ---------------------------
# 환경 설정
# ---------------------------

# 쇼 루트 (환경변수 없으면 기본값 사용)
SHOWS_ROOT = os.environ.get("SKYFALL_SHOWS", "/Volumes/skyfall/shows")

# Kitsu / Zou URL (이미 쓰고 있던 IP)
KITSU_URL = os.environ.get("KITSU_URL", "http://10.10.10.150:5000")

# 토큰 캐시 파일 (이미 사용 중인 위치)
TOKEN_CACHE_FILE = "/Volumes/skyfall/opt/pipeline/config/token_cache.json"


# ---------------------------
# 공통 HTTP 유틸
# ---------------------------

def load_token() -> str:
    """token_cache.json 에서 access_token 읽기"""
    try:
        with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("access_token")
        if not token:
            raise RuntimeError("access_token 이 token_cache.json 에 없습니다.")
        return token
    except FileNotFoundError:
        raise RuntimeError(f"토큰 캐시 파일을 찾을 수 없습니다: {TOKEN_CACHE_FILE}")


def get_headers() -> dict:
    """Authorization 헤더 구성"""
    token = load_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def api_get(path: str) -> requests.Response:
    url = f"{KITSU_URL}{path}"
    resp = requests.get(url, headers=get_headers())
    resp.raise_for_status()
    return resp


def api_post(path: str, payload: dict) -> requests.Response:
    url = f"{KITSU_URL}{path}"
    resp = requests.post(url, headers=get_headers(), json=payload)
    resp.raise_for_status()
    return resp


# ---------------------------
# KITSU 엔티티 유틸
# ---------------------------

def find_project(show_code: str) -> dict:
    """
    /data/projects 에서 name == show_code 인 프로젝트 찾기
    """
    resp = api_get("/data/projects")
    projects = resp.json()
    for p in projects:
        if p.get("name") == show_code:
            return p
    raise RuntimeError(f"Project '{show_code}' 를 /data/projects 에서 찾을 수 없습니다.")


def get_entity_type_id(name: str) -> str:
    """
    /data/entity-types 에서 name 으로 ID 찾기
    (Episode, Sequence, Shot 등)
    """
    resp = api_get("/data/entity-types")
    types = resp.json()
    for t in types:
        if t.get("name") == name:
            return t["id"]
    raise RuntimeError(f"EntityType '{name}' 을 /data/entity-types 에서 찾을 수 없습니다.")


def create_episode(project_id: str, name: str, episode_type_id: str) -> dict:
    payload = {
        "name": name,
        "project_id": project_id,
        "entity_type_id": episode_type_id,
    }
    resp = api_post("/data/entities", payload)
    return resp.json()


def create_sequence(project_id: str, episode_id: str, name: str, sequence_type_id: str) -> dict:
    payload = {
        "name": name,
        "project_id": project_id,
        "parent_id": episode_id,        # Episode 아래에 Sequence 달기
        "entity_type_id": sequence_type_id,
    }
    resp = api_post("/data/entities", payload)
    return resp.json()


def create_shot(project_id: str, sequence_id: str, name: str, description: str, shot_type_id: str) -> dict:
    """
    Shot 엔티티 생성 (Task 는 만들지 않음)
    description 은 data 필드에 넣어서 보관
    """
    payload = {
        "name": name,
        "project_id": project_id,
        "parent_id": sequence_id,       # Sequence 아래에 Shot 달기
        "entity_type_id": shot_type_id,
        "data": {
            "description": description or "",
        },
    }
    resp = api_post("/data/entities", payload)
    return resp.json()


# ---------------------------
# 로컬 디렉토리 / Nuke 템플릿
# ---------------------------

def create_shot_directory_tree(show: str, ep: str, seq: str, shot: str) -> Path:
    """
    /<SHOWS_ROOT>/<show>/<ep>/<seq>/<shot> 및 하위 폴더 생성
    예: /Volumes/skyfall/shows/BBG/EP03/S001/0010/...
    """
    shot_root = Path(SHOWS_ROOT) / show / ep / seq / shot

    subdirs = [
        "comp/nk",
        "comp/preview",
        "comp/render",
        "plate",
        "prep",
        "roto",
    ]

    for sub in subdirs:
        path = shot_root / sub
        path.mkdir(parents=True, exist_ok=True)

    return shot_root


def create_nuke_script(show: str, ep: str, seq: str, shot: str, shot_root: Path) -> Path:
    """
    쇼별 템플릿:
      /Volumes/skyfall/shows/<show>/config/env/nuke_template.nk

    샷 스크립트:
      <shot_root>/comp/nk/<show>_<ep>_<seq>_<shot>_comp_v001.nk
    """
    import shutil

    template_path = Path(SHOWS_ROOT) / show / "config" / "env" / "nuke_template.nk"
    if not template_path.exists():
        raise FileNotFoundError(f"Nuke 템플릿을 찾을 수 없습니다: {template_path}")

    nk_dir = shot_root / "comp" / "nk"
    nk_dir.mkdir(parents=True, exist_ok=True)

    nk_name = f"{show}_{ep}_{seq}_{shot}_comp_v001.nk"
    nk_path = nk_dir / nk_name

    shutil.copy2(template_path, nk_path)
    return nk_path


# ---------------------------
# CLI / 메인 로직
# ---------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SKYFALL Shot Setup (no tasks, self-contained)")
    parser.add_argument("--show", required=True, help="Show code (예: BBG)")
    parser.add_argument("--ep", required=True, help="Episode code (예: EP01)")
    parser.add_argument("--seq", required=True, help="Sequence code (예: S001)")
    parser.add_argument("--shot", required=True, help="Shot code (예: 0010)")
    parser.add_argument("--description", default="", help="Shot description (그대로 저장)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"\n▶ Setting up: {args.show}/{args.ep}/{args.seq}/{args.shot}")
    if args.description:
        print(f"   📝 Description: {args.description}")

    # 1) 프로젝트 찾기
    try:
        project = find_project(args.show)
    except Exception as e:
        print(f"❌ Project '{args.show}' not found or error: {e}")
        sys.exit(1)

    project_id = project["id"]
    print(f"   🎯 Project found: {project_id}")

    # 2) EntityType ID 조회
    try:
        episode_type_id = get_entity_type_id("Episode")
        sequence_type_id = get_entity_type_id("Sequence")
        shot_type_id = get_entity_type_id("Shot")
    except Exception as e:
        print(f"❌ EntityType 조회 실패: {e}")
        sys.exit(1)

    # 3) Episode / Sequence / Shot 생성
    print("\n🔧 Creating Kitsu entities...")

    try:
        episode = create_episode(project_id, args.ep, episode_type_id)
        print(f"   📌 Episode:  {episode['id']}")
    except Exception as e:
        print(f"❌ Episode 생성 실패: {e}")
        sys.exit(1)

    try:
        sequence = create_sequence(project_id, episode["id"], args.seq, sequence_type_id)
        print(f"   📌 Sequence: {sequence['id']}")
    except Exception as e:
        print(f"❌ Sequence 생성 실패: {e}")
        sys.exit(1)

    try:
        shot = create_shot(project_id, sequence["id"], args.shot, args.description, shot_type_id)
        print(f"   📌 Shot:     {shot['id']}")
    except Exception as e:
        print(f"❌ Shot 생성 실패: {e}")
        sys.exit(1)

    # 4) 로컬 디렉토리 및 Nuke 템플릿 생성
    print("\n📁 Creating directories / Nuke script...")

    try:
        shot_root = create_shot_directory_tree(args.show, args.ep, args.seq, args.shot)
        print(f"   📁 Shot dir: {shot_root}")
    except Exception as e:
        print(f"❌ 디렉토리 생성 실패: {e}")
        sys.exit(1)

    try:
        nk_path = create_nuke_script(args.show, args.ep, args.seq, args.shot, shot_root)
        print(f"   📜 Nuke script: {nk_path}")
        print("   📎 Plate loader는 템플릿 내부 plate_loader 로직으로 자동 연결됩니다.")
    except Exception as e:
        print(f"❌ Nuke 스크립트 생성 실패: {e}")
        sys.exit(1)

    print("\n⚠️ Tasks 는 자동 생성하지 않습니다. Kitsu 웹에서 수동으로 Task 를 추가하세요.")
    print("\n🎉 Done! (v011)\n")


if __name__ == "__main__":
    main()
