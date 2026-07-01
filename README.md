# bus-alarm-bot

텔레그램 명령어 한 번으로 내가 타는 정류장의 버스 도착시간과 혼잡도를 확인하는 봇.
`/morning`, `/evening` 두 명령어만 있는 1인용 MVP.

## 설정

1. **정류장(`stops.json`)** — `morning`/`evening` 시나리오를 채운다.
   - `ars_id`: 출발 정류장 표지판의 5자리 ARS 번호. 카카오버스 앱에서 정류장을 검색해 확인할 수 있다.
   - `label`: 헤더에 표시할 텍스트 (예: `"등촌역 → 당산역"`).
   - `groups`: 방면별 그룹 배열. 각 그룹은 `label`(방면 이름, 빈 문자열이면 생략 가능)과 `routes`(그 정류장에서 내가 타는 버스 번호 목록, 예: `["6516", "660"]`)로 구성된다. 그룹당 최대 3개 노선까지 표시된다.
   - 도착 정류장 ID는 입력하지 않는다 (도착시간·혼잡도는 출발 정류장 기준).

2. **API 키(`env/.env`)** — `env/.env.example`을 `env/.env`로 복사한 뒤 채운다.
   - `SEOUL_BUS_API_KEY`: 서울 버스도착정보 API 키.
   - `TELEGRAM_BOT_TOKEN`: @BotFather 에서 발급한 봇 토큰.
   - `TELEGRAM_CHAT_ID`: (선택) 이 chat_id 에서 온 명령만 응답. 비우면 모두 응답.

## 로컬 실행

```bash
pip install -r requirements.txt
python -m src.bot
```

## Railway 배포

worker 프로세스로 상시 실행한다 (long-polling, 인바운드 포트 불필요).
API 키는 코드가 아닌 Railway Variables 에 입력한다.

## 테스트

```bash
python -m pytest tests/
```
