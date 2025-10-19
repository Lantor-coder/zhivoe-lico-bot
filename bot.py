from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003189812929
PRODAMUS_LINK = "https://payform.ru/cd9qXh7/"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    tg_id = message.from_user.id
    pay_link = f"{PRODAMUS_LINK}?custom_fields[telegram_id]={tg_id}"
    text = (
        "Привет 🌿\n\n"
        "Я помогу тебе оплатить и получить доступ к онлайн-курсу Антония Ланина «Живое лицо».\n\n"
        f"👉 Оплата по ссылке:\n{pay_link}\n\n"
        "После оплаты бот автоматически пришлёт ссылку на закрытый канал 💫"
    )
    await message.answer(text)

@dp.message_handler(commands=["access"])
async def give_access(message: types.Message):
    try:
        invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await message.answer(
            f"🎉 Оплата получена!\nВот ссылка на закрытый канал:\n{invite_link.invite_link}"
        )
    except Exception:
        await message.answer("Ошибка при выдаче доступа 😔. Напиши администратору.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
