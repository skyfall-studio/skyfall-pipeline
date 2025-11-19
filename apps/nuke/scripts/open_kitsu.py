import webbrowser
import nuke
from apps.nuke.scripts.context import get_kitsu_shot_url

def open_shot_in_kitsu():
    try:
        url = get_kitsu_shot_url()
    except Exception as e:
        nuke.message(f"Kitsu Error:\n{e}")
        return

    webbrowser.open(url)
    nuke.message("Opened in Kitsu:\n" + url)
