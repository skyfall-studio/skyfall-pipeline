import os
import nuke
import nukescripts
from pathlib import Path

from core.env.pipeline_env import SHOWS_DIR


def _get_context(node):
    """SKYFALL Signature Global 노드에서 컨텍스트 읽기."""
    show = node["show"].value()
    ep   = node["episode"].value()
    seq  = node["sequence"].value()
    shot = node["shot"].value()
    version = node["version"].value()
    notes = node["notes"].value()

    shot_root = SHOWS_DIR / show / ep / seq / shot

    return {
        "show": show,
        "ep": ep,
        "seq": seq,
        "shot": shot,
        "version": version,
        "notes": notes,
        "root": shot_root,
    }


# -----------------------------
# Preview 생성 (h264)
# -----------------------------
def create_preview(node):
    ctx = _get_context(node)
    shot_root = ctx["root"]

    preview_dir = shot_root / "comp" / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    mov_path = preview_dir / f"{ctx['shot']}_{ctx['version']}.mov"

    # Write Node 생성
    write = nuke.createNode("Write")
    write["file"].setValue(str(mov_path))
    write["file_type"].setValue("mov")

    # render
    nukescripts.renderPanel(write)

    nuke.delete(write)
    return mov_path


# -----------------------------
# Render Sequence
# -----------------------------
def create_render(node):
    ctx = _get_context(node)
    shot_root = ctx["root"]

    render_dir = shot_root / "comp" / "render" / ctx["version"]
    render_dir.mkdir(parents=True, exist_ok=True)

    write = nuke.createNode("Write")
    write["file"].setValue(str(render_dir / f"{ctx['shot']}.%04d.exr"))
    write["file_type"].setValue("exr")

    nukescripts.renderPanel(write)

    nuke.delete(write)
    return render_dir


# -----------------------------
# KITSU Publish
# -----------------------------
def publish_to_kitsu(node):
    ctx = _get_context(node)

    # TODO — 다음 단계에서 실제 API 연결
    print("[SKYFALL] Would publish to Kitsu:", ctx)

    return True
