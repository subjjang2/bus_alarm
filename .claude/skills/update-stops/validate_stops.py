"""stops.json 스키마 검증 (네트워크 없음, 순수 검증).

update-stops 스킬의 헬퍼. src.config.load_stops()를 재사용해 로드하고
필수 필드/타입을 확인한다. 실패 시 문제 경로와 함께 exit 1.

사용법: python .claude/skills/update-stops/validate_stops.py [stops.json 경로]
"""

import re
import sys
from pathlib import Path

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 출력을 깨뜨린다. UTF-8로 고정.
# (scripts/hooks/tdd_guard.py 와 동일한 패턴.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# 프로젝트 루트를 sys.path에 추가해 src.config를 재사용한다 (중복 구현 금지).
_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from src.config import load_stops  # noqa: E402

_ARS_ID_RE = re.compile(r"^\d{4,6}$")
# ADR-002: 출발 정류장(ars_id)만 허용. 도착지/목적지류 키가 보이면 경고.
_DEST_KEY_HINTS = ("to_ars_id", "dest_ars_id", "destination", "to_stop", "arrival_ars_id")


def _fail(errors):
    print("stops.json 검증 실패:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)


def validate(stops: dict) -> list:
    errors = []

    if not isinstance(stops, dict) or not stops:
        return ["최상위가 비어있지 않은 객체여야 합니다."]

    for scenario_name, scenario in stops.items():
        prefix = f"{scenario_name}"

        for hint in _DEST_KEY_HINTS:
            if isinstance(scenario, dict) and hint in scenario:
                errors.append(
                    f"{prefix}: '{hint}' 키 발견 — ADR-002 위반(도착 정류장/경로 "
                    "금지, ars_id는 출발 정류장만 허용)."
                )

        if not isinstance(scenario, dict):
            errors.append(f"{prefix}: 시나리오는 객체여야 합니다.")
            continue

        label = scenario.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{prefix}.label: 비어있지 않은 문자열이어야 합니다.")

        ars_id = scenario.get("ars_id")
        if not isinstance(ars_id, str) or not _ARS_ID_RE.match(ars_id):
            errors.append(
                f"{prefix}.ars_id: 4~6자리 숫자 문자열이어야 합니다 (현재: {ars_id!r})."
            )

        groups = scenario.get("groups")
        if not isinstance(groups, list) or not groups:
            errors.append(f"{prefix}.groups: 비어있지 않은 배열이어야 합니다.")
            continue

        for i, group in enumerate(groups):
            gprefix = f"{prefix}.groups[{i}]"
            if not isinstance(group, dict):
                errors.append(f"{gprefix}: 객체여야 합니다.")
                continue
            if "label" not in group or not isinstance(group.get("label"), str):
                errors.append(f"{gprefix}.label: 문자열이어야 합니다 (빈 문자열 허용).")
            routes = group.get("routes")
            if not isinstance(routes, list) or not routes:
                errors.append(f"{gprefix}.routes: 비어있지 않은 배열이어야 합니다.")
            elif not all(isinstance(r, str) and r for r in routes):
                errors.append(f"{gprefix}.routes: 모든 원소가 비어있지 않은 문자열이어야 합니다.")

    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(_ROOT / "stops.json")
    try:
        stops = load_stops(path)
    except Exception as exc:
        print(f"stops.json 로드 실패: {type(exc).__name__}: {exc}")
        sys.exit(1)

    errors = validate(stops)
    if errors:
        _fail(errors)

    print(f"OK: {path} — {len(stops)}개 시나리오 검증 통과.")


if __name__ == "__main__":
    main()
