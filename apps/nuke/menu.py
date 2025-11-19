import nuke
import os
import sys


# 안전 import ─ 실패해도 메뉴는 표시되게
def _safe_imports():
    try:
        from apps.nuke.scripts import (
            create_comp_template,
            plate_loader,
            auto_version,
            open_folder,
            open_kitsu,
            auto_create_global,
        )
        return {
            "create_comp_template": create_comp_template,
            "plate_loader": plate_loader,
            "auto_version": auto_version,
            "open_folder": open_folder,
            "open_kitsu": open_kitsu,
            "auto_create_global": auto_create_global,
        }
    except Exception as e:
        nuke.tprint("[SKYFALL] Import error:", e)
        return {}


modules = _safe_imports()


def build_menu():
    nuke.tprint("[SKYFALL] build_menu() START")

    main_menu = nuke.menu("Nuke")
    sky_menu = main_menu.addMenu("SKYFALL")
    nuke.tprint("[SKYFALL] SKYFALL menu created =", sky_menu)

    # Create Comp Template
    if modules.get("create_comp_template"):
        sky_menu.addCommand(
            "Create Comp Template",
            "import apps.nuke.scripts.create_comp_template as s; s.run()",
        )

    # Load Plate
    if modules.get("plate_loader"):
        sky_menu.addCommand(
            "Load Plate",
            "import apps.nuke.scripts.plate_loader as s; s.run()",
        )

    # Save New Version
    if modules.get("auto_version"):
        sky_menu.addCommand(
            "Save New Version",
            "import apps.nuke.scripts.auto_version as s; s.save_new_version()",
        )

    # Open Shot Folder
    if modules.get("open_folder"):
        sky_menu.addCommand(
            "Open Shot Folder",
            "import apps.nuke.scripts.open_folder as s; s.open_shot_folder()",
        )

    # Open in Kitsu
    if modules.get("open_kitsu"):
        sky_menu.addCommand(
            "Open in Kitsu",
            "import apps.nuke.scripts.open_kitsu as s; s.open_shot_in_kitsu()",
        )

    nuke.tprint("[SKYFALL] Menu loaded via menu.py")


# 메뉴는 init.py에서 로드
nuke.tprint("[SKYFALL] menu.py imported (build_menu not auto-called)")

