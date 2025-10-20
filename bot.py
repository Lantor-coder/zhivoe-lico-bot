import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003189812929
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"
SECRET_KEY = os.getenv("ACCESS_SECRET", "my_secret_key")  # 🔒 ключ для проверки вызовов из n8n

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === СТАРТ ===
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


# === СЕРВЕР ДЛЯ N8N ===
async def handle_access(request):
    """Выдаёт доступ только при правильном секретном ключе"""
    data = await request.json()

    # Проверяем секрет
    secret = request.headers.get("X-Access-Secret")
    if secret != SECRET_KEY:
        return web.Response(text="Unauthorized", status=401)

    user_id = data.get("telegram_id")
    if not user_id or not str(user_id).isdigit():
        return web.Response(text="Invalid telegram_id", status=400)

    try:
        # Создаём персональную ссылку
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"access_{user_id}",
            member_limit=1,
            expire_date=None,  # можно ограничить срок, например, на 1 день
        )

        await bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 Оплата подтверждена!\n\n"
                f"Вот ваша персональная ссылка для входа в курс:\n\n"
                f"{invite_link.invite_link}"
            ),
        )
        return web.Response(text="ok", status=200)

    except Exception as e:
        return web.Response(text=str(e), status=500)


async def on_startup(app):
    asyncio.create_task(dp.start_polling(bot))
    print("✅ Aiogram polling started")


def create_app():
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="ok"))  # Render health check
    app.router.add_post("/access", handle_access)  # 🔒 защищённый маршрут для n8n
    app.on_startup.append(on_startup)
    return app


# === ЗАПУСК ===
if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
