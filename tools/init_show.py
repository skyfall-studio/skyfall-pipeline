#!/usr/bin/env python3
"""
SKYFALL Pipeline v3.0
Show Initialization Script (init_show.py)

Creates full show structure under SKYFALL_ROOT/shows/<SHOW>
and deploys Nuke template + publish gizmo.
"""

import os
import shutil
from pathlib import Path

from core.env.pipeline_env import SKYFALL_ROOT, PIPELINE_ROOT


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

SHOWS_DIR = SKYFALL_ROOT / "shows"

NUKE_TEMPLATE_SRC = PIPELINE_ROOT / "templates" / "nuke" / "skyfall_signature_global.nk"
PUBLISH_GIZMO_SRC = PIPELINE_ROOT / "templates" / "nuke" / "skyfall_publish_panel.gizmo"

PROJECT_STRUCTURE = [
    "assets/char",
    "assets/env",
    "assets/prop",
    "assets/tex",
    "assets/lookdev",
    "plates/ingest_log",
    "editorial/offline",
    "editorial/conform",
    "editorial/reference",
    "editorial/timeline",
    "dailies",
    "deliveries/season_master",
    "exchange/inbound",
    "exchange/outbound",
    "exchange/archive",
    "exchange/nda",
    "config/env",
    "config/ocio",
    "config/luts"
]


# ------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------

def create_directories(root: Path) -> None:
    for folder in PROJECT_STRUCTURE:
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created: {path}")


def copy_templates(show_root: Path) -> None:
    env_dir = show_root / "config" / "env"
    env_dir.mkdir(parents=True, exist_ok=True)

    nuke_dest = env_dir / "nuke_template.nk"
    gizmo_dest = env_dir / "skyfall_publish_panel.gizmo"

    # Copy template NK
    if NUKE_TEMPLATE_SRC.exists():
        shutil.copyfile(NUKE_TEMPLATE_SRC, nuke_dest)
        print(f"🎬 Copied Nuke template → {nuke_dest}")
    else:
        print(f"⚠️ Nuke template NOT FOUND: {NUKE_TEMPLATE_SRC}")

    # Copy publish gizmo
    if PUBLISH_GIZMO_SRC.exists():
        shutil.copyfile(PUBLISH_GIZMO_SRC, gizmo_dest)
        print(f"🧩 Copied Publish gizmo → {gizmo_dest}")
    else:
        print(f"⚠️ Publish gizmo NOT FOUND: {PUBLISH_GIZMO_SRC}")


def create_project_yaml(show_root: Path, show: str):
    meta_path = show_root / "project.yml"

    if meta_path.exists():
        print(f"ℹ️ project.yml already exists: {meta_path}")
        return

    content = f"""show: {show}
fps: 23.976
resolution: 1920x1080
colorspace: ACEScg

ocio_config: {show_root}/config/ocio/config.ocio
grain_profile: film_stock_A
delivery_format: EXR16
preview_format: mov_h264
"""
    meta_path.write_text(content, encoding="utf-8")
    print(f"📝 Created metadata: {meta_path}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def init_show(show: str):
    show_root = SHOWS_DIR / show
    show_root.mkdir(parents=True, exist_ok=True)

    print(f"\n🚀 Initializing SKYFALL SHOW: {show}\nPath: {show_root}\n")

    create_directories(show_root)
    create_project_yaml(show_root, show)
    copy_templates(show_root)

    print("\n🎉 COMPLETE — SKYFALL Show Setup Ready.\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize SKYFALL Show Structure (v3.0)")
    parser.add_argument("--show", required=True, help="Show code (e.g. BBF)")
    args = parser.parse_args()

    init_show(args.show)
