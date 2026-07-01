"""서울 버스 API 실응답 스키마 검증 (bus-api-verify 스킬 헬퍼).

src/bus_service.py 의 파싱 가정(msgBody.itemList, rtNm, arrmsg1/2,
congestion1/2)이 실제 API 응답과 맞는지 대조 리포트를 출력한다.

이 스크립트는 실 네트워크를 호출하는 수동 검증 도구다. tests/ 대상이 아니며
pytest에 편입하지 않는다 (CLAUDE.md 의 mock 강제 규칙은 tests/ 전용).

사용법: python .claude/skills/bus-api-verify/verify_api.py [morning|evening]
"""

import sys
from pathlib import Path

# Windows 콘솔/파이프 기본 인코딩(cp949)은 한글 출력을 깨뜨린다. UTF-8로 고정.
# (scripts/hooks/tdd_guard.py 와 동일한 패턴.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import requests  # noqa: E402
from urllib.parse import unquote  # noqa: E402

from src.bus_service import API_URL, _extract_items  # noqa: E402
from src.config import get_scenario, load_settings, load_stops  # noqa: E402

_EXPECTED_ITEM_FIELDS = ("rtNm", "arrmsg1", "arrmsg2", "congestion1", "congestion2")
_KNOWN_CONGESTION_CODES = {"0", "3", "4", "5", ""}


def main():
    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "morning"

    settings = load_settings()
    if not settings.seoul_bus_api_key:
        print(
            "SEOUL_BUS_API_KEY 가 설정되지 않았습니다 (env/.env). "
            "키 승인 후 다시 실행하세요."
        )
        return

    scenario = get_scenario(load_stops(), scenario_name)
    ars_id = scenario["ars_id"]

    print(f"조회: scenario={scenario_name} ars_id={ars_id}")
    resp = requests.get(
        API_URL,
        params={
            "serviceKey": unquote(settings.seoul_bus_api_key),
            "arsId": ars_id,
            "resultType": "json",
        },
    )
    resp.raise_for_status()
    payload = resp.json()

    if "msgBody" not in (payload or {}):
        print("불일치: 응답에 'msgBody' 키가 없습니다. 전체 응답 최상위 키:")
        print(f"  {list((payload or {}).keys())}")
        return

    items = _extract_items(payload)
    print(f"itemList 항목 수: {len(items)}")
    if not items:
        print("주의: itemList가 비어 있습니다 (해당 정류장에 도착 예정 버스가 없을 수 있음).")
        return

    missing_fields = set()
    unknown_congestion = set()
    for item in items:
        for field in _EXPECTED_ITEM_FIELDS:
            if field not in item:
                missing_fields.add(field)
        for cf in ("congestion1", "congestion2"):
            val = str(item.get(cf, "")).strip()
            if val not in _KNOWN_CONGESTION_CODES:
                unknown_congestion.add(val)

    print("\n=== 가정 vs 실제 리포트 ===")
    if missing_fields:
        print(f"불일치: 예상 필드가 일부 응답에 없음 -> {sorted(missing_fields)}")
    else:
        print(f"일치: 예상 필드 {_EXPECTED_ITEM_FIELDS} 모두 확인됨.")

    if unknown_congestion:
        print(
            f"주의: 문서화되지 않은 혼잡도 코드 발견 -> {sorted(unknown_congestion)} "
            "(bus_service.py의 _CONGESTION 매핑 확인 필요)"
        )
    else:
        print("일치: 혼잡도 코드가 모두 알려진 값(0/3/4/5/없음) 범위 안.")

    print(f"\n샘플 item 1건:\n  {items[0]}")


if __name__ == "__main__":
    main()
