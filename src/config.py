"""설정 로더: env/.env(또는 환경변수)와 stops.json을 읽는다.

이 모듈은 import 만으로는 어떤 부작용/예외도 일으키지 않는다.
(키 로딩은 load_settings() 호출 시점에만 일어난다.)
"""

import json
import os
from dataclasses import dataclass

ENV_PATH = "env/.env"
STOPS_PATH = "stops.json"


@dataclass
class Settings:
    seoul_bus_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str


def load_settings() -> Settings:
    """env/.env 가 있으면 로드한 뒤 환경변수에서 값을 읽는다.

    값이 없으면 빈 문자열을 채운다. 키를 코드에 하드코딩하지 않는다.
    """
    if os.path.exists(ENV_PATH):
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)

    return Settings(
        seoul_bus_api_key=os.environ.get("SEOUL_BUS_API_KEY", ""),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
    )


def load_stops(path: str = STOPS_PATH) -> dict:
    """stops.json 을 읽어 dict로 반환한다. 최상위에 morning/evening 키."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_scenario(stops: dict, name: str) -> dict:
    """morning|evening 시나리오 dict를 반환한다. 없는 이름이면 ValueError."""
    if name not in stops:
        raise ValueError(f"unknown scenario: {name!r}")
    return stops[name]
