# Step 0: project-setup

## 읽어야 할 파일

먼저 아래 파일들을 읽고 프로젝트의 아키텍처와 설계 의도를 파악하라:

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/ADR.md`
- `docs/UI_GUIDE.md`
- `CLAUDE.md`
- 이미 존재하는 설정 파일: `env/.env.example`, `stops.json`

이 step은 파이썬 프로젝트 골격과 설정 로더만 만든다. 외부 API 호출 코드는 만들지 않는다.

## 작업

1. `requirements.txt` 생성. 의존성: `requests`, `python-dotenv`, `pytest`. (버전 핀은 자유, 최소 구성)
2. `Procfile` 생성: 한 줄 `worker: python -m src.bot`
3. 패키지 골격: `src/__init__.py`, `tests/__init__.py` (빈 파일)
4. `src/config.py` 구현:
   - `Settings` 데이터클래스: `seoul_bus_api_key: str`, `telegram_bot_token: str`, `telegram_chat_id: str`
   - `load_settings() -> Settings`: `env/.env` 가 있으면 `python-dotenv`로 로드한 뒤 환경변수에서 읽는다. 값이 없으면 빈 문자열을 채운다.
   - `load_stops(path: str = "stops.json") -> dict`: `stops.json`을 읽어 dict로 반환. 최상위에 `"morning"`/`"evening"` 키.
   - `get_scenario(stops: dict, name: str) -> dict`: `"morning"`|`"evening"` 시나리오 dict 반환. 없는 이름이면 `ValueError`.
5. 짧은 `README.md` 생성. 다음을 간단히 안내:
   - 설정: ARS ID는 정류장 표지판의 5자리 번호(또는 카카오버스에서 검색)로 확인해 `stops.json`에 기입. `routes`에는 내가 타는 버스 번호. API 키는 `env/.env`(`env/.env.example` 복사)에 입력.
   - 로컬 실행: `python -m src.bot`
   - Railway 배포: worker 프로세스로 실행, 키는 Railway Variables에 입력.

핵심 규칙(반드시 지킬 것):
- API 키를 코드에 하드코딩하지 마라. 반드시 `env/.env` 또는 환경변수에서만 읽어라. 이유: 키 유출 방지 + Railway Variables 주입과 호환.
- `src/config.py`는 import 만으로 예외를 던지면 안 된다. 이유: step1/step2가 키 없이도 모듈을 import해 테스트한다.
- `stops.json` 등 파일을 읽을 때 반드시 `open(..., encoding="utf-8")`을 명시하라. 이유: Windows 기본 인코딩(cp949)으로 열면 한글(label) 때문에 `UnicodeDecodeError`로 죽는다.

## Acceptance Criteria

```bash
pip install -r requirements.txt
python -c "from src.config import load_stops, get_scenario; s=load_stops(); get_scenario(s,'morning'); get_scenario(s,'evening'); print('ok')"
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - ARCHITECTURE.md 디렉토리 구조를 따르는가? (`src/`, `tests/`)
   - 이 step에서 외부 API 호출 코드를 만들지 않았는가? (설정 로더만)
   - API 키 하드코딩이 없는가?
3. 결과에 따라 `phases/0-mvp/index.json`의 step 0을 업데이트한다:
   - 성공 → `"status": "completed"`, `"summary": "산출물 한 줄 요약"`
   - 수정 3회 시도 후에도 실패 → `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 → `"status": "blocked"`, `"blocked_reason": "사유"` 후 즉시 중단

## 금지사항

- `src/bus_service.py`, `src/bot.py`를 만들지 마라. 이유: 각각 step1, step2의 범위다.
- `.env` 파서를 직접 구현하지 마라. 이유: `python-dotenv`로 충분, 불필요한 코드.
- `stops.json`, `env/.env.example`의 내용을 바꾸지 마라. 이유: 이미 확정된 설정 스키마다.
- 기존 테스트(`scripts/test_execute.py`)를 깨뜨리지 마라.
