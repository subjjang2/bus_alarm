"""텔레그램 폴링 봇 + 메시지 포맷 + 진입점.

텔레그램 HTTP 호출은 이 모듈 안에서만 한다 (의존성 격리).
`format_arrivals` 는 네트워크 없는 순수 함수로 두어 키 없이 테스트 가능하다.
토큰/키는 config 에서만 읽는다 (하드코딩 금지).
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from src.bus_service import Arrival, BusEta, get_arrivals
from src.config import get_scenario, load_settings, load_stops

_KST = timezone(timedelta(hours=9))

# 혼잡도 라벨 → 색 점 이모지 (docs/UI_GUIDE.md 매핑 표)
_CONGESTION_EMOJI = {"여유": "🟢", "보통": "🟡", "혼잡": "🔴"}
# 혼잡도 라벨 → 정렬 우선순위(낮을수록 우선). None/기타 혼잡도는 맨 뒤.
_CONGESTION_RANK = {"여유": 0, "보통": 1, "혼잡": 2}
# 방면 그룹 하나당 보여줄 최대 도착 버스 수
_MAX_PER_GROUP = 3

# 상시 버튼 키보드 (매 응답마다 붙여 항상 노출)
_BTN_MORNING = "🌅 아침"
_BTN_EVENING = "🌆 저녁"
_KEYBOARD = {
    "keyboard": [[{"text": _BTN_MORNING}, {"text": _BTN_EVENING}]],
    "resize_keyboard": True,
    "is_persistent": True,  # 클라이언트별 지원 편차 있음(best-effort)
}

_HELP = (
    "🚌 버스 알리미\n"
    "\n"
    "/morning — 아침 정류장 도착정보\n"
    "/evening — 저녁 정류장 도착정보\n"
    "\n"
    "아래 버튼으로도 바로 조회할 수 있어요."
)


def _format_eta(eta: BusEta) -> str:
    """BusEta 1건을 카드 안의 한 줄로. 없는 정보는 우아하게 생략한다."""
    parts: List[str] = []
    # 핵심(도착 N분)이 먼저. 분 파싱 실패 시 원본 메시지로 폴백.
    if eta.minutes is not None:
        parts.append(f"⏱ {eta.minutes}분")
    else:
        parts.append(eta.raw_msg)
    if eta.congestion:
        emoji = _CONGESTION_EMOJI.get(eta.congestion, "")
        parts.append(f"{emoji} {eta.congestion}".strip())
    if eta.stations_away is not None:
        parts.append(f"{eta.stations_away}정거장 전")
    # 텔레그램은 고정폭 폰트가 아니라 공백만으로는 칼럼이 안 맞는다.
    # 자릿수와 무관하게 항상 읽히도록 구분자로 연결한다.
    return " · " + " · ".join(parts)


def _sort_key(eta: BusEta):
    """정렬 우선순위: 도착 빠른 순이 최우선, 같은 분이면 혼잡도 낮은 순.

    분 파싱 실패 시 원본 메시지에 "곧"이 있으면 가장 빠른 것으로,
    그 외(운행종료 등)는 맨 뒤로 보낸다.
    """
    if eta.minutes is not None:
        mins = eta.minutes
    elif "곧" in eta.raw_msg:
        mins = 0
    else:
        mins = 9999
    return (mins, _CONGESTION_RANK.get(eta.congestion, 3))


def format_arrivals(
    label: str, groups: List[dict], arrivals: List[Arrival], *, evening: bool = False
) -> str:
    """방면 그룹별 도착순 통합 리스트 메시지를 만든다 (docs/UI_GUIDE.md).

    네트워크 없는 순수 함수. 헤더 이모지: 아침 🌅 / 저녁 🌆.
    각 그룹은 노선당 가장 빨리 오는 버스 1대만 후보로 삼고,
    그중 도착 빠른 순 → 동일 분이면 혼잡도 낮은 순으로 정렬해
    상위 `_MAX_PER_GROUP`개 노선만 보여준다(같은 노선이 여러 줄을
    차지해 다른 노선을 밀어내지 않도록).
    """
    header_emoji = "🌆" if evening else "🌅"
    blocks: List[str] = [f"{header_emoji} {label}"]

    by_route = {a.route: a for a in arrivals}
    any_bus = False

    for group in groups:
        group_lines: List[str] = []
        if group.get("label"):
            group_lines.append(f"🚏 {group['label']}")

        pairs = [
            (route, min(etas, key=_sort_key))
            for route in group["routes"]
            if (etas := by_route.get(route, Arrival(route=route, etas=[])).etas)
        ]
        pairs.sort(key=lambda p: _sort_key(p[1]))
        pairs = pairs[:_MAX_PER_GROUP]

        if pairs:
            any_bus = True
            for route, eta in pairs:
                group_lines.append(f"🚌 {route}번" + _format_eta(eta))
        else:
            group_lines.append("도착 예정 버스가 없어요 🚏")

        blocks.append("\n".join(group_lines))

    if not any_bus:
        blocks = [f"{header_emoji} {label}", "표시할 버스가 없어요 🚏"]

    blocks.append(f"🕘 {datetime.now(_KST).strftime('%H:%M')} 기준")
    return "\n\n".join(blocks)


def build_message(scenario_name: str) -> str:
    """설정을 읽어 해당 시나리오의 도착정보 메시지를 만든다.

    scenario_name: "morning" | "evening".
    버스 조회가 실패해도 앱이 죽지 않도록 한 줄 에러 메시지를 반환한다.
    """
    evening = scenario_name == "evening"
    try:
        settings = load_settings()
        scenario = get_scenario(load_stops(), scenario_name)
        groups = scenario["groups"]
        all_routes = [route for group in groups for route in group["routes"]]
        arrivals = get_arrivals(
            scenario["ars_id"],
            all_routes,
            settings.seoul_bus_api_key,
        )
    except Exception as exc:  # 사용자에게 보여줄 한 줄 안내로 강등
        # 예외 문자열에는 buses API의 serviceKey가 담긴 요청 URL이 그대로
        # 들어있을 수 있다(requests.HTTPError 등). 채팅/로그 어디에도 원문을
        # 남기지 않고 예외 종류만 알린다.
        print(f"build_message 실패({scenario_name}): {type(exc).__name__}", file=sys.stderr)
        return f"⚠️ 버스 정보를 가져오지 못했어요 ({type(exc).__name__})"
    return format_arrivals(scenario["label"], groups, arrivals, evening=evening)


def _handle_command(text: str) -> Optional[str]:
    """텔레그램 텍스트를 명령으로 처리. 모르는 입력이면 None(무응답)."""
    if not text:
        return None
    # 상시 키보드 버튼(라벨 전체가 메시지로 옴)은 첫 토큰 분리 전 원문으로 비교해야 한다.
    # "🌅 아침" 을 split()[0] 하면 "🌅" 만 남아 아래 슬래시 분기와 매칭되지 않기 때문.
    stripped = text.strip()
    if stripped in (_BTN_MORNING, "아침"):
        return build_message("morning")
    if stripped in (_BTN_EVENING, "저녁"):
        return build_message("evening")
    # "/morning@my_bot 어쩌고" → "/morning"
    cmd = text.split()[0].split("@")[0].lower()
    if cmd == "/morning":
        return build_message("morning")
    if cmd == "/evening":
        return build_message("evening")
    if cmd in ("/start", "/help"):
        return _HELP
    return None


def _send_message(token: str, chat_id: str, text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(_KEYBOARD),
        },
    )


def _poll_once(token: str, base: str, offset: Optional[int], allowed_chat: str) -> Optional[int]:
    """getUpdates 1회 호출 + 받은 업데이트 처리. 다음에 쓸 offset을 반환한다.

    네트워크 예외(getUpdates/sendMessage 모두)는 삼키고 종류만 로그로 남긴다.
    폴링 루프가 일시적 오류로 죽지 않도록 하기 위함이며, 예외 문자열에는
    토큰이 담긴 요청 URL이 들어있을 수 있어 종류 이상은 남기지 않는다.
    """
    try:
        resp = requests.get(
            f"{base}/getUpdates", params={"timeout": 30, "offset": offset}
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"getUpdates 실패: {type(exc).__name__}", file=sys.stderr)
        return offset

    for update in resp.json().get("result", []):
        offset = update["update_id"] + 1
        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
        chat_id = str(message.get("chat", {}).get("id", ""))
        if allowed_chat and chat_id != allowed_chat:
            continue
        reply = _handle_command((message.get("text") or "").strip())
        if reply is None:
            continue
        try:
            _send_message(token, chat_id, reply)
        except requests.RequestException as exc:
            print(f"sendMessage 실패: {type(exc).__name__}", file=sys.stderr)

    return offset


def run() -> None:
    """텔레그램 getUpdates long polling 루프."""
    settings = load_settings()
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN 가 설정되지 않았습니다 (env/.env).")
    allowed_chat = settings.telegram_chat_id

    base = f"https://api.telegram.org/bot{token}"
    offset = None
    while True:
        offset = _poll_once(token, base, offset, allowed_chat)


if __name__ == "__main__":
    run()
