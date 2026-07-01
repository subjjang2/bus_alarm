# 아키텍처

## 디렉토리 구조
```
src/
├── __init__.py
├── config.py        # env/.env + stops.json 로딩
├── bus_service.py    # 서울 버스도착정보 API 래퍼 — 외부 버스 API 호출은 여기서만
└── bot.py           # 텔레그램 폴링 루프 + 명령어 처리 + 메시지 포맷 + 진입점
tests/
├── __init__.py
├── test_bus_service.py
└── test_bot.py
stops.json            # 사용자 정류장 설정
env/.env(.example)    # API 키
requirements.txt
Procfile              # Railway worker: python -m src.bot
```

## 패턴
- 상태 없음(stateless). 매 명령마다 API 1회 호출 → 포맷 → 응답. DB/캐시 없음.
- 외부 의존성 격리: 서울 버스 API 호출은 `bus_service.py` 에만, 텔레그램 호출은 `bot.py` 에만.
- 순수 함수 분리: 메시지 포맷(`format_arrivals`)은 네트워크 없이 단독으로 테스트 가능하게 둔다.

## 데이터 흐름
```
사용자가 /morning 또는 /evening 전송
  → bot.py: stops.json에서 해당 시나리오의 ars_id, routes 조회
  → bus_service.get_arrivals(ars_id, routes, api_key): 서울 API 호출 → 도착정보+혼잡도 파싱 → routes로 필터
  → bot.format_arrivals(): 카드형 메시지 문자열 생성
  → 텔레그램 sendMessage 로 응답
```

## 외부 API
- **서울 버스도착정보**: 정류소 ARS ID 기준 도착정보 조회(getStationByUid 계열). 응답에서 노선번호(rtNm), 도착메시지(arrmsg1/arrmsg2), 혼잡도(congestion) 사용. 혼잡도는 제공되지 않는 버스도 있으며 그 경우 생략한다.
- **텔레그램 Bot API**: getUpdates(long polling) + sendMessage. 프레임워크 없이 `requests`로 호출.

## 배포
- Railway worker 프로세스로 폴링 봇 상시 실행. 인바운드 포트/웹훅 불필요.
- API 키는 Railway Variables(운영) / `env/.env`(로컬)에서 주입.

## 상태 관리
- 없음. 모든 요청은 무상태. 직전 응답을 기억하지 않는다.
