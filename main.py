import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Token muhit o'zgaruvchisidan olinadi, agar bo'lmasa zaxirasi ishlaydi
BOT_TOKEN = os.getenv("BOT_TOKEN", "8836453685:AAEJHWQHHv3Qni_k9dosQodq0cEUsG7PfSw")

# Ochiq kanallar ro'yxati (Bot bu kanallarda ADMIN bo'lishi shart!)
CHANNELS = [
    "@yuristkonsult0",
    "@Yangirenessansyoshlari"
]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Obunani tekshirish funksiyasi
async def check_subscriptions(user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Obunani tekshirishda xatolik ({channel}): {e}")
            return False
    return True

# Obuna tugmalarini yasash
def get_subscribe_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1-kanalga obuna bo'lish 📢", url="https://t.me/yuristkonsult0")],
        [InlineKeyboardButton(text="2-kanalga obuna bo'lish 📢", url="https://t.me/Yangirenessansyoshlari")],
        [InlineKeyboardButton(text="Yopiq guruhga qo'shilish 👥", url="https://t.me/+utM5W-bXIN1lOTk6")],
        [InlineKeyboardButton(text="Tekshirish 🔄", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# /start buyrug'i kelganda
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    is_subscribed = await check_subscriptions(message.from_user.id)
    
    if is_subscribed:
        await message.answer("Xush kelibsiz! Siz barcha kanallarga a'zo bo'lgansiz. 🎉")
    else:
        await message.answer(
            "Botdan foydalanish uchun quyidagi manbalarga a'zo bo'ling:",
            reply_markup=get_subscribe_keyboard()
        )

# "Tekshirish" tugmasi bosilganda
@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    is_subscribed = await check_subscriptions(callback.from_user.id)
    
    if is_subscribed:
        await callback.message.delete()
        await callback.message.answer("Rahmat! Obuna tasdiqlandi. Endi botdan foydalanishingiz mumkin. 🎉")
    else:
        await callback.answer("Siz hali barcha manbalarga a'zo bo'lmadingiz! ❌", show_alert=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
