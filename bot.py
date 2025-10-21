import os
import json
import hmac
import hashlib
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === НАСТРОЙКИ ===
TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")  # 🔐 Секретный ключ из личного кабинета Продамус
CHANNEL_ID = -1003189812929  # ID твоего закрытого Telegram-канала
WEBHOOK_URL = "https://zhivoe-lico-bot.onrender.com/webhook"
PRICE = 4500
BASE_URL = "https://nastroikatela.payform.ru/"  # 🔗 твоя личная форма

bot = Bot(token=TOKEN)
dp = Dispatcher()


# === СОЗДАНИЕ ССЫЛКИ НА ОПЛАТУ ===
def create_invoice(tg_id: int) -> str:
    """Формирует ссылку на оплату через твою форму payform.ru"""
    params = {
        "do": "pay",
        "sum": PRICE,
        "order_num": tg_id,
        "name": "Доступ к онлайн-курсу 'Живое лицо'",
        "description": "Онлайн-курс Антония Ланина 'Живое лицо'",
        "success_url": "https://t.me/nastroika_tela",
        "fail_url": "https://t.me/nastroika_tela",
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE_URL}?{query}"


# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    pay_url = create_invoice(tg_id)

    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_url}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)


# === ПРОВЕРКА ПОДПИСИ ===
def verify_signature(raw_body: str, signature: str) -> bool:
    """Проверяет подпись, чтобы убедиться, что запрос пришёл от Продамус"""
    if not signature:
        return False

    expected = hmac.new(
        PRODAMUS_SECRET.encode(),
        msg=raw_body.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


# === ВЫДАЧА ДОСТУПА ПОСЛЕ ОПЛАТЫ ===
async def handle_access(request):
    raw_body = await request.text()
    signature = request.headers.get("Sign")

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        print("⚠️ Некорректный JSON в уведомлении Prodamus")
        return web.Response(text="invalid json", status=400)

    # Проверяем подпись
    if not verify_signature(raw_body, signature):
        print("⚠️ Подпись не совпадает, запрос отклонён")
        return web.Response(text="invalid signature", status=403)

    # Проверяем статус платежа
    if data.get("payment_status") != "success":
        print("⏳ Платёж не завершён:", data)
        return web.Response(text="not success", status=200)

    user_id = data.get("order_num")
    if not user_id:
        return web.Response(text="no user_id", status=400)

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"access_{user_id}",
        )
        await bot.send_message(
            int(user_id),
            f"🎉 Оплата получена!\n\n"
            f"Вот твоя персональная ссылка для входа в курс:\n\n"
            f"{invite.invite_link}",
        )
        print(f"✅ Доступ выдан пользователю {user_id}")
        return web.Response(text="ok", status=200)
    except Exception as e:
        print(f"❌ Ошибка при выдаче ссылки: {e}")
        return web.Response(text="error", status=500)


# === ОБРАБОТКА ВЕБХУКА ОТ TELEGRAM ===
async def handle_webhook(request):
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"⚠️ Ошибка webhook: {e}")
    return web.Response(status=200)


# === СТАРТ СЕРВЕРА ===
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def create_app():
    app = web.Application()
    app.router.add_post("/access", handle_access)
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", lambda _: web.Response(text="ok"))
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
