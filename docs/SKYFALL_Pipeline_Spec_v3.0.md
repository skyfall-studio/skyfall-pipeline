
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
5. NAS Project Data Structure (/Volumes/skyfall)  
6. Pipeline Deployment Model  
7. Repository Structure & Git Workflow  
8. Nuke Integration (High-Level)  
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
- Kitsu API workflow (setup, ingest, publish)
- Multi-site scalability (KR ↔ VN ↔ IN ↔ SG)

**Core Philosophy**
- Code = local  
- Data = NAS  
- Updates = Git  
- Shows = structure-first  
- Nuke = fully integrated  
- Multi-site = latency-safe architecture  

---

# 2. Global Architecture

```
          Developer (~/skyfall-dev)
                   ↓ push
        GitHub (skyfall-studio/skyfall-pipeline)
                   ↓ pull
──────────────────────────────────────────
   Runtime Pipeline on Every Client Machine
                /opt/pipeline
──────────────────────────────────────────
              NAS Project Storage
         /Volumes/skyfall/shows/
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
├── pipeline/
├── ingest-tests/
├── nuke-tests/
├── docs/
└── sandbox/
```

---

# 5. NAS Project Data Structure – /Volumes/skyfall

```
/Volumes/skyfall/
│
├── shows/
│   └── <SHOW_NAME>/
│       ├── project.yml
│       ├── assets/
│       ├── plates/
│       ├── editorial/
│       ├── EP01/
│       │   └── S001/0010/
│       ├── dailies/
│       ├── deliveries/
│       ├── exchange/
│       ├── config/
│       └── logs/
│
├── assets/
├── config/
└── opt/
```

---

# 6. Pipeline Deployment Model (v3.0)

```
~/skyfall-dev/pipeline
     ↓ push
GitHub (skyfall-studio/skyfall-pipeline)
     ↓ pull
/opt/pipeline (runtime engine)
```

---

# 7. Repository Structure & Git Workflow

```
main        ← stable  
dev         ← development  
feature/*   ← feature branches  
hotfix/*    ← emergency fixes  
```

---

# 8. Nuke Integration

Loads automatically:

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

- Code: /opt/pipeline (root-owned)  
- Data: /Volumes/skyfall (NAS)  

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
