# 진행 메모 (Progress Notes)

> 다른 환경에서 작업을 이어가기 위한 현재 상태 기록. 최신 항목을 맨 위에 추가한다.

## 2026-07-06

### 현재 상태
2026-06-26 이후 아래 커밋이 추가됨:
- `348a242` fix(bus_service): 도착 버스별 혼잡도 필드 분리 (congestion1/congestion2)
- `7f4555c` chore(stops): `stops.json`을 실제 정류장 ARS ID/노선으로 갱신 — 아래 "API 키 승인" 블로킹 중 "stops.json 미갱신" 부분은 해소됨
- `37a24bd` docs: CLAUDE.md에 TDD guard/Stop 훅 명시, 문서를 실제 구현에 맞게 갱신
- `d7845d3` feat(bot): 방면 그룹 도착정보 + TDD 가드 인프라, 시크릿 유출·크래시 수정
- `32120a9` feat(skills): 반복 개발 작업 4종 스킬화 (`add-command`, `update-stops`, `predeploy`, `bus-api-verify`)

### ⛔ 여전히 블로킹: 서울 버스 API 실응답 검증
`stops.json`은 실제 ARS ID로 갱신됐지만, `src/bus_service.py`는 여전히 실제 서울 버스 API를 한 번도 호출한 적 없다 (응답 필드명 `msgBody.itemList`/`rtNm`/`arrmsg1·2`/`congestion1·2`는 전부 가정/mock 기반). API 키 승인 후 `bus-api-verify` 스킬로 실응답 스키마를 검증할 것.

### 📌 정정: Railway는 이미 배포되어 있음
아래 2026-06-26 절 TODO의 "Railway 배포 — 미배포"는 더 이상 사실이 아니다. Railway 프로젝트 `bus-alarm-bot`의 `bus-alarm-worker` 서비스가 2026-07-01부터 SUCCESS 상태로 계속 가동 중(재시작/크래시 이력 없음). 배포 직후 `getUpdates 실패` 에러가 몇 차례 있었으나(Telegram 쪽 일시 장애로 추정) 이후 정상 동작 중이며, 폴링 실패 시 무한 재시도하던 버그는 이 세션에서 백오프(`_ERROR_BACKOFF_SECONDS`, `src/bot.py`)로 수정함.

## 2026-06-26

### 현재 상태
- 페이즈 `0-mvp` 완료 (프로젝트 셋업/설계 문서 → `bus-service` → `telegram-bot`), 단일 커밋 `cdf7219 feat: bus-alarm-bot MVP 초기 커밋`으로 스쿼시되어 저장소에 반영됨
- `serviceKey` 이중 인코딩 방지 픽스 포함 (`unquote`)
  - `requests`가 params를 재인코딩하므로, 이미 %-인코딩된 Encoding 키는 `unquote`로 한 번 풀어준다. Decoding 키는 no-op.
- 테스트: `python -m pytest tests/` → 15 passed
- working tree 깨끗함 (커밋 안 된 변경 없음)

### 저장소 / 원격
- `origin` = https://github.com/subjjang2/bus_alarm
- 작업 브랜치: `main`

### 다음 환경에서 이어받기
```bash
git fetch origin
git checkout main
git pull
python -m pytest tests/   # 동작 확인
```
> private repo이므로 해당 환경에서도 `subjjang2` 계정 인증 필요 (`gh auth login`).

### ⛔ 블로킹: 서울 버스 API 키 승인 대기 중
**현재 더 진행할 수 있는 실작업이 없다.** 코드(bus_service/bot/format)와 mock 테스트는 모두 완료됐고, 남은 작업은 전부 *승인된* 키를 전제로 한다. `env/.env`에 키 값은 채워져 있으나 **공공데이터포털 활용신청이 아직 미승인**이라 실호출 시 거부된다(`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`류).

step 0~2가 `completed`로 마킹된 것은 셋 다 코드+mock 작업이라 키 없이 끝낼 수 있었기 때문이다. "키가 있어야만 가능한 작업"은 애초에 step으로 만들어지지 않았다.

### 키 승인되면 할 일 (TODO — 승인 전까지 블로킹)
- [ ] **실제 API 응답 스키마 검증** — `src/bus_service.py`는 실제 서울 버스 API를 한 번도 호출한 적 없음. 응답 필드명(`msgBody.itemList`, `rtNm`, `arrmsg1/arrmsg2`, `congestion1/congestion2`)이 전부 가정/mock 기반. 특히 `getStationByUid`가 각 도착 버스별로 `congestion1`/`congestion2`를 실제로 따로 주는지 미검증. 실응답 받아 파싱이 맞는지 확인.
- [ ] **로컬 E2E 스모크** — `python -m src.bot` 실행 후 텔레그램에서 `/morning` `/evening` 보내 실데이터 왕복 확인.
- [ ] **Railway 배포** — `README.md`에 문서화됨, 미배포. 키는 Railway Variables에 입력(코드 하드코딩 금지). 키 승인 후에만 의미 있음.

> 승인 대비: 키가 들어오면 한 번에 실응답 스키마를 점검할 일회성 검증 스크립트를 `scripts/`에 준비해두면 좋다(코드 본체는 안 건드림).
