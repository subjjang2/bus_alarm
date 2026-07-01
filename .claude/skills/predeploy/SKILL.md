---
name: predeploy
description: >-
  Railway 배포 전 게이트. pytest·시크릿 노출 패턴·env 미커밋·Procfile을
  기계적으로 점검한 뒤 로컬 E2E 스모크와 Railway 배포 절차를 안내한다.
  docs/PROGRESS.md에 흩어진 TODO를 실행 가능한 체크리스트로 대체하고, 과거
  "시크릿 유출" 커밋(d7845d3) 같은 재발을 막는다. "배포", "deploy", "릴리스",
  "배포 전 점검", "Railway 배포" 등에 트리거.
---

# 배포 전 점검

## 절차

1. 점검 스크립트 실행:
   ```
   python .claude/skills/predeploy/predeploy_check.py
   ```
   PASS/FAIL을 항목별로 출력하며, 하나라도 FAIL이면 exit 1로 끝난다. 실패
   항목을 고치기 전에는 배포로 넘어가지 않는다.
2. 전부 PASS면 **로컬 E2E 스모크**(선택, 유효한 키가 있을 때만):
   `python -m src.bot`을 실행해 텔레그램에서 `/morning`, `/evening`을 직접
   보내 응답을 확인한다. 키가 없으면 이 단계는 건너뛴다.
3. **Railway 배포**: `mcp__railway__*` 도구를 사용한다.
   - 키/토큰은 **Railway Variables**에만 입력한다. 코드나 커밋에 하드코딩하지
     않는다(ADR-004). 필요한 변수: `SEOUL_BUS_API_KEY`, `TELEGRAM_BOT_TOKEN`,
     `TELEGRAM_CHAT_ID`.
   - 배포 대상 프로세스는 `Procfile`의 `worker: python -m src.bot`
     (long-polling, 포트/웹훅 불필요).
   - `accept-deploy` 등 되돌리기 어려운 동작 전에는 사용자에게 먼저 확인한다.

## 점검 항목 (predeploy_check.py)

1. `python -m pytest tests/` 통과.
2. `src/` 내 시크릿 노출 의심 패턴 스캔 — 하드코딩된 키/토큰 리터럴, 예외를
   `str(exc)`/`{exc}` 형태로 노출하는 새 코드(요청 URL에 `serviceKey`/토큰이
   담겨 샐 수 있음, `bot.py:142-147` 참고).
3. `git ls-files env/`에 `.env`(실값)가 없어야 함(`.env.example`만 추적).
4. `Procfile`, `requirements.txt` 존재 확인.

## 금지 사항

- 점검을 건너뛰고 바로 배포하지 않는다.
- FAIL이 뜬 상태로 "일단 배포하고 나중에 고치기" 하지 않는다.
