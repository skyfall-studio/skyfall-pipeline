"""
apps/nuke/remap.py

- path_map.json 을 이용해서 경로 변환
- v3 사양에 맞게 /opt/pipeline/config/path_map.json 참고
"""

import json
from pathlib import Path

import nuke

from core.env.pipeline_env import PATHMAP_FILE


def _load_pathmap() -> dict:
    if not PATHMAP_FILE.exists():
        nuke.message(f"path_map.json not found:\n{PATHMAP_FILE}")
        return {}

    with PATHMAP_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _remap_path(path: str, mode: str, mapping: dict) -> str:
    """
    mode: "to_native" | "to_project"
    mapping 예시 (config/path_map.json):

    {
      "to_native": {
        "/Volumes/skyfall": "X:/"
      },
      "to_project": {
        "X:/": "/Volumes/skyfall"
      }
    }
    """
    table = mapping.get(mode, {})
    for src, dst in table.items():
        if path.startswith(src):
            return path.replace(src, dst, 1)
    return path


def _remap_selected_reads(mode: str):
    mapping = _load_pathmap()
    if not mapping:
        return

    nodes = [n for n in nuke.selectedNodes() if n.Class() == "Read"]
    if not nodes:
        nuke.message("No Read nodes selected.")
        return

    for node in nodes:
        old = node["file"].value()
        new = _remap_path(old, mode, mapping)
        if old != new:
            node["file"].setValue(new)
            print(f"[SKYFALL PATHMAP] {old}  ->  {new}")

    nuke.message(f"Path Remap → {mode} complete.")


def to_native():
    _remap_selected_reads("to_native")


def to_project():
    _remap_selected_reads("to_project")
