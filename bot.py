import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

from faceit_client import FaceitAPIError, get_player_summary


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def cmd_start(message: Message) -> None:
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
    )


async def cmd_faceit(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ник: /faceit &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    nickname = args[1].strip()
    if not nickname:
        await message.answer("Укажи ник: /faceit &lt;ник&gt;", reply_to_message_id=message.message_id)
        return

    await message.answer(f"Ищу игрока <b>{nickname}</b> на FACEIT, подожди секунду…")

    try:
        summary = get_player_summary(nickname)
    except FaceitAPIError as exc:
        await message.answer(
            "Произошла ошибка при запросе к FACEIT 🛠\n"
            f"Детали: {exc}"
        )
        return
    except Exception:
        await message.answer("Что-то пошло не так при запросе к FACEIT 😔")
        return

    await message.answer(summary)


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_faceit, Command("faceit"))
    dp.message.register(cmd_faceit, F.text.startswith("/faceit "))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


