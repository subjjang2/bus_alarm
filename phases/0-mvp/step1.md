# Step 1: bus-service

## 읽어야 할 파일

먼저 아래 파일들을 읽고 설계 의도를 파악하라:

- `docs/ARCHITECTURE.md` (외부 API 섹션)
- `docs/ADR.md` (ADR-001, ADR-002)
- `docs/UI_GUIDE.md` (혼잡도 매핑 표)
- `src/config.py` (step 0 산출물 — 일관성 유지)
- `stops.json`

이전 step에서 만들어진 코드를 꼼꼼히 읽고 작업하라.

## 작업

`src/bus_service.py` 에 서울 버스도착정보 API 래퍼를 구현한다.

데이터 모델 (시그니처):

```python
@dataclass
class BusEta:
    minutes: Optional[int]        # 도착까지 남은 분
    stations_away: Optional[int]   # "N번째 전" 정거장 수
    congestion: Optional[str]      # "여유" | "보통" | "혼잡" | None
    raw_msg: str                   # 원본 도착메시지 (파싱 실패 시 폴백용)

@dataclass
class Arrival:
    route: str                     # 노선번호 "6516"
    etas: List[BusEta]             # 도착 예정 버스 최대 2대
```

함수 (시그니처):

```python
def get_arrivals(ars_id: str, routes: Optional[List[str]], api_key: str, *, client=requests) -> List[Arrival]:
    ...
```

동작:
- 서울 버스도착정보 API를 `ars_id`로 호출한다 (정류소 ARS 기준 도착정보 조회, getStationByUid 계열, `resultType=json` 권장). HTTP 호출은 `client` 인자로 주입받아 테스트에서 mock 가능하게 하라.
- 응답에서 각 버스의 노선번호(rtNm), 도착메시지(arrmsg1, arrmsg2), 혼잡도(congestion)를 읽는다.
- 혼잡도 코드 매핑: `3→"여유"`, `4→"보통"`, `5→"혼잡"`, 그 외/없음/`0` → `None`.
- `arrmsg`에서 분과 "N번째 전"(정거장 수)을 파싱해 `minutes`, `stations_away`에 넣는다. 파싱 실패해도 `raw_msg`에 원문을 보존하라.
- `routes`가 주어지면 그 노선번호만, **routes의 순서를 유지**해 반환한다. `routes`가 None이거나 비면 응답에 온 전체를 반환한다.
- 각 노선의 `Arrival.etas`에는 도착 예정 버스를 최대 2대(arrmsg1, arrmsg2) 담는다.

핵심 규칙(반드시 지킬 것):
- 외부 HTTP 호출은 이 모듈 안에서만 한다. 이유: 의존성 격리(ARCHITECTURE / CLAUDE.md CRITICAL).
- 네트워크/HTTP 예외를 이 함수에서 삼키지 마라(호출자가 처리). 단, 파싱 단계의 누락 필드는 `None`으로 견뎌라. 이유: 혼잡도 등은 선택적 필드라 없을 수 있다.
- 참고: 서울 API는 혼잡도 필드명이 `congestion` 또는 `congetion`(API 오탈자)으로 올 수 있고, 일부 버스만 제공한다. 실제 필드명은 공식 스펙으로 확인하되, 없으면 `None`으로 처리하라.

테스트 `tests/test_bus_service.py`:
- 실제 네트워크를 호출하지 마라. `client`를 mock으로 주입해 샘플 응답(JSON dict)을 반환시켜라.
- 검증: (1) routes 필터링과 순서, (2) 혼잡도 코드→라벨 매핑 및 미제공 시 None, (3) arrmsg 파싱(minutes/stations_away), (4) 노선당 최대 2 etas.

## Acceptance Criteria

```bash
python -m pytest tests/test_bus_service.py -q
python -c "import src.bus_service"
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트:
   - 외부 HTTP 호출이 `bus_service.py` 안에만 있는가?
   - 혼잡도 매핑이 UI_GUIDE.md 표와 일치하는가?
   - 테스트가 실제 API를 호출하지 않고 mock을 쓰는가?
3. 결과에 따라 `phases/0-mvp/index.json`의 step 1을 업데이트한다 (completed/error/blocked + 해당 필드).

## 금지사항

- `src/bot.py`나 텔레그램 관련 코드를 만들지 마라. 이유: step2 범위.
- 테스트에서 실제 서울 API를 호출하지 마라. 이유: API 키 필요 + 네트워크 의존. 반드시 mock.
- 응답에 선택적 필드가 없다고 예외로 죽지 마라. 이유: 혼잡도/정거장 수는 없을 수 있다.
- 기존 테스트를 깨뜨리지 마라.
