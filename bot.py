import asyncio
import hashlib
import hmac
import os
from urllib.parse import parse_qs
from aiohttp import web
from aiogram import Bot, Dispatcher, types

# --- Конфигурация ---
TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")  # тот самый секрет из Prodamus
CHANNEL_LINK = "https://t.me/+xxxxxxxxxxxx"     # сюда дать доступ после оплаты
PRICE = 4500
BASE_URL = "https://nastroikatela.payform.ru"   # твоя страница Prodamus

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- Утилита: создаём ссылку на оплату ---
from urllib.parse import urlencode

def create_invoice(tg_id: int) -> str:
    """Создаёт ссылку Prodamus для оплаты"""
    params = {
        "order_num": tg_id,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "do": "pay",
        "urlSuccess": "https://zhivoe-lico-bot-1.onrender.com/success",
        "urlReturn": "https://zhivoe-lico-bot-1.onrender.com/fail",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
    }
    return f"{BASE_URL}?{urlencode(params, doseq=True)}"


# --- Проверка подписи по правилам Prodamus ---
def compute_prodamus_signature(secret: str, form_data: dict) -> str:
    """Формирует подпись в точности как у Prodamus (аналог Hmac::verify($_POST,...))"""
    sorted_items = sorted(form_data.items())
    message = "&".join(f"{k}={v}" for k, v in sorted_items)
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


# --- Хэндлер старта ---
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    link = create_invoice(message.from_user.id)
    await message.answer(
        "💳 Для доступа к курсу «Живое лицо» нажми на кнопку ниже:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Оплатить 4500₽", url=link)
        )
    )


# --- Обработчик вебхука от Prodamus ---
async def handle_access(request: web.Request):
    print("📩 Уведомление получено!")

    headers = dict(request.headers)
    raw_sign = headers.get("Sign", "")
    signature = raw_sign.replace("Sign:", "").strip()

    body = await request.text()
    data = {k: v[0] for k, v in parse_qs(body).items()}

    print("🔹 Parsed data:", data)
    print("🧾 Sign из запроса:", signature)

    expected_signature = compute_prodamus_signature(PRODAMUS_SECRET, data)
    print("🧮 Наш расчёт:", expected_signature)

    if signature != expected_signature:
        print("⚠️ Неверная подпись")
        return web.Response(text="invalid signature", status=403)

    # Проверяем успешную оплату
    if data.get("payment_status") == "success":
        order_num = data.get("order_num")
        try:
            user_id = int(order_num)
            await bot.send_message(
                user_id,
                f"✅ Оплата получена!\n\nВот ссылка на канал с курсом:\n{CHANNEL_LINK}"
            )
            print(f"✅ Сообщение отправлено пользователю {user_id}")
        except Exception as e:
            print(f"❌ Ошибка при отправке пользователю: {e}")

    return web.Response(text="success", status=200)


# --- Вспомогательные эндпоинты ---
async def success_page(request):
    return web.Response(text="✅ Оплата успешна! Ссылка на курс придёт в ваш Telegram.", content_type="text/html")

async def fail_page(request):
    return web.Response(text="❌ Ошибка оплаты. Попробуйте ещё раз.", content_type="text/html")


# --- Запуск веб-сервера и бота ---
async def on_startup(app):
    webhook_url = "https://zhivoe-lico-bot-1.onrender.com/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook установлен: {webhook_url}")

app = web.Application()
app.router.add_post("/access", handle_access)
app.router.add_get("/success", success_page)
app.router.add_get("/fail", fail_page)

app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
