# apps/nuke/init.py
# Nuke 시작 시 SKYFALL 파이프라인 경로를 Python path에 추가

import os
import sys
from pathlib import Path

def _ensure_pipeline_root():
    root = os.getenv("PIPELINE_ROOT")
    if not root:
        # init.py 기준으로 상위 두 단계가 pipeline 루트라고 가정
        root = str(Path(__file__).resolve().parents[2])
        os.environ["PIPELINE_ROOT"] = root

    if root not in sys.path:
        sys.path.insert(0, root)

_ensure_pipeline_root()
