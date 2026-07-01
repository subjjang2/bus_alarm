"""bot.format_arrivals 단위 테스트. 순수 함수만 검증(텔레그램/버스 API 호출 없음)."""

from src.bot import format_arrivals
from src.bus_service import Arrival, BusEta


def _eta(minutes=None, stations_away=None, congestion=None, raw_msg=""):
    return BusEta(
        minutes=minutes,
        stations_away=stations_away,
        congestion=congestion,
        raw_msg=raw_msg,
    )


def test_includes_route_minutes_and_congestion_emoji():
    arrivals = [
        Arrival(
            route="6516",
            etas=[
                _eta(3, 2, "여유", "3분후[2번째 전]"),
                _eta(12, 6, "보통", "12분후[6번째 전]"),
            ],
        ),
        Arrival(route="660", etas=[_eta(7, 4, "혼잡", "7분후[4번째 전]")]),
    ]
    msg = format_arrivals("등촌역 → 당산역", arrivals)

    assert "🚌 6516번" in msg
    assert "🚌 660번" in msg
    assert "⏱ 3분" in msg
    assert "⏱ 12분" in msg
    assert "🟢 여유" in msg
    assert "🟡 보통" in msg
    assert "🔴 혼잡" in msg
    assert "2정거장 전" in msg


def test_congestion_none_omits_emoji():
    arrivals = [Arrival(route="660", etas=[_eta(21, None, None, "21분후")])]
    msg = format_arrivals("등촌역 → 당산역", arrivals)

    assert "⏱ 21분" in msg
    # 혼잡도 None → 색 점 이모지 없음
    assert "🟢" not in msg
    assert "🟡" not in msg
    assert "🔴" not in msg


def test_morning_vs_evening_header_emoji():
    arrivals = [Arrival(route="6516", etas=[_eta(3, 2, "여유", "3분후[2번째 전]")])]

    morning = format_arrivals("등촌역 → 당산역", arrivals, evening=False)
    evening = format_arrivals("당산역 → 등촌역", arrivals, evening=True)

    assert morning.startswith("🌅")
    assert evening.startswith("🌆")


def test_raw_msg_fallback_when_minutes_missing():
    # 분 파싱 실패 → 원본 도착메시지 그대로 표시
    arrivals = [Arrival(route="6516", etas=[_eta(None, None, None, "곧 도착")])]
    msg = format_arrivals("등촌역 → 당산역", arrivals)

    assert "곧 도착" in msg
    assert "⏱" not in msg


def test_no_bus_message():
    msg = format_arrivals("등촌역 → 당산역", [])
    assert "표시할 버스가 없어요" in msg

    # etas 가 모두 비어도 안내 한 줄
    msg2 = format_arrivals("등촌역 → 당산역", [Arrival(route="6516", etas=[])])
    assert "표시할 버스가 없어요" in msg2
