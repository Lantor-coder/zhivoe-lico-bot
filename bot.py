import os
import hmac
import hashlib
import json
from urllib.parse import urlencode
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === Константы ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRODAMUS_SECRET = os.getenv("PRODAMUS_SECRET")
BASE_URL = "https://nastroikatela.payform.ru/"
PRICE = 4500  # цена курса
WEBHOOK_URL = "https://zhivoe-lico-bot.onrender.com/webhook"

bot = Bot(token=BOT_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# === Генерация HMAC-подписанной ссылки на оплату ===
def create_invoice(tg_id: int) -> str:
    """Создаёт платёжную ссылку Prodamus со всеми параметрами и подписью"""
    data = {
        "order_id": tg_id,
        "customer_phone": "",
        "customer_email": "",
        "products": [
            {
                "name": "Онлайн-курс 'Живое лицо'",
                "price": PRICE,
                "quantity": 1,
                "tax": {"tax_type": 0},
                "paymentMethod": 1,
                "paymentObject": 4,
            }
        ],
        "do": "pay",
        "urlSuccess": "https://t.me/nastroika_tela",
        "urlReturn": "https://t.me/nastroika_tela",
        "urlNotification": "https://zhivoe-lico-bot.onrender.com/access",
        "customer_extra": "Оплата курса 'Живое лицо'",
        "npd_income_type": "FROM_INDIVIDUAL",
    }

    json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    signature = hmac.new(
        PRODAMUS_SECRET.encode(),
        msg=json_data.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    data["signature"] = signature

    query = urlencode({"data": json.dumps(data, ensure_ascii=False)}, doseq=True)
    return f"{BASE_URL}?{query}"


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


# === Обработка уведомления от Prodamus ===
async def handle_access(request: web.Request):
    """Webhook от Prodamus после успешной оплаты"""
    try:
        data = await request.json()
        order_id = data.get("order_id")
        payment_status = data.get("status")

        if payment_status == "success" and order_id:
            chat_id = int(order_id)
            await bot.send_message(
                chat_id,
                "✅ Оплата получена!\n\n"
                "Вот ссылка на закрытый Telegram-канал:\n"
                "👉 https://t.me/+YourPrivateChannelInviteLink"
            )
        return web.Response(status=200)
    except Exception as e:
        print("Ошибка при обработке уведомления:", e)
        return web.Response(status=500)


# === Настройка вебхука ===
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


def setup_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/access", handle_access)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app


# === Точка входа ===
if __name__ == "__main__":
    app = setup_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
