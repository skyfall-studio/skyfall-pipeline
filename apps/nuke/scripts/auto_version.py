import nuke
import re
import os
from pathlib import Path


def parse_version(path):
    m = re.search(r"_v(\d+)\.nk$", path)
    return int(m.group(1)) if m else None


def next_version(v):
    return f"{v+1:03d}"


def save_new_version():
    path = nuke.root().name()
    v = parse_version(path)

    if v is None:
        nuke.message("Version format invalid: *_v###.nk required")
        return

    new_v = next_version(v)
    new_path = re.sub(r"_v\d+\.nk$", f"_v{new_v}.nk", path)

    nuke.scriptSaveAs(new_path)
    nuke.message(f"Saved new version:\n{new_path}")
