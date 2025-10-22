import os
import json
import hmac
import hashlib
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")
BASE_URL = "https://nastroikatela.payform.ru/"
WEBHOOK_URL = "https://zhivoe-lico-bot-1.onrender.com/webhook"
CHANNEL_ID = -1003189812929
PRICE = 4500

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# === Генерация короткой платёжной ссылки ===
async def create_payment_link(order_id: int) -> str:
    payload = {
        "do": "link",
        "order_id": order_id,
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL, data=payload) as resp:
            text = await resp.text()
            print(f"📎 Ответ Prodamus: {text}")
            return text.strip()


# === /start ===
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    print(f"🚀 Получена команда /start от {message.from_user.id}")
    pay_link = await create_payment_link(message.from_user.id)
    if not pay_link.startswith("http"):
        await message.answer("⚠️ Ошибка при создании ссылки. Попробуй позже.")
        return

    await message.answer(
        f"Привет 🌿\n\n"
        f"Вот ссылка для оплаты курса:\n<a href='{pay_link}'>Оплатить курс</a>\n\n"
        "После оплаты бот автоматически пришлёт персональную ссылку 💫",
        disable_web_page_preview=True,
    )


# === Проверка подписи ===
def verify_signature(data: dict, signature: str) -> bool:
    if not signature or not PRODAMUS_SECRET:
        return False
    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    calc = hmac.new(
        PRODAMUS_SECRET.encode(), msg=json_data.encode(), digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calc, signature.strip().lower())


# === Обработка уведомлений Prodamus ===
async def handle_access(request: web.Request):
    try:
        raw = await request.text()
        headers = dict(request.headers)
        print("📬 Пришёл POST /access")
        print("🔸 Заголовки:", headers)
        print("🔸 Тело:", raw)

        signature = headers.get("Sign")
        data = json.loads(raw)

        if not verify_signature(data, signature):
            print("⚠️ Подпись не совпала!")
            return web.Response(text="invalid signature", status=403)

        if data.get("status") != "success":
            print("ℹ️ Статус оплаты не success:", data.get("status"))
            return web.Response(text="not success", status=200)

        user_id = int(data.get("order_id", 0))
        if not user_id:
            print("⚠️ Нет user_id")
            return web.Response(text="no user_id", status=400)

        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID, member_limit=1, name=f"invite_{user_id}"
        )
        await bot.send_message(
            user_id,
            f"🎉 Оплата получена!\n\nВот твоя ссылка:\n{invite.invite_link}"
        )
        print(f"✅ Ссылка отправлена пользователю {user_id}")
        return web.Response(text="ok", status=200)

    except Exception as e:
        print("❌ Ошибка при обработке уведомления:", e)
        return web.Response(status=500)


# === Инициализация вебхука ===
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def setup_app():
    app = web.Application()
    app.router.add_post("/access", handle_access)

    # ВАЖНО: регистрируем webhook endpoint
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    app = setup_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

