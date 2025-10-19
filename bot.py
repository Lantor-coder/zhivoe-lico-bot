import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003189812929
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Aiogram handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    pay_link = f"{PRODAMUS_LINK}?custom_fields[telegram_id]={tg_id}"
    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_link}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)


@dp.message(Command("access"))
async def cmd_access(message: types.Message):
    try:
        invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await message.answer(
            f"🎉 Оплата получена!\nВот ссылка на закрытый канал:\n{invite_link.invite_link}"
        )
    except Exception as e:
        await message.answer(f"Ошибка при выдаче доступа 😔\n{e}")


# --- HTTP "псевдо-сервер", чтобы Render не выключал сервис ---
async def handle(request):
    return web.Response(text="ok")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP dummy server running on port {port}")



from aiohttp import web

# --- ручка для n8n ---
async def handle_access(request):
    data = await request.json()
    user_id = data.get("telegram_id")
    if not user_id:
        return web.Response(text="No telegram_id", status=400)

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
        return web.Response(text="ok", status=200)

    except Exception as e:
        return web.Response(text=str(e), status=500)


# --- добавляем маршрут в aiohttp ---
async def run_dummy_server():
    app = web.Application()
    app.router.add_post("/access", handle_access)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Webhook server running on port 8080")


# --- Webhook для n8n ---
from aiohttp import web

async def handle_access(request):
    data = await request.json()
    user_id = data.get("telegram_id")
    if not user_id:
        return web.Response(text="No telegram_id", status=400)

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
        return web.Response(text="ok", status=200)

    except Exception as e:
        return web.Response(text=str(e), status=500)


async def run_dummy_server():
    
    app = web.Application()
    app.router.add_post("/access", handle_access)  # ← вот этот маршрут нужен!
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Webhook server running on port 8080")


# --- Главный запуск ---
async def main():
    await asyncio.gather(
        start_web_server(),   # сервер для Render
        dp.start_polling(bot) # aiogram
    )

if __name__ == "__main__":
    asyncio.run(main())



# --- ДОБАВЛЯЕМ В КОНЕЦ ФАЙЛА ---

from aiogram.filters import Command

CHANNEL_ID = -1003189812929  # ID твоего закрытого канала

@dp.message(Command("access"))
async def access_message(message: types.Message):
    try:
        # создаём персональную одноразовую ссылку на канал
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"access_{message.from_user.id}",
            member_limit=1,   # только для одного человека
            expire_date=None  # без срока действия
        )

        await message.answer(
            f"🎉 Оплата получена!\n\n"
            f"Вот ваша персональная ссылка для входа в курс:\n\n"
            f"{invite_link.invite_link}"
        )

    except Exception as e:
        await message.answer(f"⚠️ Ошибка при создании ссылки: {e}")



# Ловим если n8n прислал просто текст "/access"
@dp.message(lambda message: message.text == "/access")
async def access_text_message(message: types.Message):
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"access_{message.from_user.id}",
            member_limit=1,
            expire_date=None
        )

        await message.answer(
            f"🎉 Оплата получена!\n\n"
            f"Вот ваша персональная ссылка для входа в курс:\n\n"
            f"{invite_link.invite_link}"
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при создании ссылки: {e}")



from aiohttp import web
import threading

async def handle_access(request):
    data = await request.json()
    user_id = data.get("telegram_id")
    if not user_id:
        return web.Response(text="No telegram_id", status=400)

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
        return web.Response(text="ok", status=200)
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def run_web_server():
    app = web.Application()
    app.router.add_post("/access", handle_access)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)  # порт можно любой (Render сам найдёт)
    await site.start()
    print("✅ Webhook server started at /access")

def start_web_server():
    asyncio.run(run_web_server())

if __name__ == "__main__":
    # запускаем aiohttp сервер в отдельном потоке
    threading.Thread(target=start_web_server, daemon=True).start()

    # запускаем aiogram
    asyncio.run(main())





