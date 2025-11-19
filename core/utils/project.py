"""
core/utils/project.py

프로젝트 메타 정보 관련 유틸.
지금은 fps 고정이지만, 나중에 project.yml 파싱으로 교체 예정.
"""


def get_fps() -> int:
    # TODO: /Volumes/skyfall/shows/<show>/project.yml 에서 읽어오도록 확장
    return 24
