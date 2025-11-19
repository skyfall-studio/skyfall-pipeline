import nuke
from apps.nuke.scripts.context import get_shot_root

def run():
    try:
        shot_root = get_shot_root()
    except Exception as e:
        nuke.message(f"Create Comp Template Error:\n{e}")
        return

    template_path = "/Users/pd/skyfall-dev/pipeline/apps/nuke/templates/skyfall_comp_default.nk"

    try:
        nuke.scriptReadFile(template_path)
    except Exception as e:
        nuke.message(f"Template load error:\n{e}")
