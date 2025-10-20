import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")  # секрет для n8n
CHANNEL_ID = -1003189812929  # id закрытого канала
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"  # ссылка на оплату

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === /start ===
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


# === ФУНКЦИЯ ВЫДАЧИ ДОСТУПА ===
async def give_access(user_id: int):
    """Создать уникальную ссылку и выдать доступ"""
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
        await bot.send_message(chat_id=user_id, text=f"⚠️ Ошибка при выдаче доступа: {e}")


# === HTTP-ручка /access для n8n ===
async def handle_access(request):
    """Получает запрос из n8n и выдаёт доступ, если секрет совпадает"""
    try:
        data = await request.json()
        secret = request.headers.get("X-Access-Secret")  # 🔒 защита
        if secret != ACCESS_SECRET:
            return web.Response(text="Forbidden", status=403)

        user_id = data.get("telegram_id")
        status = data.get("status")

        if not user_id:
            return web.Response(text="No telegram_id", status=400)

        if status != "paid":
            return web.Response(text="Not paid", status=200)

        await give_access(int(user_id))
        return web.Response(text="ok", status=200)

    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)


# === ПРОСТАЯ ПРОВЕРКА СЕРВЕРА ===
async def handle_root(_):
    return web.Response(text="ok")


# === WEBHOOK ДЛЯ TELEGRAM (если нужно использовать Webhook-режим) ===
from aiogram import types
async def handle_webhook(request):
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")


# === СТАРТ ПРИЛОЖЕНИЯ ===
async def on_startup(app):
    asyncio.create_task(dp.start_polling(bot))
    print("✅ Aiogram polling started")


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)         # проверочный маршрут
    app.router.add_post("/access", handle_access) # n8n → бот
    app.router.add_post("/webhook", handle_webhook)  # опционально
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
