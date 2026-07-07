# 프로젝트: 버스 알리미 봇 (bus-alarm-bot)

## 기술 스택
- Python 3 (표준 라이브러리 + requests + python-dotenv)
- 테스트: pytest
- 배포: Railway (worker 프로세스, 텔레그램 long-polling)
- 외부 API: 서울 버스도착정보 API, 텔레그램 Bot API

## 아키텍처 규칙
- CRITICAL: 외부 버스 API 호출은 `src/bus_service.py` 에서만, 텔레그램 호출은 `src/bot.py` 에서만 한다. 다른 곳에서 직접 호출하지 마라.
- CRITICAL: API 키/토큰을 코드에 하드코딩하지 마라. 반드시 `env/.env` 또는 환경변수에서 읽는다.
- CRITICAL: 상태를 저장하지 마라 (DB/캐시/파일 영속화 없음). 매 명령마다 API 호출 → 포맷 → 응답.
- CRITICAL: `src/` 아래 구현 파일(.py)을 추가/수정하기 전에 대응하는 `tests/test_<module>.py` 가 먼저 존재해야 한다. 없으면 PreToolUse 훅(`scripts/hooks/tdd_guard.py`)이 Edit/Write 자체를 차단한다 — 테스트부터 작성하라.
- PreToolUse 훅이 위험한 Bash 명령어(`rm -rf`, `git push --force`, `git reset --hard`, `DROP TABLE`)도 차단한다 (`.claude/settings.json`).
- 출발 정류장(`ars_id`)만 사용한다. 도착 정류장 ID를 입력받거나 경로 탐색을 구현하지 마라. (ADR-002)
- stops.json 시나리오는 `ars_id` + `groups[]`(방면별 `label`/`routes`) 구조다. 상세 스키마·데이터 흐름은 `docs/ARCHITECTURE.md` 참고.
- 메시지 형식은 `docs/UI_GUIDE.md` 를 따른다.
- 세션 간 이어받을 현재 상태(블로킹 이슈, TODO)는 `docs/PROGRESS.md` 에 기록되어 있다. 작업 시작 전 확인하라.

## 개발 프로세스
- CRITICAL: 오버엔지니어링 금지. 사용자 1명을 위한 MVP다. 명시되지 않은 기능/추상화/파일을 추가하지 마라.
- 외부 API를 호출하는 코드는 테스트에서 반드시 mock한다 (실제 네트워크 호출 금지).
- 매 응답 종료 시 Stop 훅이 `python -m pytest tests/` 를 자동 실행한다 (`.claude/settings.json`). 실패한 채로 끝내지 마라.
- 커밋 메시지는 conventional commits 형식 (feat:, fix:, docs:, refactor:, chore:).
- 반복 작업은 전용 스킬을 써라: 새 명령 추가 → `add-command`, 정류장/노선/방면 그룹 변경 → `update-stops`, 배포 전 점검 → `predeploy`, API 키 승인 후 실응답 검증 → `bus-api-verify`.

## 명령어
python -m pytest tests/   # 테스트
python -m src.bot         # 봇 실행 (로컬, env/.env 필요)

## 주의사항
- CRITICAL: `scripts/execute.py`(Harness 실행기, `/harness` 참고)는 `codex exec`를 비대화형으로 호출해 실제 API 과금이 발생한다. 사용자 확인 없이 실행하지 마라.
