"""
services/kitsu_api.py

Kitsu REST API 래퍼
- BASE_URL, TOKEN 은 core.env.pipeline_env 에서 가져옴
- 토큰 파일 의존성 제거 (env-only)
"""

from typing import Dict, Any, List, Optional

import requests

from core.env.pipeline_env import get_kitsu_base_url, get_kitsu_headers


BASE_URL = get_kitsu_base_url().rstrip("/")  # e.g. http://10.10.10.150:5000
API_BASE = f"{BASE_URL}/data"


# ---------------------------------------------------------------------------
# HTTP HELPERS
# ---------------------------------------------------------------------------

def _get(path: str):
    r = requests.get(API_BASE + path, headers=get_kitsu_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def _post(path: str, payload: Dict[str, Any]):
    r = requests.post(API_BASE + path, headers=get_kitsu_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# PROJECT
# ---------------------------------------------------------------------------

def find_project(show_code: str) -> Optional[Dict[str, Any]]:
    """
    프로젝트 이름(show code)으로 프로젝트 검색
    """
    for p in _get("/projects"):
        if p["name"] == show_code:
            return p
    return None


# ---------------------------------------------------------------------------
# LOOKUP
# ---------------------------------------------------------------------------

def get_entity_type_id(name: str) -> str:
    for e in _get("/entity-types"):
        if e["name"] == name:
            return e["id"]
    raise ValueError(f"EntityType '{name}' not found")


# task types 캐시
_TASK_TYPES_RAW: List[Dict[str, Any]] = _get("/task-types")
TASK_TYPES: dict[str, str] = {t["name"]: t["id"] for t in _TASK_TYPES_RAW}


# ---------------------------------------------------------------------------
# EPISODE / SEQUENCE / SHOT 생성
# ---------------------------------------------------------------------------

def create_episode(project_id: str, name: str):
    payload = {
        "name": name,
        "entity_type_id": get_entity_type_id("Episode"),
        "project_id": project_id,
    }
    return _post("/entities", payload)


def create_sequence(project_id: str, parent_id: str, name: str):
    payload = {
        "name": name,
        "entity_type_id": get_entity_type_id("Sequence"),
        "project_id": project_id,
        "parent_id": parent_id,
    }
    return _post("/entities", payload)


def create_shot_with_tasks(
    sequence_id: str,
    name: str,
    description: str,
    task_type_ids: list[str],
):
    """
    1) Shot 생성
    2) 연결된 Task 들 생성
    """
    shot_payload = {
        "type": "Shot",
        "name": name,
        "description": description,
        "parent_id": sequence_id,
    }

    shot = _post("/entities", shot_payload)
    shot_id = shot["id"]

    for task_type_id in task_type_ids:
        task_payload = {
            "entity_id": shot_id,
            "task_type_id": task_type_id,
            "status": "not_started",
        }
        _post("/task-items", task_payload)

    return shot
