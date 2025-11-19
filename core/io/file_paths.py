"""
core/io/file_paths.py

- 쇼 템플릿 / 기본 Nuke nk 생성 관련
"""

import os
from pathlib import Path

from core.env.pipeline_env import SHOWS_DIR, get_show, get_ep, get_seq, get_shot


def get_show_template(show_code: str | None = None) -> Path:
    """
    Return path to show-specific template.
    Example:
        /Volumes/skyfall/shows/BBG/config/env/nuke_template.nk
    """
    show = show_code or get_show()
    if not show:
        return Path()
    return SHOWS_DIR / show / "config" / "env" / "nuke_template.nk"


def sanitize_template(path: Path) -> str | None:
    """
    Remove SKYFALL_SIGNATURE_GLOBAL group block
    so template doesn't break when double-clicked.
    """
    if not path.exists():
        return None

    clean_lines: list[str] = []
    skip = False

    with path.open("r", encoding="utf-8") as src:
        for line in src.readlines():
            if "SKYFALL_SIGNATURE_GLOBAL" in line:
                skip = True
            if not skip:
                clean_lines.append(line)
            if skip and "end_group" in line:
                skip = False

    return "".join(clean_lines)


def create_nuke_script(
    show: str | None = None,
    ep: str | None = None,
    seq: str | None = None,
    shot: str | None = None,
    shot_dir: str | Path | None = None,
) -> Path:
    """
    Create a Nuke script from the show template.

    - show/ep/seq/shot 이 None 이면 env(SHOW/EP/SEQ/SHOT)에서 가져옴
    - shot_dir 가 None 이면
      /Volumes/skyfall/shows/<show>/<ep>/<seq>/<shot> 를 기본으로 사용
    """
    show = show or get_show()
    ep = ep or get_ep()
    seq = seq or get_seq()
    shot = shot or get_shot()

    if not all([show, ep, seq, shot]):
        raise RuntimeError("SHOW/EP/SEQ/SHOT must be set (env or arguments).")

    if shot_dir is None:
        shot_dir = (
            SHOWS_DIR / show / ep / seq / shot
        )  # /plate, /comp/... 같은 기본 트리에 맞춤

    shot_dir = Path(shot_dir)
    template_path = get_show_template(show)

    nk_name = f"{show}_{ep}_{seq}_{shot}_comp_v001.nk"
    nk_path = shot_dir / "comp" / "nk" / nk_name

    os.makedirs(nk_path.parent, exist_ok=True)

    print(f"📄 Using template: {template_path}")

    if template_path.exists():
        content = sanitize_template(template_path)
        with nk_path.open("w", encoding="utf-8") as dst:
            dst.write(content or "")
    else:
        print("⚠ Template not found — creating empty comp file")
        nk_path.touch()

    return nk_path
