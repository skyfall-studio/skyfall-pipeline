#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SKYFALL Pipeline — setup_from_excel_v7
FULL EXPANDED VERSION

Excel ingest with robust normalization:
 - Accepts: SHOT CODE alone OR EP/SEQ/SHOT split
 - Auto-clean spaces, hyphens, tabs, weird formatting
 - Auto-recombine into SKYFALL SHOT CODE standard
 - Multi-line descriptions supported
 - Duration optional

Uses setup_shot_v7 as the backend.
"""

import os
import sys
import uuid
import pandas as pd
from pathlib import Path

PIPELINE_ROOT = Path(os.getenv("PIPELINE_ROOT", "/opt/pipeline")).resolve()
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

# backend
from setup_shot_v7 import setup_shot


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clean_string(v):
    """Normalize common dirty Excel input
       - Remove spaces, tabs
       - Replace hyphens with _
       - Strip weird characters
    """
    if pd.isna(v):
        return ""
    v = str(v).strip()
    v = v.replace(" ", "")
    v = v.replace("\t", "")
    v = v.replace("-", "_")
    v = v.replace("__", "_")
    return v


def normalize_shot_code(row: dict):
    """
    Accept several formats:

    1) SHOT CODE = "EP04_S003_0010"
    2) EP, SEQ, SHOT present separately
    3) SEQ, SHOT only
    4) SHOT only

    Returns normalized shot_code.
    """

    # 1) If SHOT CODE column exists
    if "SHOT CODE" in row and not pd.isna(row["SHOT CODE"]):
        raw = clean_string(row["SHOT CODE"])
        return raw

    # 2) If EP + SEQ + SHOT exist
    if all(col in row for col in ["EP", "SEQ", "SHOT"]):
        if not pd.isna(row["SHOT"]):
            ep = clean_string(row["EP"])
            seq = clean_string(row["SEQ"])
            shot = clean_string(row["SHOT"])

            parts = []
            if ep:
                parts.append(ep)
            if seq:
                parts.append(seq)
            if shot:
                parts.append(shot)

            return "_".join(parts)

    # 3) If SEQ + SHOT exist
    if all(col in row for col in ["SEQ", "SHOT"]):
        seq = clean_string(row["SEQ"])
        shot = clean_string(row["SHOT"])
        if seq and shot:
            return f"{seq}_{shot}"

    # 4) Only SHOT exists
    if "SHOT" in row:
        shot = clean_string(row["SHOT"])
        return shot

    raise ValueError(f"Cannot parse shot code from row: {row}")


def read_description(row):
    """Multi-line description safe extraction"""
    if "DESCRIPTION" not in row:
        return None
    if pd.isna(row["DESCRIPTION"]):
        return None
    return str(row["DESCRIPTION"]).strip()


def read_duration(row):
    if "DURATION" not in row:
        return None
    v = row["DURATION"]
    if pd.isna(v) or v == "":
        return None
    try:
        return int(v)
    except:
        return None


# ------------------------------------------------------------
# Main ingest
# ------------------------------------------------------------
def ingest_excel(file_path: str):
    print(f"📄 Loading Excel: {file_path}")

    df = pd.read_excel(file_path, dtype=str)
    df = df.fillna("")  # avoid NaN

    required = ["SHOW"]
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Excel missing required column: {r}")

    print(f"\n✅ Loaded {len(df)} rows from Excel\n")

    success = 0
    failed = 0

    # Logs
    from datetime import datetime
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_items = []

    for idx, row in df.iterrows():
        show = clean_string(row["SHOW"])
        if not show:
            print(f"⚠️ Row {idx}: SHOW missing — skipped\n")
            continue

        try:
            # Normalize shot code
            shot_code = normalize_shot_code(row)

            print("=" * 60)
            print(f"🎬 {show} / {shot_code}")

            desc = read_description(row)
            if desc:
                print(f"📝 {desc}")

            duration = read_duration(row)

            # Backend ingest
            setup_shot(show, shot_code, desc, duration)

            success += 1
            log_items.append({"show": show, "shot_code": shot_code, "status": "OK"})

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            log_items.append({"show": show, "shot_code": row.to_dict(), "status": f"ERROR {e}"})

    # summary
    print("\n" + "=" * 60)
    print("📊 Batch Summary")
    print(f"   Total   : {len(df)}")
    print(f"   Success : {success}")
    print(f"   Failed  : {failed}")
    print("=" * 60)

    # Save log
    log_path = Path(f"/Volumes/skyfall/logs/excel_ingest_{run_id}.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    import json
    log_path.write_text(json.dumps(log_items, indent=4, ensure_ascii=False), encoding="utf-8")

    print(f"\n📄 Log saved: {log_path}")
    print("🎉 Excel ingest complete!")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SKYFALL Excel Ingest v7")
    parser.add_argument("--file", required=True, help="Excel file path")

    args = parser.parse_args()
    ingest_excel(args.file)
