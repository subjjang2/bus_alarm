"""텔레그램 폴링 봇 + 메시지 포맷 + 진입점.

텔레그램 HTTP 호출은 이 모듈 안에서만 한다 (의존성 격리).
`format_arrivals` 는 네트워크 없는 순수 함수로 두어 키 없이 테스트 가능하다.
토큰/키는 config 에서만 읽는다 (하드코딩 금지).
"""

from datetime import datetime
from typing import List, Optional

import requests

from src.bus_service import Arrival, BusEta, get_arrivals
from src.config import get_scenario, load_settings, load_stops

# 혼잡도 라벨 → 색 점 이모지 (docs/UI_GUIDE.md 매핑 표)
_CONGESTION_EMOJI = {"여유": "🟢", "보통": "🟡", "혼잡": "🔴"}

_HELP = (
    "🚌 버스 알리미\n"
    "\n"
    "/morning — 아침 정류장 도착정보\n"
    "/evening — 저녁 정류장 도착정보"
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
    return "   " + "   ".join(parts)


def format_arrivals(
    label: str, arrivals: List[Arrival], *, evening: bool = False
) -> str:
    """노선별 카드형 메시지 문자열을 만든다 (docs/UI_GUIDE.md).

    네트워크 없는 순수 함수. 헤더 이모지: 아침 🌅 / 저녁 🌆.
    """
    header_emoji = "🌆" if evening else "🌅"
    blocks: List[str] = [f"{header_emoji} {label}"]

    cards = [a for a in arrivals if a.etas]
    if not cards:
        blocks.append("표시할 버스가 없어요 🚏")
        return "\n\n".join(blocks)

    for arrival in cards:
        card_lines = [f"🚌 {arrival.route}번"]
        card_lines += [_format_eta(eta) for eta in arrival.etas]
        blocks.append("\n".join(card_lines))

    blocks.append(f"🕘 {datetime.now().strftime('%H:%M')} 기준")
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
        arrivals = get_arrivals(
            scenario["ars_id"],
            scenario.get("routes"),
            settings.seoul_bus_api_key,
        )
    except Exception as exc:  # 사용자에게 보여줄 한 줄 안내로 강등
        return f"⚠️ 버스 정보를 가져오지 못했어요: {exc}"
    return format_arrivals(scenario["label"], arrivals, evening=evening)


def _handle_command(text: str) -> Optional[str]:
    """텔레그램 텍스트를 명령으로 처리. 모르는 입력이면 None(무응답)."""
    if not text:
        return None
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
        data={"chat_id": chat_id, "text": text},
    )


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
        resp = requests.get(
            f"{base}/getUpdates", params={"timeout": 30, "offset": offset}
        )
        resp.raise_for_status()
        for update in resp.json().get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue
            chat_id = str(message.get("chat", {}).get("id", ""))
            if allowed_chat and chat_id != allowed_chat:
                continue
            reply = _handle_command((message.get("text") or "").strip())
            if reply is not None:
                _send_message(token, chat_id, reply)


if __name__ == "__main__":
    run()
