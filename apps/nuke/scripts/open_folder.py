import nuke
import subprocess
from apps.nuke.scripts.context import get_shot_root

def open_shot_folder():
    try:
        root = get_shot_root()
    except Exception as e:
        nuke.message(f"Open Folder Error:\n{e}")
        return

    subprocess.Popen(["open", root])
