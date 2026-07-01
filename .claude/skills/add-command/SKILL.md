---
name: add-command
description: >-
  새 텔레그램 봇 명령/시나리오를 test-first로 추가한다. tdd_guard 훅 때문에
  테스트를 먼저 쓰지 않으면 src/bot.py 편집 자체가 차단된다는 점과, 명령
  하나가 라우팅·키보드·헬프텍스트·stops.json·UI_GUIDE 5곳에 걸친다는 점을
  놓치지 않도록 절차를 강제한다. "새 명령 추가", "add command", "버튼 추가",
  "/X 명령 만들어줘", "새 시나리오 추가" 등에 트리거.
---

# 새 봇 명령 추가 (test-first)

이 프로젝트는 PreToolUse 훅(`scripts/hooks/tdd_guard.py`)이 `tests/test_<module>.py`
없이 `src/*.py` 편집을 차단한다. 순서를 어기면 Edit/Write 자체가 실패하니
**반드시 아래 순서대로** 진행한다.

## 절차

1. **테스트 먼저** — `tests/test_bot.py`에 새 명령의 `_handle_command` 케이스를
   추가하고 저장한다. 기존 `/morning`·`/evening` 테스트(같은 파일)를 템플릿으로
   삼는다. 이 커밋이 있어야 이후 `src/bot.py` 편집이 훅을 통과한다.
2. **라우팅** — `src/bot.py:151` `_handle_command()`에 분기를 추가한다.
   `bot.py:163-170`의 `/morning`, `/evening`, `/start`, `/help` 패턴을 따른다.
3. **버튼 명령이면** — `_BTN_*` 상수(`bot.py:28-29`), `_KEYBOARD`(`bot.py:30`)에
   추가한다. **주의**: 버튼 라벨(예: "🌅 아침")은 텔레그램에서 원문 그대로
   메시지로 온다. `text.split()[0]`으로 자르면 이모지만 남아 매칭이 깨진다
   (`bot.py:155-161` 참고). 반드시 `stripped` 원문과 직접 비교한다.
4. **시나리오형 명령이면** — `stops.json`에 새 시나리오를 추가하고
   (`update-stops` 스킬로 검증), `build_message()`(`bot.py:125`)를 재사용한다.
   출력 포맷은 `docs/UI_GUIDE.md`를 따른다 — 새 포맷을 즉흥으로 만들지 않는다.
5. **헬프 텍스트** — `_HELP`(`bot.py:36`)를 갱신해 새 명령을 안내한다.
6. **검증** — `python -m pytest tests/`. (Stop 훅이 턴 종료 시 자동 실행하지만
   중간에 직접 돌려 빠르게 피드백을 받는다.)

## 금지 사항

- **ADR-002 위반 금지**: 도착 정류장 ID를 입력받거나 경로 탐색을 구현하지
  않는다. 출발 정류장(`ars_id`) 기준만 허용된다.
- **예외 문자열 노출 금지**: 새 명령 핸들러에서 예외를 사용자/로그에 보여줄
  때 `str(exc)`를 쓰지 않는다. 버스 API `serviceKey`나 텔레그램 토큰이 요청
  URL에 담겨 `requests.HTTPError` 문자열에 그대로 노출될 수 있다
  (`bot.py:142-147` 참고). `type(exc).__name__`만 노출한다.
- **오버엔지니어링 금지**: 이 프로젝트는 1인용 MVP다. 프레임워크·추상화
  레이어를 새로 만들지 말고 기존 if/elif 라우팅 패턴을 그대로 따른다.
