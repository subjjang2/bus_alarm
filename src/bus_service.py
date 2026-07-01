"""서울 버스도착정보 API 래퍼.

외부 버스 API HTTP 호출은 이 모듈 안에서만 한다 (의존성 격리).
정류소 ARS ID 기준 도착정보(getStationByUid 계열)를 조회해
노선번호·도착시간·정거장 수·혼잡도를 파싱한다.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import unquote

import requests

# 서울 버스도착정보: 정류소 ARS 기준 도착정보 조회
API_URL = "http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid"

# 혼잡도 코드 → 라벨 (docs/UI_GUIDE.md 매핑 표). 그 외/없음/0 → None
_CONGESTION = {"3": "여유", "4": "보통", "5": "혼잡"}

_MINUTES_RE = re.compile(r"(\d+)\s*분")
_STATIONS_RE = re.compile(r"(\d+)\s*번째\s*전")


@dataclass
class BusEta:
    minutes: Optional[int]          # 도착까지 남은 분
    stations_away: Optional[int]    # "N번째 전" 정거장 수
    congestion: Optional[str]       # "여유" | "보통" | "혼잡" | None
    raw_msg: str                    # 원본 도착메시지 (파싱 실패 시 폴백용)


@dataclass
class Arrival:
    route: str                      # 노선번호 "6516"
    etas: List[BusEta]              # 도착 예정 버스 최대 2대


def _map_congestion(value) -> Optional[str]:
    """혼잡도 코드를 라벨로. 없거나 매핑 밖이면 None."""
    if value is None:
        return None
    return _CONGESTION.get(str(value).strip())


def _parse_int(pattern: re.Pattern, text: str) -> Optional[int]:
    if not text:
        return None
    m = pattern.search(text)
    return int(m.group(1)) if m else None


def _build_eta(arrmsg: Optional[str], congestion) -> Optional[BusEta]:
    """도착메시지 1건을 BusEta로. 메시지가 비어 있으면 None."""
    if not arrmsg:
        return None
    raw = str(arrmsg).strip()
    if not raw:
        return None
    return BusEta(
        minutes=_parse_int(_MINUTES_RE, raw),
        stations_away=_parse_int(_STATIONS_RE, raw),
        congestion=_map_congestion(congestion),
        raw_msg=raw,
    )


def _extract_items(payload: dict) -> List[dict]:
    """API 응답에서 itemList 추출. 단일 dict/None 모두 견딘다."""
    body = (payload or {}).get("msgBody") or {}
    items = body.get("itemList")
    if items is None:
        return []
    if isinstance(items, dict):
        return [items]
    return list(items)


def _get_congestion(item: dict, seq: int):
    """도착 버스 seq(1|2)번째의 혼잡도 필드(congestion1/congestion2)."""
    return item.get(f"congestion{seq}")


def get_arrivals(
    ars_id: str,
    routes: Optional[List[str]],
    api_key: str,
    *,
    client=requests,
) -> List[Arrival]:
    """ars_id 정류소의 도착정보를 조회해 노선별 Arrival 리스트로 반환한다.

    routes 가 주어지면 그 노선만 routes 순서대로, 없으면 응답 순서대로 반환한다.
    각 노선은 도착 예정 버스 최대 2대(arrmsg1, arrmsg2)를 담는다.
    네트워크/HTTP 예외는 삼키지 않는다 (호출자가 처리).
    """
    resp = client.get(
        API_URL,
        # 이미 %-인코딩된 Encoding 키면 풀어준다(requests가 params를 다시 인코딩하므로).
        # Decoding 키엔 %가 없어 no-op → Encoding/Decoding 두 형태 모두 동작.
        params={"serviceKey": unquote(api_key), "arsId": ars_id, "resultType": "json"},
    )
    resp.raise_for_status()
    payload = resp.json()

    # 노선번호 → Arrival (응답 순서 유지)
    by_route: "dict[str, Arrival]" = {}
    for item in _extract_items(payload):
        route = item.get("rtNm")
        if not route:
            continue
        route = str(route)
        etas = [
            eta
            for eta in (
                _build_eta(item.get("arrmsg1"), _get_congestion(item, 1)),
                _build_eta(item.get("arrmsg2"), _get_congestion(item, 2)),
            )
            if eta is not None
        ]
        if route not in by_route:
            by_route[route] = Arrival(route=route, etas=etas)

    if routes:
        return [by_route[r] for r in routes if r in by_route]
    return list(by_route.values())
