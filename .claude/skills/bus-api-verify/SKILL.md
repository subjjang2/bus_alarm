---
name: bus-api-verify
description: >-
  서울 버스도착정보 API 실응답이 src/bus_service.py 의 파싱 가정(msgBody.
  itemList, rtNm, arrmsg1/2, congestion1/2)과 실제로 맞는지 검증한다.
  docs/PROGRESS.md 가 실응답 스키마 미검증(API 키 승인 대기)을 블로킹 이슈로
  기록하고 있어, 키 승인 후 반드시 한 번 돌려야 한다. "API 검증", "실응답
  확인", "버스 API 스모크", "API 키 승인됐어" 등에 트리거. 유효한
  SEOUL_BUS_API_KEY 필요.
---

# 버스 API 실응답 검증

`src/bus_service.py`의 파싱 로직은 **실제 API를 호출해본 적 없이** 문서/추정
스키마로 작성되었다(`docs/PROGRESS.md` 참고). 키가 승인되면 이 스킬로 가정과
실제를 대조한다.

## 절차

1. `env/.env`에 `SEOUL_BUS_API_KEY`가 채워져 있는지 확인한다(없으면
   `env/.env.example`을 복사해 채운다). 하드코딩 금지 — 반드시 env로.
2. 검증 스크립트 실행 (기본은 `morning` 시나리오, 인자로 `evening` 선택 가능):
   ```
   python .claude/skills/bus-api-verify/verify_api.py morning
   ```
3. 출력된 리포트를 확인한다:
   - `msgBody.itemList` 필드가 실제로 존재하는가
   - 각 아이템에 `rtNm`, `arrmsg1`, `arrmsg2`, `congestion1`, `congestion2`가
     실제로 오는가 (가정 vs 실제 diff)
   - 혼잡도 코드가 문서화된 3/4/5 외의 값을 주는가
4. 불일치가 있으면:
   - `src/bus_service.py`의 파싱(특히 `_extract_items`, `_get_congestion`,
     `_CONGESTION` 매핑)을 실제 스키마에 맞게 수정한다 — **test-first**
     (tdd_guard 훅 적용 대상이므로 `tests/test_bus_service.py`를 먼저 갱신).
   - `docs/PROGRESS.md`의 블로킹 상태를 갱신한다("검증 완료" 기록).

## 주의

- 이 스크립트는 `tests/`가 아닌 수동 검증 도구다. 실 네트워크를 호출하므로
  CI/pytest에 편입하지 않는다(CLAUDE.md: 테스트에서 외부 API mock 필수 규칙은
  `tests/`에만 적용).
- 키가 없으면 스크립트는 크래시 없이 안내 메시지만 출력하고 종료한다.
