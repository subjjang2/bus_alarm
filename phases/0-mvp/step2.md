# Step 2: telegram-bot

## 읽어야 할 파일

먼저 아래 파일들을 읽고 설계 의도를 파악하라:

- `docs/UI_GUIDE.md` (메시지 형식 — 반드시 그대로 준수)
- `docs/ARCHITECTURE.md`, `docs/PRD.md`
- `src/config.py`, `src/bus_service.py` (이전 step 산출물 — 시그니처 그대로 사용)
- `stops.json`, `env/.env.example`, `Procfile`

이전 step에서 만들어진 `Settings`, `load_settings`, `load_stops`, `get_scenario`, `get_arrivals`, `Arrival`, `BusEta`를 그대로 활용하라.

## 작업

`src/bot.py` 구현: 텔레그램 폴링 봇 + 메시지 포맷.

함수 (시그니처):

```python
def format_arrivals(label: str, arrivals: List[Arrival], *, evening: bool = False) -> str:
    ...  # UI_GUIDE.md의 노선별 카드형 형식. 네트워크 없는 순수 함수.

def build_message(scenario_name: str) -> str:
    ...  # 설정 로드 → get_arrivals 호출 → format_arrivals. 시나리오: "morning"|"evening".

def run() -> None:
    ...  # 텔레그램 getUpdates long polling 루프.
```

동작:
- `format_arrivals`: UI_GUIDE.md 형식을 그대로 따른다. 🟢🟡🔴 혼잡도, ⏱ 분, 정거장 수. 혼잡도 None이면 그 칸 생략. minutes/stations 없으면 `raw_msg` 사용. 표시할 버스 없으면 안내 한 줄. 헤더 이모지: `evening=False`면 🌅, True면 🌆.
- `build_message`: `load_settings()`, `load_stops()`로 설정을 읽고, 해당 시나리오의 `ars_id`/`routes`로 `get_arrivals` 호출, `format_arrivals`로 문자열 생성. `evening`은 `scenario_name == "evening"`. `get_arrivals`가 예외를 던지면 잡아서 사용자에게 보여줄 한 줄 에러 메시지를 반환(앱이 죽지 않게).
- `run`: 텔레그램 getUpdates long polling 루프(`requests` 사용). 명령 처리 — `"/morning"`→`build_message("morning")`, `"/evening"`→`build_message("evening")`, `"/start"`|`"/help"`→ 두 명령을 설명하는 안내. `TELEGRAM_CHAT_ID`가 설정돼 있으면 그 chat에서 온 메시지에만 응답. 응답은 sendMessage로 전송.
- `python -m src.bot`로 실행되도록 `__main__` 진입점에서 `run()` 호출.

핵심 규칙(반드시 지킬 것):
- 텔레그램 HTTP 호출은 이 모듈에서만. 이유: 의존성 격리(CLAUDE.md CRITICAL).
- `format_arrivals`는 네트워크 없는 순수 함수로 유지한다. 이유: 키 없이 테스트해야 한다.
- 토큰/키는 `config`에서만 읽어라. 하드코딩 금지.

테스트 `tests/test_bot.py`:
- `format_arrivals`를 샘플 `Arrival` 리스트로 검증: 노선번호·분·혼잡도 이모지(🟢/🟡/🔴) 포함, 혼잡도 None인 항목은 이모지 없음, 아침/저녁 헤더 이모지 구분.
- 실제 텔레그램/버스 API 호출 금지(순수 함수만 테스트).

## Acceptance Criteria

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
python -c "import src.bot"
```

## 검증 절차

1. 위 AC 커맨드를 실행한다 (`tests/` 전체가 통과해야 한다).
2. 아키텍처 체크리스트:
   - 텔레그램 호출이 `bot.py` 안에만 있는가?
   - 메시지 출력이 UI_GUIDE.md 형식과 일치하는가?
   - `format_arrivals`가 순수 함수인가(네트워크 없음)?
3. 결과에 따라 `phases/0-mvp/index.json`의 step 2를 업데이트한다 (completed/error/blocked + 해당 필드).

참고: 라이브 봇 실행(실제 키로 폴링)은 AC에 넣지 않는다. API 키는 사용자가 `env/.env`(로컬) 또는 Railway Variables(운영)에 넣는 설정 단계이며, 이는 blocked 사유가 아니다.

## 금지사항

- `python-telegram-bot` 등 텔레그램 프레임워크를 추가하지 마라. 이유: ADR-003, 명령 2개에 과함. `requests`로 충분.
- 정해진 시간 자동 푸시/스케줄러를 만들지 마라. 이유: MVP 제외(PRD). on-demand 명령어만.
- 라이브 봇 실행을 AC로 만들지 마라(키 필요). 대신 순수 함수 테스트로 검증.
- `src/config.py`, `src/bus_service.py`의 시그니처를 바꾸지 마라. 이유: 이전 step에서 확정됨.
- 기존 테스트를 깨뜨리지 마라.
