import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


load_dotenv()

FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
FACEIT_BASE_URL = "https://open.faceit.com/data/v4"


class FaceitAPIError(Exception):
    """Custom exception for Faceit API errors."""


def _country_code_to_flag(code: str) -> str:
    """
    Convert ISO country code (e.g. 'kg') to flag emoji.
    If code is invalid/empty, returns '—'.
    """
    if not code or len(code) != 2:
        return "—"

    try:
        code = code.upper()
        return "".join(chr(127397 + ord(c)) for c in code)
    except Exception:
        return "—"

def _get_headers() -> Dict[str, str]:
    if not FACEIT_API_KEY:
        raise FaceitAPIError("FACEIT_API_KEY is not set in environment")

    return {
        "Authorization": f"Bearer {FACEIT_API_KEY}",
        "Accept": "application/json",
    }


def search_player(nickname: str) -> Optional[Dict[str, Any]]:
    """
    Find player by nickname.
    Returns first matched player dict or None.
    """
    url = f"{FACEIT_BASE_URL}/search/players"
    params = {"nickname": nickname}

    resp = requests.get(url, headers=_get_headers(), params=params, timeout=10)

    if resp.status_code != 200:
        raise FaceitAPIError(
            f"Faceit search error ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    items = data.get("items") or []

    return items[0] if items else None


def get_player_info(player_id: str) -> Dict[str, Any]:
    url = f"{FACEIT_BASE_URL}/players/{player_id}"
    resp = requests.get(url, headers=_get_headers(), timeout=10)

    if resp.status_code != 200:
        raise FaceitAPIError(
            f"Faceit player info error ({resp.status_code}): {resp.text}"
        )

    return resp.json()


def get_player_stats(player_id: str, game: str = "cs2") -> Dict[str, Any]:
    url = f"{FACEIT_BASE_URL}/players/{player_id}/stats/{game}"
    resp = requests.get(url, headers=_get_headers(), timeout=10)

    if resp.status_code != 200:
        raise FaceitAPIError(
            f"Faceit player stats error ({resp.status_code}): {resp.text}"
        )

    return resp.json()


def get_player_summary(nickname: str, game: str = "cs2") -> str:
    """
    High-level helper: by nickname returns formatted text with main stats.
    """
    player = search_player(nickname)
    if not player:
        return "Игрок не найден на FACEIT 🤷‍♂️"

    player_id = player["player_id"]

    info = get_player_info(player_id)
    stats = get_player_stats(player_id, game=game)

    game_info = info.get("games", {}).get(game, {})
    lifetime = stats.get("lifetime", {}) or {}

    elo = game_info.get("faceit_elo", "—")
    level_ = game_info.get("skill_level", "—")

    kd = lifetime.get("Average K/D Ratio", "—")
    kr = lifetime.get("Average K/R Ratio", "—")
    adr = lifetime.get("ADR", "—")
    hs = lifetime.get("Headshots %", "—")

    country_code = info.get("country", "") or ""
    country_flag = _country_code_to_flag(country_code)
    nickname_real = info.get("nickname") or nickname

    text = (
        f"🎮 FACEIT профиль\n"
        f"Ник: <b>{nickname_real}</b>\n"
        f"Страна: {country_flag} ({country_code.upper() or '—'})\n"
        f"Игра: {game.upper()}\n\n"
        f"ELO: <b>{elo}</b>\n"
        f"Уровень: <b>{level_}</b>\n\n"
        f"📊 Статы (lifetime):\n"
        f"K/D: <b>{kd}</b>\n"
        f"K/R: <b>{kr}</b>\n"
        f"ADR: <b>{adr}</b>\n"
        f"HS%: <b>{hs}</b>\n"
    )

    return text


if __name__ == "__main__":
    # simple manual test
    nickname = input("Введите ник на FACEIT: ")
    try:
        print(get_player_summary(nickname))
    except FaceitAPIError as exc:
        print("Ошибка при запросе к FACEIT:", exc)


