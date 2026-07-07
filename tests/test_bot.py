"""bot.format_arrivals / _handle_command 단위 테스트. 텔레그램/버스 API 호출 없음."""

import re
from datetime import timedelta

import requests

import src.bot as bot
from src.bot import _handle_command, format_arrivals
from src.bus_service import Arrival, BusEta


def _eta(minutes=None, stations_away=None, congestion=None, raw_msg=""):
    return BusEta(
        minutes=minutes,
        stations_away=stations_away,
        congestion=congestion,
        raw_msg=raw_msg,
    )


def _single_group(routes):
    return [{"label": "", "routes": routes}]


def test_includes_route_minutes_and_congestion_emoji():
    arrivals = [
        Arrival(
            route="6516",
            etas=[
                _eta(3, 2, "여유", "3분후[2번째 전]"),
            ],
        ),
        Arrival(route="660", etas=[_eta(7, 4, "혼잡", "7분후[4번째 전]")]),
    ]
    msg = format_arrivals(
        "등촌역 → 당산역", _single_group(["6516", "660"]), arrivals
    )

    assert "🚌 6516번" in msg
    assert "🚌 660번" in msg
    assert "⏱ 3분" in msg
    assert "🟢 여유" in msg
    assert "🔴 혼잡" in msg
    assert "2정거장 전" in msg


def test_congestion_none_omits_emoji():
    arrivals = [Arrival(route="660", etas=[_eta(21, None, None, "21분후")])]
    msg = format_arrivals("등촌역 → 당산역", _single_group(["660"]), arrivals)

    assert "⏱ 21분" in msg
    # 혼잡도 None → 색 점 이모지 없음
    assert "🟢" not in msg
    assert "🟡" not in msg
    assert "🔴" not in msg


def test_morning_vs_evening_header_emoji():
    arrivals = [Arrival(route="6516", etas=[_eta(3, 2, "여유", "3분후[2번째 전]")])]
    groups = _single_group(["6516"])

    morning = format_arrivals("등촌역 → 당산역", groups, arrivals, evening=False)
    evening = format_arrivals("당산역 → 등촌역", groups, arrivals, evening=True)

    assert morning.startswith("🌅")
    assert evening.startswith("🌆")


def test_raw_msg_fallback_when_minutes_missing():
    # 분 파싱 실패 → 원본 도착메시지 그대로 표시
    arrivals = [Arrival(route="6516", etas=[_eta(None, None, None, "곧 도착")])]
    msg = format_arrivals("등촌역 → 당산역", _single_group(["6516"]), arrivals)

    assert "곧 도착" in msg
    assert "⏱" not in msg


def test_no_bus_message():
    msg = format_arrivals("등촌역 → 당산역", _single_group(["6516"]), [])
    assert "표시할 버스가 없어요" in msg

    # etas 가 모두 비어도 안내 한 줄
    msg2 = format_arrivals(
        "등촌역 → 당산역",
        _single_group(["6516"]),
        [Arrival(route="6516", etas=[])],
    )
    assert "표시할 버스가 없어요" in msg2


def test_groups_shown_with_sublabel_and_sorted_by_arrival():
    groups = [
        {"label": "등촌역 방면", "routes": ["6623", "6632"]},
        {"label": "관음·삼성아파트 방면", "routes": ["660"]},
    ]
    arrivals = [
        Arrival(route="6632", etas=[_eta(6, 4, "여유", "6분후[4번째 전]")]),
        Arrival(route="6623", etas=[_eta(4, 2, "여유", "4분후[2번째 전]")]),
        Arrival(route="660", etas=[_eta(5, 3, "여유", "5분후[3번째 전]")]),
    ]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    assert "🚏 등촌역 방면" in msg
    assert "🚏 관음·삼성아파트 방면" in msg
    # 그룹 안에서는 도착 빠른 순: 6623(4분) 이 6632(6분) 보다 앞
    assert msg.index("🚌 6623번") < msg.index("🚌 6632번")


def test_group_tie_break_by_congestion_when_same_minutes():
    groups = [{"label": "등촌역 방면", "routes": ["605", "6514"]}]
    arrivals = [
        Arrival(route="605", etas=[_eta(5, 1, "보통", "5분후[1번째 전]")]),
        Arrival(route="6514", etas=[_eta(5, 1, "여유", "5분후[1번째 전]")]),
    ]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    # 동일 5분 도착 → 혼잡도 낮은(여유) 6514 가 보통인 605 보다 앞
    assert msg.index("🚌 6514번") < msg.index("🚌 605번")


