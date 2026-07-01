"""bus_service 단위 테스트. 실제 네트워크 호출 없이 client를 mock으로 주입한다."""

from src.bus_service import Arrival, BusEta, get_arrivals


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    """client.get(...) 호출을 가로채 고정 응답을 돌려준다."""

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return FakeResponse(self._payload)


def _payload(items):
    return {"msgBody": {"itemList": items}}


def test_routes_filter_and_order():
    # 응답 순서(660, 6516)와 다른 routes 순서(6516, 660)로 요청
    client = FakeClient(
        _payload(
            [
                {"rtNm": "660", "arrmsg1": "7분후[4번째 전]", "congestion": "5"},
                {"rtNm": "6516", "arrmsg1": "3분후[2번째 전]", "congestion": "3"},
                {"rtNm": "999", "arrmsg1": "1분후[1번째 전]", "congestion": "4"},
            ]
        )
    )
    arrivals = get_arrivals("16104", ["6516", "660"], "KEY", client=client)

    assert [a.route for a in arrivals] == ["6516", "660"]  # routes 순서 유지, 999 제외


def test_routes_none_returns_all_in_response_order():
    client = FakeClient(
        _payload(
            [
                {"rtNm": "660", "arrmsg1": "7분후[4번째 전]"},
                {"rtNm": "6516", "arrmsg1": "3분후[2번째 전]"},
            ]
        )
    )
    arrivals = get_arrivals("16104", None, "KEY", client=client)
    assert [a.route for a in arrivals] == ["660", "6516"]


def test_congestion_mapping_and_none():
    client = FakeClient(
        _payload(
            [
                {"rtNm": "A", "arrmsg1": "3분후[2번째 전]", "congestion": "3"},
                {"rtNm": "B", "arrmsg1": "3분후[2번째 전]", "congestion": "4"},
                {"rtNm": "C", "arrmsg1": "3분후[2번째 전]", "congestion": "5"},
                {"rtNm": "D", "arrmsg1": "3분후[2번째 전]", "congestion": "0"},
                {"rtNm": "E", "arrmsg1": "3분후[2번째 전]"},  # 필드 자체 없음
            ]
        )
    )
    arrivals = get_arrivals("16104", None, "KEY", client=client)
    cong = {a.route: a.etas[0].congestion for a in arrivals}
    assert cong == {"A": "여유", "B": "보통", "C": "혼잡", "D": None, "E": None}


def test_congestion_field_typo_congetion():
    # API 오탈자 필드명 'congetion' 도 견딘다
    client = FakeClient(
        _payload([{"rtNm": "A", "arrmsg1": "3분후[2번째 전]", "congetion": "5"}])
    )
    arrivals = get_arrivals("16104", None, "KEY", client=client)
    assert arrivals[0].etas[0].congestion == "혼잡"


def test_arrmsg_parsing():
    client = FakeClient(
        _payload([{"rtNm": "A", "arrmsg1": "12분후[6번째 전]"}])
    )
    eta = get_arrivals("16104", None, "KEY", client=client)[0].etas[0]
    assert eta.minutes == 12
    assert eta.stations_away == 6
    assert eta.raw_msg == "12분후[6번째 전]"


def test_arrmsg_parse_failure_preserves_raw():
    # "곧 도착" 등 분/정거장 파싱 불가 → None 이지만 raw_msg 보존
    client = FakeClient(_payload([{"rtNm": "A", "arrmsg1": "곧 도착"}]))
    eta = get_arrivals("16104", None, "KEY", client=client)[0].etas[0]
    assert eta.minutes is None
    assert eta.stations_away is None
    assert eta.raw_msg == "곧 도착"


def test_max_two_etas():
    client = FakeClient(
        _payload(
            [
                {
                    "rtNm": "A",
                    "arrmsg1": "3분후[2번째 전]",
                    "arrmsg2": "12분후[6번째 전]",
                }
            ]
        )
    )
    etas = get_arrivals("16104", None, "KEY", client=client)[0].etas
    assert len(etas) == 2
    assert etas[0].minutes == 3
    assert etas[1].minutes == 12


def test_missing_arrmsg2_yields_single_eta():
    client = FakeClient(_payload([{"rtNm": "A", "arrmsg1": "3분후[2번째 전]"}]))
    etas = get_arrivals("16104", None, "KEY", client=client)[0].etas
    assert len(etas) == 1


def test_empty_itemlist_returns_empty():
    client = FakeClient(_payload(None))
    assert get_arrivals("16104", ["6516"], "KEY", client=client) == []


def test_request_params_include_arsid_and_key():
    client = FakeClient(_payload([]))
    get_arrivals("16104", None, "MYKEY", client=client)
    _, params = client.calls[0]
    assert params["arsId"] == "16104"
    assert params["serviceKey"] == "MYKEY"
    assert params["resultType"] == "json"
