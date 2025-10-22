import os
import hmac
import hashlib
import json
from urllib.parse import urlencode, parse_qs, unquote_plus
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")  # 🔑 Секретный ключ из личного кабинета Prodamus
BASE_URL = "https://nastroikatela.payform.ru/"
WEBHOOK_URL = "https://zhivoe-lico-bot-1.onrender.com/webhook"
CHANNEL_ID = -1000000000000  # 🔄 замени на ID твоего закрытого канала (можно узнать через @userinfobot)
PRICE = 4500  # стоимость курса

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === Генерация платёжной ссылки ===
def create_invoice(tg_id: int) -> str:
    """Создаёт ссылку Prodamus для оплаты"""
    params = {
        "order_num": tg_id,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "do": "pay",
        "urlSuccess": "https://t.me/nastroika_tela",
        "urlReturn": "https://t.me/nastroika_tela",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
    }
    return f"{BASE_URL}?{urlencode(params, doseq=True)}"

# === Команда /start ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    pay_link = create_invoice(message.from_user.id)
    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 <a href='{pay_link}'>Оплатить курс</a>\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text, disable_web_page_preview=True)

# === Проверка подписи Prodamus ===
def verify_signature(secret: str, raw_body: str, sent_sign: str) -> bool:
    """Проверяет подлинность уведомления от Prodamus"""
    try:
        calculated = hmac.new(
            key=secret.encode(),
            msg=raw_body.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(calculated, sent_sign)
    except Exception as e:
        print("Ошибка при проверке подписи:", e)
        return False

# === Обработка уведомлений об оплате ===
async def handle_access(request: web.Request):
    try:
        raw = await request.text()
        headers = dict(request.headers)
        print("📩 Уведомление получено!")
        print("🔸 Headers:", headers)
        print("🔸 Body:", raw)

        # Парсим тело
        data = {k: unquote_plus(v[0]) for k, v in parse_qs(raw).items()}
        print("🔹 Parsed data:", data)

        # Извлекаем подпись
        raw_sign = headers.get("Sign", "")
        signature = raw_sign.replace("Sign:", "").strip()

        # Проверяем подпись
        expected_signature = hmac.new(
            key=PRODAMUS_SECRET.encode(),
            msg=raw.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        print(f"🧾 Sign из запроса: {signature}")
        print(f"🧮 Наш расчёт: {expected_signature}")

        if signature != expected_signature:
            print("⚠️ Неверная подпись")
            return web.Response(text="invalid signature", status=403)

        # Проверяем статус
        if data.get("payment_status") != "success":
            print(f"ℹ️ Статус не 'success': {data.get('payment_status')}")
            return web.Response(text="not success", status=200)

        # Получаем Telegram ID
        user_id = int(data.get("order_num", 0))
        if not user_id:
            print("⚠️ Нет user_id (order_num)")
            return web.Response(text="no user_id", status=400)

        # Создаём одноразовую ссылку на канал
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID, member_limit=1, name=f"invite_{user_id}"
        )
        await bot.send_message(
            user_id,
            f"🎉 Оплата получена!\n\nВот твоя ссылка на курс:\n{invite.invite_link}"
        )
        print(f"✅ Ссылка выдана пользователю {user_id}")

        return web.Response(text="ok", status=200)

    except Exception as e:
        print("❌ Ошибка при обработке уведомления:", e)
        return web.Response(status=500)

# === Настройка вебхука ===
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

# === Приложение aiohttp ===
def setup_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/access", handle_access)
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app

# === Запуск ===
if __name__ == "__main__":
    app = setup_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
