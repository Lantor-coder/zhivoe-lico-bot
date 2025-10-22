import os
import hmac
import hashlib
from urllib.parse import urlencode, parse_qs
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")
CHANNEL_LINK = "https://t.me/+YOUR_CHANNEL_INVITE_LINK"  # замени на реальную ссылку-приглашение
PRICE = 4500
BASE_URL = "https://nastroikatela.payform.ru"
WEBHOOK_URL = "https://zhivoe-lico-bot-1.onrender.com/webhook"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


# === Создание ссылки на оплату ===
def create_invoice(tg_id: int) -> str:
    params = {
        "order_num": tg_id,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "do": "pay",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
        "urlSuccess": "https://zhivoe-lico-bot-1.onrender.com/success",
        "urlReturn": "https://zhivoe-lico-bot-1.onrender.com/fail",
    }
    return f"{BASE_URL}?{urlencode(params, doseq=True)}"


# === Проверка подписи Prodamus (точно как Hmac::verify($_POST,...)) ===
def compute_prodamus_signature(secret: str, form_data: dict) -> str:
    sorted_items = sorted(form_data.items())
    message = "&".join(f"{k}={v}" for k, v in sorted_items)
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


# === Команда /start ===
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    pay_link = create_invoice(message.from_user.id)
    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина <b>«Живое лицо»</b>.\n\n"
        f"👉 <a href='{pay_link}'>Перейти к оплате (4500 ₽)</a>\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text, disable_web_page_preview=True)


# === Обработка уведомлений Prodamus ===
async def handle_access(request: web.Request):
    print("📩 Уведомление получено!")
    headers = dict(request.headers)
    raw_sign = headers.get("Sign", "").replace("Sign:", "").strip()

    body = await request.text()
    data = {k: v[0] for k, v in parse_qs(body).items()}

    print("🔹 Parsed data:", data)
    print("🧾 Sign из запроса:", raw_sign)

    expected_signature = compute_prodamus_signature(PRODAMUS_SECRET, data)
    print("🧮 Наш расчёт:", expected_signature)

    if raw_sign != expected_signature:
        print("⚠️ Неверная подпись")
        return web.Response(text="invalid signature", status=403)

    # Если всё ок — отправляем доступ пользователю
    if data.get("payment_status") == "success":
        try:
            user_id = int(data.get("order_num"))
            await bot.send_message(
                user_id,
                f"✅ Оплата получена!\n\nВот ссылка на курс:\n{CHANNEL_LINK}"
            )
            print(f"✅ Сообщение отправлено пользователю {user_id}")
        except Exception as e:
            print(f"❌ Ошибка при отправке сообщения: {e}")

    return web.Response(text="success", status=200)


# === Страницы успеха и ошибки ===
async def success_page(request):
    return web.Response(text="✅ Оплата успешна! Ссылка придёт в Telegram-бот.", content_type="text/html")

async def fail_page(request):
    return web.Response(text="❌ Ошибка оплаты. Попробуйте ещё раз.", content_type="text/html")


# === Настройка приложения и вебхука ===
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def setup_app():
    app = web.Application()
    app.router.add_post("/access", handle_access)
    app.router.add_get("/success", success_page)
    app.router.add_get("/fail", fail_page)
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    web.run_app(setup_app(), host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
