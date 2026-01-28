import asyncio
import logging
import os
import signal
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from faceit_client import (
    FaceitAPIError,
    get_player_summary,
    get_player_maps_stats,
    get_player_recent_matches,
    search_player, get_player_card_data,
)

from card_renderer import render_faceit_card
from aiogram.types import FSInputFile


load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Глобальные переменные для graceful shutdown
bot_instance: Bot | None = None
dp_instance: Dispatcher | None = None
shutdown_event = asyncio.Event()


async def cmd_start(message: Message) -> None:
    logger.info(f"User {message.from_user.id} ({message.from_user.username}) used /start")
    await message.answer(
        "Привет! Я бот для просмотра статистики FACEIT по игрокам.\n\n"
        "Используй команду:\n"
        "/faceit &lt;ник&gt;\n\n"
        "Например:\n"
        "/faceit Ars_Ki"
    )


async def cmd_help(message: Message) -> None:
    await message.answer(
        "Доступные команды:\n"
        "/start — краткая информация\n"
        "/help — помощь\n"
        "/faceit &lt;ник&gt; — показать ELO, уровень, K/D и другие статы\n"
        "/faceit_maps &lt;ник&gt; — статистика по картам\n"
        "/faceit_matches &lt;ник&gt; — последние матчи\n\n"
        "💡 После запроса профиля используй inline-кнопки для быстрого доступа!"
    )


def create_player_keyboard(nickname: str) -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру с быстрыми действиями для игрока."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗺 Карты", callback_data=f"maps:{nickname}"),
            InlineKeyboardButton(text="🎮 Матчи", callback_data=f"matches:{nickname}"),
        ],
        [
            InlineKeyboardButton(text="📊 Профиль", callback_data=f"profile:{nickname}"),
        ]
    ])
    return keyboard


