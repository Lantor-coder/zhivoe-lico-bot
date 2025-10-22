import os
import json
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://nastroikatela.payform.ru/"  # твоя форма Prodamus
WEBHOOK_URL = "https://zhivoe-lico-bot-1.onrender.com/webhook"
PRICE = 4500  # стоимость курса

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# === Генерация платёжной ссылки через do=link ===
async def create_payment_link(order_id: int) -> str:
    """Создаёт короткую платёжную ссылку через Prodamus API"""
    payload = {
        "do": "link",
        "order_id": order_id,
        "products[0][name]": "Онлайн-курс 'Живое лицо'",
        "products[0][price]": PRICE,
        "products[0][quantity]": 1,
        "customer_extra": "Оплата курса 'Живое лицо'",
        "urlSuccess": "https://t.me/nastroika_tela",
        "urlReturn": "https://t.me/nastroika_tela",
        "urlNotification": "https://zhivoe-lico-bot-1.onrender.com/access",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL, data=payload) as resp:
            link = await resp.text()
            print(f"📎 Ответ Prodamus: {link}")
            return link.strip()


# === Обработка команды /start ===
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
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text, disable_web_page_preview=True)


# === Обработка уведомлений о платеже ===
async def handle_access(request: web.Request):
    try:
        data = await request.json()
        print(f"📩 Уведомление от Prodamus: {data}")
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
        print("❌ Ошибка при обработке уведомления:", e)
        return web.Response(status=500)


# === Установка webhook ===
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")


# === Настройка aiohttp-приложения ===
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
