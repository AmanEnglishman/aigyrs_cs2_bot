import logging
import os
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional


import requests
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


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


# Простое кэширование на основе LRU (TTL через декоратор не поддерживается напрямую)
_cache: Dict[str, tuple[Dict[str, Any], float]] = {}
_CACHE_TTL = 300  # 5 минут


def _get_cached(key: str) -> Optional[Dict[str, Any]]:
    """Получить значение из кэша, если оно не устарело."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < _CACHE_TTL:
            logger.debug(f"Cache hit for {key}")
            return value
        else:
            del _cache[key]
    return None


def _set_cached(key: str, value: Dict[str, Any]) -> None:
    """Сохранить значение в кэш."""
    _cache[key] = (value, time.time())
    logger.debug(f"Cached {key}")


def search_player(nickname: str) -> Optional[Dict[str, Any]]:
    """
    Find player by nickname.
    Returns first matched player dict or None.
    Uses caching to reduce API calls.
    """
    cache_key = f"search:{nickname.lower()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = f"{FACEIT_BASE_URL}/search/players"
    params = {"nickname": nickname}

    logger.info(f"Searching player: {nickname}")
    resp = requests.get(url, headers=_get_headers(), params=params, timeout=10)

    if resp.status_code != 200:
        logger.error(f"FACEIT search error ({resp.status_code}): {resp.text}")
        raise FaceitAPIError(
            f"Faceit search error ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    items = data.get("items") or []
    result = items[0] if items else None

    if result:
        _set_cached(cache_key, result)

    return result


def get_player_info(player_id: str) -> Dict[str, Any]:
    cache_key = f"info:{player_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = f"{FACEIT_BASE_URL}/players/{player_id}"
    logger.debug(f"Fetching player info: {player_id}")
    resp = requests.get(url, headers=_get_headers(), timeout=10)

    if resp.status_code != 200:
        logger.error(f"FACEIT player info error ({resp.status_code}): {resp.text}")
        raise FaceitAPIError(
            f"Faceit player info error ({resp.status_code}): {resp.text}"
        )

    result = resp.json()
    _set_cached(cache_key, result)
    return result


def get_player_stats(player_id: str, game: str = "cs2") -> Dict[str, Any]:
    cache_key = f"stats:{player_id}:{game}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = f"{FACEIT_BASE_URL}/players/{player_id}/stats/{game}"
    logger.debug(f"Fetching player stats: {player_id} ({game})")
    resp = requests.get(url, headers=_get_headers(), timeout=10)

    if resp.status_code != 200:
        logger.error(f"FACEIT player stats error ({resp.status_code}): {resp.text}")
        raise FaceitAPIError(
            f"Faceit player stats error ({resp.status_code}): {resp.text}"
        )

    result = resp.json()
    _set_cached(cache_key, result)
    return result


def get_player_matches(player_id: str, game: str = "cs2", limit: int = 5) -> Dict[str, Any]:
    """
    Get recent matches for a player.
    Returns matches data with pagination.
    """
    cache_key = f"matches:{player_id}:{game}:{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    url = f"{FACEIT_BASE_URL}/players/{player_id}/history"
    params = {"game": game, "limit": limit}
    
    logger.debug(f"Fetching player matches: {player_id} ({game}, limit={limit})")
    resp = requests.get(url, headers=_get_headers(), params=params, timeout=10)

    if resp.status_code != 200:
        logger.error(f"FACEIT player matches error ({resp.status_code}): {resp.text}")
        raise FaceitAPIError(
            f"Faceit player matches error ({resp.status_code}): {resp.text}"
        )

    result = resp.json()
    _set_cached(cache_key, result)
    return result


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


def get_player_maps_stats(nickname: str, game: str = "cs2") -> str:
    """
    Get player statistics by maps.
    Returns formatted text with stats for each map.
    """
    player = search_player(nickname)
    if not player:
        return "Игрок не найден на FACEIT 🤷‍♂️"

    player_id = player["player_id"]
    stats = get_player_stats(player_id, game=game)
    segments = stats.get("segments", [])

    if not segments:
        return f"Статистика по картам для <b>{nickname}</b> недоступна 📊"

    nickname_real = player.get("nickname") or nickname
    text = f"🗺 Статистика по картам: <b>{nickname_real}</b>\n\n"

    # Сортируем карты по количеству матчей (если есть)
    sorted_segments = sorted(
        segments,
        key=lambda x: x.get("stats", {}).get("Matches", 0) or 0,
        reverse=True
    )

    for segment in sorted_segments[:10]:  # Показываем топ-10 карт
        map_name = segment.get("label", "Unknown")
        map_stats = segment.get("stats", {}) or {}

        matches = map_stats.get("Matches", "—")
        wins = map_stats.get("Wins", "—")
        losses = map_stats.get("Losses", "—")
        win_rate = map_stats.get("Win Rate %", "—")
        kd = map_stats.get("Average K/D Ratio", "—")
        adr = map_stats.get("Average ADR", "—")

        text += (
            f"<b>{map_name}</b>\n"
            f"Матчей: {matches} | W/L: {wins}/{losses} | WR: {win_rate}%\n"
            f"K/D: {kd} | ADR: {adr}\n\n"
        )

    return text

def format_faceit_date(value: Any) -> str:
    """
    Приводит дату FACEIT к читаемому виду.
    Поддерживает:
    - unix timestamp (int)
    - ISO-строку
    - None / мусорные значения
    """
    if isinstance(value, int):
        return datetime.utcfromtimestamp(value).strftime("%d.%m.%Y %H:%M")

    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return value

    return "N/A"


def get_player_recent_matches(nickname: str, game: str = "cs2", limit: int = 5) -> str:
    """
    Get recent matches for a player.
    Returns formatted text with match results.
    """
    player = search_player(nickname)
    if not player:
        return "Игрок не найден на FACEIT 🤷‍♂️"

    player_id = player["player_id"]
    matches_data = get_player_matches(player_id, game=game, limit=limit)
    items = matches_data.get("items", [])

    if not items:
        return f"Последние матчи для <b>{nickname}</b> не найдены 🎮"

    nickname_real = player.get("nickname") or nickname
    text = f"🎮 Последние матчи: <b>{nickname_real}</b>\n\n"

    for match in items:
        match_id = match.get("match_id", "N/A")

        # ✅ безопасное форматирование даты
        date_str = format_faceit_date(match.get("started_at"))

        # --- Команды и счёт ---
        teams = match.get("teams", {})
        faction1 = teams.get("faction1", {})
        faction2 = teams.get("faction2", {})

        score1 = faction1.get("stats", {}).get("score", 0) or 0
        score2 = faction2.get("stats", {}).get("score", 0) or 0

        # --- Определяем команду игрока ---
        player_team = None
        for team_key in ("faction1", "faction2"):
            roster = teams.get(team_key, {}).get("roster", [])
            if any(p.get("player_id") == player_id for p in roster):
                player_team = team_key
                break

        if player_team:
            won = (
                player_team == "faction1" and score1 > score2
            ) or (
                player_team == "faction2" and score2 > score1
            )
            result_emoji = "✅" if won else "❌"
        else:
            result_emoji = "⚪"

        # --- Статы игрока ---
        player_stats = {}
        for team_key in ("faction1", "faction2"):
            roster = teams.get(team_key, {}).get("roster", [])
            for p in roster:
                if p.get("player_id") == player_id:
                    player_stats = p.get("stats", {}) or {}
                    break
            if player_stats:
                break

        kd = player_stats.get("K/D Ratio", player_stats.get("Average K/D Ratio", "—"))
        kills = player_stats.get("Kills", "—")
        deaths = player_stats.get("Deaths", "—")
        adr = player_stats.get("ADR", player_stats.get("Average ADR", "—"))

        text += (
            f"{result_emoji} <b>{date_str}</b>\n"
            f"Счёт: {score1} - {score2}\n"
            f"K/D: {kd} ({kills}/{deaths}) | ADR: {adr}\n"
            f"ID: <code>{match_id}</code>\n\n"
        )

    return text



if __name__ == "__main__":
    # simple manual test
    nickname = input("Введите ник на FACEIT: ")
    try:
        print(get_player_summary(nickname))
    except FaceitAPIError as exc:
        print("Ошибка при запросе к FACEIT:", exc)


