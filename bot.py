import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003189812929
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === ОБРАБОТЧИКИ БОТА ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    pay_link = f"{PRODAMUS_LINK}?custom_fields[telegram_id]={tg_id}"
    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_link}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)


@dp.message(Command("access"))
async def cmd_access(message: types.Message):
    """Ручная проверка команды /access"""
    await give_access(message.from_user.id, message)


# === ЛОГИКА ВЫДАЧИ ДОСТУПА ===
async def give_access(user_id: int, message: types.Message | None = None):
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"access_{user_id}",
            member_limit=1,
            expire_date=None,
        )

        text = (
            "🎉 Оплата получена!\n\n"
            f"Вот ваша персональная ссылка для входа в курс:\n\n"
            f"{invite_link.invite_link}"
        )

        if message:
            await message.answer(text)
        else:
            await bot.send_message(chat_id=user_id, text=text)

    except Exception as e:
        err = f"⚠️ Ошибка при создании ссылки: {e}"
        if message:
            await message.answer(err)
        else:
            await bot.send_message(chat_id=user_id, text=err)


# === HTTP-СЕРВЕР ДЛЯ RENDER И N8N ===
async def handle_access(request):
    """Маршрут для n8n: POST /access"""
    data = await request.json()
    user_id = data.get("telegram_id")
    if not user_id:
        return web.Response(text="No telegram_id", status=400)

    await give_access(int(user_id))
    return web.Response(text="ok", status=200)


async def on_startup(app):
    asyncio.create_task(dp.start_polling(bot))
    print("✅ Aiogram polling started")


def create_app():
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="ok"))  # проверочный маршрут
    app.router.add_post("/access", handle_access)               # основной маршрут для n8n
    app.on_startup.append(on_startup)
    return app


# === ЗАПУСК ===
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

from aiogram import types

@dp.message(Command("access"))
async def cmd_access_command(message: types.Message):
    """Срабатывает, если человек сам вводит /access"""
    await send_access_link(message.from_user.id, message)


@dp.message(lambda message: message.text.strip() == "/access")
async def cmd_access_text(message: types.Message):
    """Срабатывает, если n8n прислал текст '/access'"""
    await send_access_link(message.chat.id, message)


async def send_access_link(user_id: int, message: types.Message):
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"access_{user_id}",
            member_limit=1,
            expire_date=None
        )
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Оплата получена!\n\n"
                f"Вот ваша персональная ссылка для входа в курс:\n\n"
                f"{invite_link.invite_link}"
            )
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при создании ссылки: {e}")