def test_group_limits_to_max_per_group():
    routes = ["a", "b", "c", "d", "e"]
    arrivals = [
        Arrival(route=r, etas=[_eta(i + 1, 1, "여유", f"{i + 1}분후")])
        for i, r in enumerate(routes)
    ]
    groups = [{"label": "등촌역 방면", "routes": routes}]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    # 메시지에 실제로 나타나는 순서대로 추출한다(입력 순서 재구성이 아니라
    # 표시 순서 자체를 검증해야 정렬/슬라이스 회귀를 잡아낼 수 있다).
    shown = re.findall(r"🚌 (\w+)번", msg)
    assert len(shown) == bot._MAX_PER_GROUP
    # 가장 빨리 오는 3대(a,b,c)만, 도착 순서대로 남아야 한다
    assert shown == ["a", "b", "c"]


def test_group_soon_arrival_ranks_first():
    groups = [{"label": "등촌역 방면", "routes": ["a", "b"]}]
    arrivals = [
        Arrival(route="a", etas=[_eta(3, 1, "여유", "3분후")]),
        Arrival(route="b", etas=[_eta(None, None, None, "곧 도착")]),
    ]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    assert msg.index("🚌 b번") < msg.index("🚌 a번")


def test_empty_group_shows_no_bus_line_but_keeps_sublabel():
    groups = [
        {"label": "등촌역 방면", "routes": ["6623"]},
        {"label": "관음·삼성아파트 방면", "routes": ["660"]},
    ]
    arrivals = [Arrival(route="6623", etas=[_eta(4, 2, "여유", "4분후[2번째 전]")])]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    assert "🚏 관음·삼성아파트 방면" in msg
    assert "도착 예정 버스가 없어요" in msg


def test_group_dedupes_same_route_to_nearest_only():
    # 같은 노선의 여러 대가 상위권을 독점해 다른 노선을 밀어내면 안 된다.
    groups = [{"label": "등촌역 방면", "routes": ["605", "6623", "6632"]}]
    arrivals = [
        Arrival(
            route="605",
            etas=[
                _eta(4, 2, "여유", "4분후[2번째 전]"),
                _eta(11, 5, "여유", "11분후[5번째 전]"),
            ],
        ),
        Arrival(route="6623", etas=[_eta(6, 4, "여유", "6분후[4번째 전]")]),
        Arrival(route="6632", etas=[_eta(4, 2, "여유", "4분후[2번째 전]")]),
    ]
    msg = format_arrivals("당산역 출발", groups, arrivals, evening=True)

    # 605 는 가장 빠른 1대(4분)만 표시, 11분짜리 두 번째 줄은 없어야 한다.
    assert msg.count("🚌 605번") == 1
    assert "11분" not in msg
    # 그 자리를 대신해 다른 노선(6623)이 보여야 한다.
    assert "🚌 6623번" in msg


def test_group_without_label_omits_sublabel():
    groups = [{"label": "", "routes": ["6632"]}]
    arrivals = [Arrival(route="6632", etas=[_eta(3, 2, "여유", "3분후[2번째 전]")])]
    msg = format_arrivals("등촌역 → 당산역", groups, arrivals, evening=False)

    assert "🚏" not in msg


def test_handle_command_routes_keyboard_buttons(monkeypatch):
    # build_message 를 monkeypatch 해 네트워크 호출 없이 라우팅만 검증한다.
    monkeypatch.setattr(bot, "build_message", lambda name: f"scenario:{name}")

    assert _handle_command(bot._BTN_MORNING) == "scenario:morning"
    assert _handle_command(bot._BTN_EVENING) == "scenario:evening"
    # 수동 텍스트 입력(alias)도 버튼과 동일하게 동작
    assert _handle_command("아침") == "scenario:morning"
    assert _handle_command("저녁") == "scenario:evening"


def test_handle_command_slash_commands_unaffected(monkeypatch):
    # 버튼 라우팅 추가가 기존 슬래시 명령 동작을 깨지 않는지 회귀 확인
    monkeypatch.setattr(bot, "build_message", lambda name: f"scenario:{name}")

    assert _handle_command("/morning") == "scenario:morning"
    assert _handle_command("/evening") == "scenario:evening"
    assert _handle_command("/morning@my_bot 어쩌고") == "scenario:morning"
    assert _handle_command("/start") == bot._HELP
    assert _handle_command("/help") == bot._HELP
    assert _handle_command("알 수 없는 텍스트") is None
    assert _handle_command("") is None


