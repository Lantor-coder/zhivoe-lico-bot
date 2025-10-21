import os
import json
import hmac
import hashlib
from typing import Optional

import requests
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_API_KEY = os.getenv("PRODAMUS_API_KEY")
CHANNEL_ID = -1003189812929
WEBHOOK_URL = "https://zhivoe-lico-bot.onrender.com/webhook"  # ← твой Render-домен
PRICE = 4500

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

if not PRODAMUS_API_KEY:
    raise RuntimeError("PRODAMUS_API_KEY environment variable is not set")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === СОЗДАНИЕ ССЫЛКИ НА ОПЛАТУ ===
def create_invoice(tg_id: int):
    url = "https://prodamus.com/api/v1/invoice"
    headers = {"Authorization": f"Bearer {PRODAMUS_API_KEY}"}
    payload = {
        "sum": PRICE,
        "currency": "rub",
        "order_num": str(tg_id),
        "type": "course",  # обязательный параметр
        "name": "Доступ к онлайн-курсу 'Живое лицо'",
        "description": "Онлайн-курс Антония Ланина 'Живое лицо'",
        "success_url": "https://t.me/nastroika_tela",
        "fail_url": "https://t.me/nastroika_tela",
        "do": "pay",
    }

    res = requests.post(url, headers=headers, json=payload)
    if not res.ok:
        print(f"⚠️ Ошибка Prodamus API: {res.status_code} → {res.text}")
        return None

    try:
        data = res.json()
        return data.get("url") or data.get("payment_link")
    except Exception as e:
        print(f"⚠️ Ошибка парсинга ответа Prodamus: {e}")
        return None


# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    pay_url = create_invoice(tg_id)

    if not pay_url:
        await message.answer("⚠️ Ошибка при создании ссылки на оплату. Попробуй позже.")
        return

    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_url}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)


# === ПРОВЕРКА ПОДПИСИ ОТ PRODAMUS ===
def verify_signature(raw_body: str, signature: Optional[str]) -> bool:
    if not signature:
        return False

    expected = hmac.new(
        PRODAMUS_API_KEY.encode(),
        msg=raw_body.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    clean_signature = signature.strip().lower()
    return hmac.compare_digest(expected, clean_signature)


# === ВЫДАЧА ССЫЛКИ ПОСЛЕ ОПЛАТЫ ===
async def handle_access(request):
    raw_body = await request.text()
    signature = request.headers.get("Sign")

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        print("⚠️ Некорректный JSON в уведомлении Prodamus")
        return web.Response(text="invalid json", status=400)

    if not verify_signature(raw_body, signature):
        print("⚠️ Подпись не совпадает, запрос отклонён")
        return web.Response(text="invalid signature", status=403)

    if data.get("payment_status") != "success":
        return web.Response(text="not success", status=200)

    user_id = data.get("order_num")
    if not user_id:
        return web.Response(text="no user_id", status=400)

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        print(f"⚠️ Некорректный order_num: {user_id}")
        return web.Response(text="invalid user_id", status=400)

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID, member_limit=1, name=f"access_{user_id}"
        )
        message_text = (
            "🎉 Оплата получена!\n\n"
            "Вот твоя персональная ссылка для входа в курс:\n\n"
            f"{invite.invite_link}"
        )
        await bot.send_message(user_id_int, message_text)
        print(f"✅ Доступ выдан пользователю {user_id}")
        return web.Response(text="ok", status=200)
    except Exception as e:
        print(f"Ошибка при выдаче ссылки: {e}")
        return web.Response(text="error", status=500)


# === WEBHOOK ===
async def handle_webhook(request):
    """Обрабатывает входящие обновления от Telegram"""
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"⚠️ Ошибка webhook: {e}")
    return web.Response(status=200)


# === СТАРТ СЕРВЕРА ===
async def on_startup(app):
    # Удалим старый webhook (если есть)
    await bot.delete_webhook(drop_pending_updates=True)
    # Установим новый webhook
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def create_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_post("/access", handle_access)
    app.router.add_get("/", lambda _: web.Response(text="ok"))
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

