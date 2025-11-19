#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 배치 처리 v007 - Description + v007 스크립트 연동

- Excel → 단일 샷 스크립트(v007) batch 실행
- DESCRIPTION 컬럼을 샷 description 으로 전달
- JSON 리포트 생성
"""

import argparse
import pandas as pd
import subprocess
import sys
from pathlib import Path
import re
from datetime import datetime
import json

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from lib.pipeline_env import SKYFALL_ROOT


# 기본으로 사용할 샷 스크립트 (v007)
DEFAULT_SCRIPT = str(PIPELINE_ROOT / "setup_shots" / "setup_shots_v007.py")


def parse_shot_code(code: str) -> tuple:
    """샷 코드 파싱 (EPxx_Sxxx_yyyy 형식 정규화)"""
    code = code.strip().upper()
    parts = code.split("_")

    if len(parts) != 3:
        raise ValueError(f"Invalid shot code: {code}")

    ep, seq, shot = parts

    # Episode 정규화
    ep_match = re.match(r"E(P)?(\d+)", ep)
    if ep_match:
        num = int(ep_match.group(2))
        ep = f"EP{num:02d}"

    # Sequence 정규화
    seq_match = re.match(r"(SQ|S)(\d+)", seq)
    if seq_match:
        num = int(seq_match.group(2))
        seq = f"S{num:03d}"

    # Shot 정규화
    if shot.startswith("SH"):
        shot = shot[2:]
    if shot.isdigit():
        shot = f"{int(shot):04d}"

    return ep, seq, shot


def run_single(
    script_path: str,
    show: str,
    ep: str,
    seq: str,
    shot: str,
    description: str = None,
) -> dict:
    """단일 샷 설정 실행 (v007 스크립트 호출)"""

    cmd = [
        "python3",
        script_path,
        "--show",
        show,
        "--ep",
        ep,
        "--seq",
        seq,
        "--shot",
        shot,
    ]

    # Description 추가
    if description:
        cmd.extend(["--description", description])

    shot_code = f"{ep}_{seq}_{shot}"
    print("\n" + "=" * 60)
    print(f"🎬 {show} / {shot_code}")
    if description:
        print(f"   📝 {description}")
    print("=" * 60)

    result = {
        "show": show,
        "ep": ep,
        "seq": seq,
        "shot": shot,
        "code": shot_code,
        "description": description,
        "success": False,
        "error": None,
    }

    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,  # v006 보다 조금 여유
        )
        result["success"] = True
        print(proc.stdout)

    except subprocess.TimeoutExpired:
        result["error"] = "Timeout"
        print("❌ Timeout!")

    except subprocess.CalledProcessError as e:
        result["error"] = e.stderr[:500] if e.stderr else "Unknown error"
        print(f"❌ Failed: {result['error']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Error: {e}")

    return result


def load_shots_from_excel(file_path: str) -> list:
    """Excel에서 샷 목록 로드 (Description 포함)"""

    df = pd.read_excel(file_path)

    # 필수 컬럼 체크
    required_cols = ["SHOW", "SHOT CODE"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError("Excel must have 'SHOW' and 'SHOT CODE' columns")

    # Description 컬럼 존재 확인
    has_description = "DESCRIPTION" in df.columns or "Description" in df.columns
    desc_col = None
    if has_description:
        desc_col = "DESCRIPTION" if "DESCRIPTION" in df.columns else "Description"

    shots = []

    for idx, row in df.iterrows():
        try:
            show = str(row["SHOW"]).strip()
            code = str(row["SHOT CODE"]).strip()

            if not show or not code or code.lower() == "nan":
                continue

            # Description 읽기
            description = None
            if desc_col and desc_col in row:
                desc_value = row[desc_col]
                if pd.notna(desc_value) and str(desc_value).strip():
                    description = str(desc_value).strip()

            ep, seq, shot = parse_shot_code(code)
            shots.append((show, ep, seq, shot, description))

        except Exception as e:
            print(f"⚠️ Row {idx + 2}: {e}")
            continue

    return shots


def main():
    parser = argparse.ArgumentParser(
        description="Batch shot setup from Excel with description support (v007)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup_from_excel_v007.py --file shots.xlsx

Excel Format:
  | SHOW | SHOT CODE      | DESCRIPTION           |
  |------|----------------|-----------------------|
  | ABC  | EP23_S009_0020 | Car chase scene       |
  | ABC  | EP23_S014_0020 | Hero enters building  |

Note:
  - DESCRIPTION column is optional
  - 내부적으로 setup_shots_v007.py 를 호출함
        """,
    )
    parser.add_argument("--file", required=True, help="Excel file path")
    parser.add_argument("--report", help="Output report path (JSON)")
    parser.add_argument(
        "--script",
        help=f"Custom shot setup script path (default: {DEFAULT_SCRIPT})",
        default=DEFAULT_SCRIPT,
    )
    args = parser.parse_args()

    script_path = args.script

    if not Path(script_path).is_file():
        print(f"❌ Shot script not found: {script_path}")
        sys.exit(1)

    # Excel 읽기
    try:
        shots = load_shots_from_excel(args.file)
    except Exception as e:
        print(f"❌ Failed to read Excel: {e}")
        sys.exit(1)

    if not shots:
        print("❌ No valid shots found in Excel")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🚀 BATCH SETUP START (v007)")
    print("=" * 60)
    print(f"📋 Total: {len(shots)} shots")

    # Description 통계
    with_desc = sum(1 for s in shots if s[4])
    if with_desc > 0:
        print(f"📝 With description: {with_desc} shots")

    print()

    # 배치 실행
    results = []
    for idx, (show, ep, seq, shot, description) in enumerate(shots, 1):
        print(f"\n[{idx}/{len(shots)}]")
        result = run_single(script_path, show, ep, seq, shot, description)
        results.append(result)

    # 결과 집계
    success = sum(1 for r in results if r["success"])
    failed = len(results) - success

    print("\n" + "=" * 60)
    print("📊 BATCH SUMMARY (v007)")
    print("=" * 60)
    print(f"Total:      {len(results)}")
    print(f"✅ Success: {success}")
    print(f"❌ Failed:  {failed}")
    print("=" * 60)

    # 실패 목록
    if failed > 0:
        print("\n❌ Failed shots:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['code']}: {r['error']}")

    # 리포트 저장
    if args.report:
        report_path = Path(args.report)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(SKYFALL_ROOT) / "logs" / f"batch_report_{timestamp}.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "success": success,
        "failed": failed,
        "results": results,
        "script": str(script_path),
    }

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Report: {report_path}")
    print("\n🎉 Batch Complete! (v007)\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