def test_format_arrivals_footer_uses_kst(monkeypatch):
    # Railway는 UTC로 배포되므로 datetime.now()를 그냥 쓰면 한국 시각과
    # 9시간 어긋난다. 시간대가 명시적으로 KST여야 한다.
    captured = {}

    class FakeDatetime(bot.datetime):
        @classmethod
        def now(cls, tz=None):
            captured["tz"] = tz
            return super().now(tz)

    monkeypatch.setattr(bot, "datetime", FakeDatetime)

    format_arrivals("당산역 출발", _single_group([]), [], evening=True)

    assert captured["tz"] is not None
    assert captured["tz"].utcoffset(None) == timedelta(hours=9)


def test_build_message_error_hides_exception_details(monkeypatch, capsys):
    # 버스 API/텔레그램 예외 메시지에는 serviceKey/토큰이 담긴 URL이 포함될 수
    # 있다. 사용자 응답과 로그(stderr) 어디에도 원본 예외 문자열이 노출되면 안 된다.
    def _boom():
        raise RuntimeError("http://ws.bus.go.kr/...?serviceKey=SECRET123&arsId=1")

    monkeypatch.setattr(bot, "load_settings", _boom)

    msg = bot.build_message("morning")

    assert "SECRET123" not in msg
    assert "가져오지 못했어요" in msg
    captured = capsys.readouterr()
    assert "SECRET123" not in captured.err
    assert "SECRET123" not in captured.out


def test_poll_once_processes_update_and_advances_offset(monkeypatch):
    sent = []
    monkeypatch.setattr(bot, "build_message", lambda name: f"scenario:{name}")
    monkeypatch.setattr(
        bot, "_send_message", lambda token, chat_id, text: sent.append((chat_id, text))
    )

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "result": [
                    {
                        "update_id": 5,
                        "message": {"chat": {"id": 1}, "text": "/morning"},
                    }
                ]
            }

    monkeypatch.setattr(bot.requests, "get", lambda *a, **k: FakeResp())

    new_offset = bot._poll_once("TOKEN", "https://api.telegram.org/botTOKEN", None, "")

    assert new_offset == 6
    assert sent == [("1", "scenario:morning")]


def test_poll_once_survives_getupdates_network_error(monkeypatch):
    def _raise(*a, **k):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(bot.requests, "get", _raise)
    slept = []
    monkeypatch.setattr(bot.time, "sleep", lambda seconds: slept.append(seconds))

    # 폴링 루프가 죽지 않도록 예외를 삼키고 offset을 그대로 반환해야 한다.
    result = bot._poll_once("TOKEN", "https://api.telegram.org/botTOKEN", 10, "")
    assert result == 10
    # 네트워크 에러 시 즉시 재시도하며 폭주하지 않도록 백오프가 걸려야 한다.
    assert slept == [bot._ERROR_BACKOFF_SECONDS]


def test_poll_once_no_backoff_on_success(monkeypatch):
    monkeypatch.setattr(bot, "build_message", lambda name: f"scenario:{name}")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": []}

    monkeypatch.setattr(bot.requests, "get", lambda *a, **k: FakeResp())
    slept = []
    monkeypatch.setattr(bot.time, "sleep", lambda seconds: slept.append(seconds))

    bot._poll_once("TOKEN", "https://api.telegram.org/botTOKEN", None, "")
    # getUpdates가 성공하면 백오프 없이 바로 다음 반복으로 넘어가야 한다.
    assert slept == []


def test_poll_once_logs_status_code_on_http_error(monkeypatch, capsys):
    # 409(동시 폴링)/401(토큰) 등을 로그만 보고 구분할 수 있어야 한다.
    class FakeResp:
        status_code = 409

        def raise_for_status(self):
            err = requests.HTTPError("409 Conflict")
            err.response = self
            raise err

    monkeypatch.setattr(bot.requests, "get", lambda *a, **k: FakeResp())
    monkeypatch.setattr(bot.time, "sleep", lambda seconds: None)

    bot._poll_once("TOKEN", "https://api.telegram.org/botTOKEN", 10, "")

    err = capsys.readouterr().err
    assert "HTTPError" in err
    assert "409" in err
    # 상태 코드는 남기되 토큰이 담긴 URL은 절대 남기지 않는다.
    assert "TOKEN" not in err


def test_poll_once_survives_sendmessage_network_error(monkeypatch):
    monkeypatch.setattr(bot, "build_message", lambda name: "reply")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "result": [
                    {"update_id": 1, "message": {"chat": {"id": 1}, "text": "/morning"}}
                ]
            }

    monkeypatch.setattr(bot.requests, "get", lambda *a, **k: FakeResp())

    def _raise_post(*a, **k):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(bot.requests, "post", _raise_post)

    # sendMessage 실패가 폴링 루프 전체를 죽이면 안 되고 offset은 정상 갱신되어야 한다.
    result = bot._poll_once("TOKEN", "https://api.telegram.org/botTOKEN", None, "")
    assert result == 2
