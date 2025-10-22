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
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")  # 🔑 секретный ключ формы из Prodamus
BASE_URL = "https://nastroikatela.payform.ru/"
WEBHOOK_URL = "https://zhivoe-lico-bot-1.onrender.com/webhook"
CHANNEL_ID = -1003189812929  # ID твоего закрытого канала
PRICE = 4500

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# === Генерация короткой платёжной ссылки ===
async def create_payment_link(order_id: int) -> str:
    """Создаёт короткую платёжную ссылку Prodamus (do=link)"""
    payload = {
        "do": "link",
        "order_id": order_id,
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "urlSuccess": "https://zhivoe-lico-bot-1.onrender.com/success",
        "urlReturn": "https://zhivoe-lico-bot-1.onrender.com/return",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL, data=payload) as resp:
            link = await resp.text()
            print(f"📎 Ответ Prodamus: {link}")
            return link.strip()


# === Команда /start ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    pay_link = await create_payment_link(message.from_user.id)
    if not pay_link.startswith("http"):
        await message.answer("⚠️ Ошибка при создании ссылки на оплату. Попробуй позже.")
        return

    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 <a href='{pay_link}'>Оплатить курс</a>\n\n"
        "После оплаты бот автоматически пришлёт тебе персональную ссылку на закрытый канал 💫"
    )
    await message.answer(text, disable_web_page_preview=True)


# === Проверка подписи HMAC от Prodamus ===
def verify_signature(data: dict, signature: str) -> bool:
    """Проверяет, что уведомление пришло именно от Prodamus"""
    if not signature or not PRODAMUS_SECRET:
        return False

    # строка данных в формате JSON без пробелов
    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    calculated = hmac.new(
        PRODAMUS_SECRET.encode(),
        msg=json_data.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated, signature.strip().lower())


# === Обработка уведомления об оплате ===
async def handle_access(request: web.Request):
    try:
        raw_data = await request.text()
        headers = request.headers
        signature = headers.get("Sign")

        data = json.loads(raw_data)
        print(f"📩 Уведомление от Prodamus: {data}")

        # Проверяем подпись
        if not verify_signature(data, signature):
            print("⚠️ Подпись не совпадает — уведомление отклонено.")
            return web.Response(text="invalid signature", status=403)

        # Проверяем статус оплаты
        if data.get("status") != "success":
            return web.Response(text="not success", status=200)

        # ID пользователя из order_id
        user_id = int(data.get("order_id", 0))
        if not user_id:
            return web.Response(text="no user_id", status=400)

        # Создаём персональную ссылку-приглашение в канал
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID, member_limit=1, name=f"invite_{user_id}"
        )

        await bot.send_message(
            user_id,
            "🎉 Оплата получена!\n\n"
            "Вот твоя персональная ссылка для входа в курс:\n"
            f"👉 {invite.invite_link}"
        )

        print(f"✅ Пользователю {user_id} выдан доступ: {invite.invite_link}")
        return web.Response(text="ok", status=200)

    except Exception as e:
        print(f"❌ Ошибка при обработке уведомления: {e}")
        return web.Response(status=500)


# === Стандартный webhook Telegram ===
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def setup_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/access", handle_access)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    app = setup_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