async def cmd_faceit(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ник: /faceit &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    nickname = args[1].strip()
    if not nickname:
        await message.answer("Укажи ник: /faceit &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    user_info = f"{message.from_user.id} ({message.from_user.username or 'N/A'})"
    logger.info(f"User {user_info} requested stats for: {nickname}")

    await message.answer(f"Ищу игрока <b>{nickname}</b> на FACEIT, подожди секунду…")

    try:
        summary = get_player_summary(nickname)
        keyboard = create_player_keyboard(nickname)
        await message.answer(summary, reply_markup=keyboard)
        logger.info(f"Successfully retrieved stats for {nickname} (user: {user_info})")
    except FaceitAPIError as exc:
        logger.error(f"FACEIT API error for {nickname}: {exc}")
        await message.answer(
            "Произошла ошибка при запросе к FACEIT 🛠\n"
            f"Детали: {exc}"
        )
    except Exception as exc:
        logger.exception(f"Unexpected error for {nickname}: {exc}")
        await message.answer("Что-то пошло не так при запросе к FACEIT 😔")


async def cmd_faceit_maps(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ник: /faceit_maps &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    nickname = args[1].strip()
    if not nickname:
        await message.answer("Укажи ник: /faceit_maps &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    user_info = f"{message.from_user.id} ({message.from_user.username or 'N/A'})"
    logger.info(f"User {user_info} requested maps stats for: {nickname}")

    await message.answer(f"Ищу статистику по картам для <b>{nickname}</b>…")

    try:
        maps_stats = get_player_maps_stats(nickname)
        keyboard = create_player_keyboard(nickname)
        await message.answer(maps_stats, reply_markup=keyboard)
        logger.info(f"Successfully retrieved maps stats for {nickname} (user: {user_info})")
    except FaceitAPIError as exc:
        logger.error(f"FACEIT API error for {nickname}: {exc}")
        await message.answer(
            "Произошла ошибка при запросе к FACEIT 🛠\n"
            f"Детали: {exc}"
        )
    except Exception as exc:
        logger.exception(f"Unexpected error for {nickname}: {exc}")
        await message.answer("Что-то пошло не так при запросе к FACEIT 😔")


async def cmd_faceit_matches(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ник: /faceit_matches &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    nickname = args[1].strip()
    if not nickname:
        await message.answer("Укажи ник: /faceit_matches &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    user_info = f"{message.from_user.id} ({message.from_user.username or 'N/A'})"
    logger.info(f"User {user_info} requested matches for: {nickname}")

    await message.answer(f"Ищу последние матчи для <b>{nickname}</b>…")

    try:
        matches = get_player_recent_matches(nickname, limit=5)
        keyboard = create_player_keyboard(nickname)
        await message.answer(matches, reply_markup=keyboard)
        logger.info(f"Successfully retrieved matches for {nickname} (user: {user_info})")
    except FaceitAPIError as exc:
        logger.error(f"FACEIT API error for {nickname}: {exc}")
        await message.answer(
            "Произошла ошибка при запросе к FACEIT 🛠\n"
            f"Детали: {exc}"
        )
    except Exception as exc:
        logger.exception(f"Unexpected error for {nickname}: {exc}")
        await message.answer("Что-то пошло не так при запросе к FACEIT 😔")


async def handle_callback(callback: CallbackQuery) -> None:
    """Обработчик inline-кнопок."""
    data = callback.data
    if not data:
        return

    user_info = f"{callback.from_user.id} ({callback.from_user.username or 'N/A'})"
    logger.info(f"User {user_info} clicked button: {data}")

    try:
        action, nickname = data.split(":", 1)
        
        await callback.answer("Загружаю...")

        if action == "profile":
            summary = get_player_summary(nickname)
            keyboard = create_player_keyboard(nickname)
            await callback.message.edit_text(summary, reply_markup=keyboard)
        elif action == "maps":
            maps_stats = get_player_maps_stats(nickname)
            keyboard = create_player_keyboard(nickname)
            await callback.message.edit_text(maps_stats, reply_markup=keyboard)
        elif action == "matches":
            matches = get_player_recent_matches(nickname, limit=5)
            keyboard = create_player_keyboard(nickname)
            await callback.message.edit_text(matches, reply_markup=keyboard)
        else:
            await callback.answer("Неизвестное действие", show_alert=True)

    except ValueError:
        await callback.answer("Ошибка в данных", show_alert=True)
    except FaceitAPIError as exc:
        logger.error(f"FACEIT API error in callback: {exc}")
        await callback.answer(f"Ошибка API: {exc}", show_alert=True)
    except Exception as exc:
        logger.exception(f"Unexpected error in callback: {exc}")
        await callback.answer("Что-то пошло не так 😔", show_alert=True)


def setup_signal_handlers() -> None:
    """Настройка обработчиков сигналов для graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def shutdown() -> None:
    """Корректное завершение работы бота."""
    logger.info("Shutting down bot...")
    if dp_instance:
        await dp_instance.stop_polling()
    if bot_instance:
        await bot_instance.session.close()
    logger.info("Bot stopped")

async def cmd_faceit_card(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используй: /faceit_card <ник>")
        return

    nickname = args[1].strip()

    # 🔹 берём данныеданные из faceit_client
    data = get_player_card_data(nickname)  # 👈 сейчас объясню

    # 🔹 рендерим карточку
    image_path = await render_faceit_card(data)


    await message.answer_photo(
        photo=FSInputFile(image_path),
        caption="🎮 FACEIT Player Card"
    )



async def main() -> None:
    global bot_instance, dp_instance

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")

    logger.info("Starting FACEIT Telegram bot...")

    bot_instance = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp_instance = Dispatcher()

    dp_instance.message.register(cmd_start, CommandStart())
    dp_instance.message.register(cmd_help, Command("help"))
    dp_instance.message.register(cmd_faceit, Command("faceit"))
    dp_instance.message.register(cmd_faceit, F.text.startswith("/faceit "))
    dp_instance.message.register(cmd_faceit_maps, Command("faceit_maps"))
    dp_instance.message.register(cmd_faceit_matches, Command("faceit_matches"))
    dp_instance.message.register(cmd_faceit_card, Command("faceit_card"))

    # Обработчик inline-кнопок
    dp_instance.callback_query.register(handle_callback)

    setup_signal_handlers()

    try:
        logger.info("Bot is running...")
        # Запускаем polling в фоне и ждем сигнала остановки
        polling_task = asyncio.create_task(dp_instance.start_polling(bot_instance))
        await shutdown_event.wait()
        logger.info("Shutdown signal received, stopping polling...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        logger.exception(f"Error in main loop: {e}")
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


