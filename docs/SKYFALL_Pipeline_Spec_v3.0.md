
# 📘 SKYFALL PIPELINE SPECIFICATION — **v3.0 (2025-11-16)**  
**Issued by:** SKYFALL Pipeline Department  
**Audience:** Pipeline TDs, Engineering, Supervisors, IT/Infra Teams  
**Scope:** Unified VFX pipeline architecture for SKYFALL Korea · Vietnam · India · Singapore IDC  

---

# 📑 Table of Contents

1. Overview  
2. Global Architecture  
3. Runtime Pipeline Structure (Local /opt/pipeline)  
4. Developer Workspace Structure (Local ~/skyfall-dev)  
5. NAS Project Data Structure (FULL v3.0)  
6. Pipeline Deployment Model  
7. Repository Structure & Git Workflow  
8. Nuke Integration  
9. Background Services  
10. Security & Access Control  
11. Environment Variables  
12. Appendices  

---

# 1. Overview

SKYFALL Pipeline v3.0 integrates:

- Local runtime code: **/opt/pipeline/**
- Developer workspace: **~/skyfall-dev/**
- NAS-based project storage: **/Volumes/skyfall/**
- GitHub Organization: **skyfall-studio**
- Kitsu automation (setup → ingest → publish)
- Multi-site workflow (KR ↔ VN ↔ IN ↔ SG IDC)

Core Principles:

- Code executes locally → fastest  
- Data stored on NAS → safest  
- Updates flow through GitHub → clean & controlled  
- Shows follow strict standardized structure  
- Nuke integrates automatically  

---

# 2. Global Architecture

```
Developer Machine (~/skyfall-dev)
             ↓ push
GitHub (skyfall-studio/skyfall-pipeline)
             ↓ pull
──────────────────────────────────────────
Runtime Pipeline on Artist/Supervisor PCs
             /opt/pipeline
──────────────────────────────────────────
NAS Project Storage
         /Volumes/skyfall/
──────────────────────────────────────────
```

---

# 3. Runtime Pipeline Structure – /opt/pipeline

```
/opt/pipeline/
│
├── core/
│   ├── api/
│   ├── io/
│   ├── env/
│   ├── publish/
│   │   └── schema/
│   ├── utils/
│   └── log/
│
├── apps/
│   ├── nuke/
│   │   ├── plugins/
│   │   ├── nodes/
│   │   └── hooks/
│   ├── resolve/
│   ├── blender/
│   └── maya/
│
├── tools/
│   ├── setup_shots.py
│   ├── inbound_ingest.py
│   ├── nuke_publish.py
│   ├── qc_tool.py
│   └── launcher.py
│
├── services/
│   ├── kitsu_sync_daemon.py
│   ├── ingest_watchdog.py
│   ├── dailies_daemon.py
│   └── service_config.yml
│
├── config/
│   ├── pathmap.json
│   ├── pipeline_settings.json
│   ├── ocio/
│   ├── luts/
│   └── menu_templates/
│
├── templates/
│   ├── nuke/
│   ├── publish/
│   └── delivery/
│
└── install/
```

---

# 4. Developer Workspace Structure – ~/skyfall-dev

```
~/skyfall-dev/
│
├── pipeline/              ← main development repo
├── ingest-tests/
├── nuke-tests/
├── docs/
└── sandbox/
```

Develop here → push → deploy to all artists via /opt/pipeline.

---

# 5. NAS Project Data Structure — **FULL Expanded v3.0**

The following structure merges **v2.5 + v3.0** into the final, unified NAS layout.

```
/Volumes/skyfall/
│
├── shows/                                      ← All shows (Film / Series)
│   └── <SHOW_NAME>/                             ← ABC, HERO, MOV01, etc.
│       │
│       ├── project.yml                          ← Show-level metadata
│       │
│       ├── assets/                              ← Show shared assets
│       │   ├── char/
│       │   ├── env/
│       │   ├── prop/
│       │   ├── tex/
│       │   └── lookdev/
│       │
│       ├── plates/
│       │   ├── EP01/S001/0010/
│       │   │   ├── camera/                      ← RAW: R3D, ARRIRAW, BRAW
│       │   │   ├── hdr/                         ← HDRI
│       │   │   ├── lidar/                       ← Lidar / photogrammetry
│       │   │   └── metadata/                    ← Slate, lens, LUT, reports
│       │   └── ingest_log/                      ← ingest report JSON/CSV
│       │
│       ├── editorial/
│       │   ├── offline/
│       │   ├── conform/
│       │   ├── timeline/
│       │   └── reference/
│       │
│       ├── EP01/
│       │   └── S001/0010/
│       │        ├── plate/
│       │        ├── prep/
│       │        ├── roto/
│       │        ├── comp/
│       │        │   ├── render/
│       │        │   ├── preview/
│       │        │   └── nk/
│       │        ├── elements/
│       │        ├── cache/
│       │        ├── notes/
│       │        └── meta/
│       │             └── task_log.json
│       │
│       ├── dailies/
│       │   ├── EP01/
│       │   │   └── 2025-11-16_teamreview.mov
│       │   └── ...
│       │
│       ├── deliveries/
│       │   ├── EP01/
│       │   │   ├── <SHOW>_EP01_final_v001/
│       │   │   │   ├── mov/
│       │   │   │   ├── exr/
│       │   │   │   ├── docs/
│       │   │   │   └── manifest/
│       │   └── season_master/
│       │
│       ├── exchange/
│       │   ├── inbound/
│       │   │   ├── YYYYMMDD_batch/
│       │   │   │   ├── 01_list/
│       │   │   │   ├── 02_edit/
│       │   │   │   ├── 03_plate/
│       │   │   │   └── readme.txt
│       │   ├── outbound/
│       │   │   ├── YYYYMMDD_delivery/
│       │   │   │   ├── 01_mov/
│       │   │   │   ├── 02_assets/
│       │   │   │   ├── 03_docs/
│       │   │   │   └── hashlist.md5
│       │   ├── archive/
│       │   └── nda/
│       │
│       ├── config/
│       │   ├── ocio/
│       │   ├── luts/
│       │   ├── env/
│       │   │   ├── nuke_template.nk
│       │   │   └── skyfall_publish_panel.gizmo
│       │   ├── pipeline_settings.json
│       │   ├── version_manifest.yml
│       │   └── backup_policy.yml
│       │
│       └── logs/
│
├── assets/                                      ← Studio-level assets
│
├── config/                                      ← Global config
│
└── opt/                                         ← Per-show config (data only)
```

---

# 6. Pipeline Deployment Model (v3.0)

```
~/skyfall-dev/pipeline      ← 개발
        ↓ push
GitHub (skyfall-studio)
        ↓ pull
/opt/pipeline               ← Runtime for all artists
```

---

# 7. Repository Structure & Git Workflow

```
main        ← stable  
dev         ← development  
feature/*   ← feature branches  
hotfix/*    ← urgent fixes  
```

---

# 8. Nuke Integration (Auto-Load)

```
/opt/pipeline/apps/nuke/menu.py
/opt/pipeline/apps/nuke/hooks/*
```

---

# 9. Background Services

- kitsu_sync_daemon  
- ingest_watchdog  
- dailies_daemon  

---

# 10. Security & Access Control

- /opt/pipeline → root-owned (read-only for artists)  
- /Volumes/skyfall → NAS-permissions (department separated)  
- OCIO/LUT stored on NAS  
- NDA content separated in `/exchange/nda`

---

# 11. Environment Variables

```
export PIPELINE_ROOT=/opt/pipeline
export SKYFALL_SHOW_ROOT=/Volumes/skyfall/shows
export KITSU_URL=https://kitsu.skyfall.studio/api
export OCIO=/Volumes/skyfall/config/ocio/config.ocio
```

---

# 12. Appendices

## Appendix A — Version Manifest Example
```yaml
episode: EP03
delivery_tag: v001
shots:
  - EP03_S024_0020
  - EP03_S024_0030
created: 2025-11-16T10:00:00+09:00
```

## Appendix B — hierarchy_template.json
```json
{
  "shot_tree": [
    "plate",
    "prep",
    "roto",
    "comp/render",
    "comp/preview",
    "comp/nk",
    "elements",
    "cache",
    "notes",
    "meta"
  ]
}
```

---

# END OF DOCUMENT
**SKYFALL INTERNAL USE ONLY**
