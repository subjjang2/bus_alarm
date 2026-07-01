---
name: update-stops
description: >-
  stops.json의 정류장(ars_id)·노선(routes)·방면 그룹을 추가·변경하고 스키마를
  검증한다. stops.json 구조가 과거 짧은 기간에 평면 routes에서 groups[] 로
  드리프트한 이력이 있어 수기 편집 후 검증이 필요하다. "정류장 갱신", "노선
  추가", "stops 수정", "ars_id 변경", "방면 그룹 추가" 등에 트리거.
---

# stops.json 갱신 + 검증

## 절차

1. 바꿀 값을 확인한다: 정류장이면 `ars_id`(서울 버스 정류소 ARS ID, 보통
   5자리 문자열), 노선이면 그룹의 `routes` 배열, 방면 표시면 그룹의 `label`.
2. `stops.json`을 직접 편집한다. 현재 스키마:
   ```json
   {
     "morning": {
       "label": "헤더에 표시될 텍스트",
       "ars_id": "16004",
       "groups": [{"label": "", "routes": ["6632"]}]
     }
   }
   ```
   - `label`이 빈 문자열이면 `🚏 그룹명` 줄이 생략된다(그룹이 하나뿐일 때 씀).
   - `routes`는 노선번호 **문자열** 목록(정수 아님).
3. 검증 스크립트를 실행한다:
   ```
   python .claude/skills/update-stops/validate_stops.py
   ```
   실패하면 출력된 경로를 따라 수정한다.
4. 정류장/그룹 라벨을 바꿨다면 `docs/UI_GUIDE.md`의 예시 출력이나 README의
   설명이 실제와 어긋나지 않는지 확인한다(자동 동기화 수단 없음, 수기 확인).
5. `python -m pytest tests/`로 회귀를 확인한다.

## 금지 사항

- **ADR-002**: `ars_id`는 항상 **출발** 정류장이다. 도착 정류장 ID나 목적지
  좌표를 넣지 않는다. `validate_stops.py`가 `to_ars_id`/`dest`류 키를 발견하면
  경고하지만, 키 이름을 바꿔 우회하지 않는다.
- routes 배열을 빈 리스트로 두지 않는다(도착정보가 항상 0건으로 나옴).
