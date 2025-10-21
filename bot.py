import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")  # защита от n8n
CHANNEL_ID = -1003189812929
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"
WEBHOOK_URL = "https://zhivoe-lico-bot.onrender.com/webhook"  # URL для Telegram webhook

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    
    pay_link = f"{PRODAMUS_LINK}?order_num={tg_id}"


    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_link}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)


# === ЛОГИКА ВЫДАЧИ ДОСТУПА ===
async def give_access(user_id: int):
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


# === /access (ручной) ===
@dp.message(lambda msg: msg.text and msg.text.strip() == "/access")
async def handle_access_command(message: types.Message):
    await give_access(message.from_user.id)


# === n8n → /access ===
async def handle_access(request):
    data = await request.json()
    secret = request.headers.get("X-Access-Secret")
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


# === Telegram → /webhook ===
async def handle_webhook(request):
    try:
        data = await request.json()
        update = types.Update.model_validate(data)
        await dp.feed_update(bot, update)
        return web.Response(text="ok", status=200)
    except Exception as e:
        return web.Response(text=f"Webhook error: {e}", status=500)


# === Инициализация ===
async def on_startup(app):
    # Устанавливаем webhook при запуске
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


async def on_shutdown(app):
    await bot.delete_webhook()
    print("🛑 Webhook удалён")


def create_app():
    app = web.Application()
    app.router.add_get("/", lambda _: web.Response(text="ok"))  # проверка
    app.router.add_post("/access", handle_access)                # от n8n
    app.router.add_post("/webhook", handle_webhook)              # от Telegram
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)


