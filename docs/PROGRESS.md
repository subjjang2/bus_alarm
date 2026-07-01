# 진행 메모 (Progress Notes)

> 다른 환경에서 작업을 이어가기 위한 현재 상태 기록. 최신 항목을 맨 위에 추가한다.

## 2026-06-26

### 현재 상태
- **페이즈 `0-mvp` 완료 마킹됨** (`a1d33ca chore(0-mvp): mark phase completed`)
- step 0(프로젝트 셋업/설계 문서) → step 1(`bus-service`) → step 2(`telegram-bot`) 까지 진행 완료
- 마지막 작업: `serviceKey` 이중 인코딩 방지 픽스 (`e2080e8 fix(0-mvp): serviceKey 이중 인코딩 방지 (unquote)`)
  - `requests`가 params를 재인코딩하므로, 이미 %-인코딩된 Encoding 키는 `unquote`로 한 번 풀어준다. Decoding 키는 no-op.
- 테스트: `python -m pytest tests/` → 15 passed
- working tree 깨끗함 (커밋 안 된 변경 없음)

### 저장소 / 원격
- `origin` = https://github.com/subjjang2/harness_framework (private, 작업용)
- `upstream` = https://github.com/jha0313/harness_framework (원본, push 권한 없음)
- 작업 브랜치: `feat-0-mvp`

### 다음 환경에서 이어받기
```bash
git fetch origin
git checkout feat-0-mvp
git pull
python -m pytest tests/   # 동작 확인
```
> private repo이므로 해당 환경에서도 `subjjang2` 계정 인증 필요 (`gh auth login`).

### ⛔ 블로킹: 서울 버스 API 키 승인 대기 중
**현재 더 진행할 수 있는 실작업이 없다.** 코드(bus_service/bot/format)와 mock 테스트는 모두 완료됐고, 남은 작업은 전부 *승인된* 키를 전제로 한다. `env/.env`에 키 값은 채워져 있으나 **공공데이터포털 활용신청이 아직 미승인**이라 실호출 시 거부된다(`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`류).

step 0~2가 `completed`로 마킹된 것은 셋 다 코드+mock 작업이라 키 없이 끝낼 수 있었기 때문이다. "키가 있어야만 가능한 작업"은 애초에 step으로 만들어지지 않았다.

### 키 승인되면 할 일 (TODO — 승인 전까지 블로킹)
- [ ] **실제 API 응답 스키마 검증** — `src/bus_service.py`는 실제 서울 버스 API를 한 번도 호출한 적 없음. 응답 필드명(`msgBody.itemList`, `rtNm`, `arrmsg1/arrmsg2`, 혼잡도)이 전부 가정/mock 기반. 특히 `getStationByUid`가 혼잡도를 주는지 미검증 (`congestion`/오탈자 `congetion` 둘 다 방어 처리해둔 상태 = 실응답 미확인의 방증). 실응답 받아 파싱이 맞는지 확인.
- [ ] **로컬 E2E 스모크** — `python -m src.bot` 실행 후 텔레그램에서 `/morning` `/evening` 보내 실데이터 왕복 확인.
- [ ] **Railway 배포** — `README.md`에 문서화됨, 미배포. 키는 Railway Variables에 입력(코드 하드코딩 금지). 키 승인 후에만 의미 있음.

> 승인 대비: 키가 들어오면 한 번에 실응답 스키마를 점검할 일회성 검증 스크립트를 `scripts/`에 준비해두면 좋다(코드 본체는 안 건드림).
