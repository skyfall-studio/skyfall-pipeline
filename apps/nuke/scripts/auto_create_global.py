import nuke

def create_global_node():
    # 이미 있으면 재생성하지 않음
    if nuke.toNode("SKYFALL_SIGNATURE_GLOBAL"):
        return

    try:
        g = nuke.createNode("Group", "name SKYFALL_SIGNATURE_GLOBAL")
        g.begin()

        tn = nuke.createNode("Text", "name shotinfo_text")
        tn["message"].setValue("[python {from apps.nuke.scripts.context import get_show; get_show()}]")
        tn["ypos"].setValue(-50)

        g.end()
        nuke.tprint("SKYFALL: Global node created.")
    except Exception as e:
        nuke.tprint("SKYFALL global node error:", e)
