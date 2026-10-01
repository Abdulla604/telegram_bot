import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# API Tokeningizni va sozlamalarni shu yerga yozing
BOT_TOKEN = os.environ.get("BOT_TOKEN", "BOT_TOKENINGIZNI_SHUYERGA_YOZING")

# Kanallar va Yopiq guruh ID hamda linklari
CHANNEL_1 = "@kanal_username_1"  # Birinchi kanal username (masalan: @my_channel_1)
CHANNEL_2 = "@kanal_username_2"  # Ikkinchi kanal username (masalan: @my_channel_2)
CHANNEL_1_LINK = "https://t.me/kanal_username_1"
CHANNEL_2_LINK = "https://t.me/kanal_username_2"

CLOSED_GROUP_LINK = "https://t.me/+yopiq_guruh_linki"  # Yopiq guruh taklif linki

# Foydalanuvchilar va ularning takliflarini saqlash uchun ma'lumotlar bazasi
users_db = {}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Kanallarga a'zolikni tekshirish funksiyasi
async def check_subscriptions(user_id: int) -> bool:
    for channel in [CHANNEL_1, CHANNEL_2]:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Tekshirishda xatolik ({channel}): {e}")
            return False
    return True

# Tugmalarni yaratish
def get_check_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1-Kanalga a'zo bo'lish", url=CHANNEL_1_LINK)],
            [InlineKeyboardButton(text="2-Kanalga a'zo bo'lish", url=CHANNEL_2_LINK)],
            [InlineKeyboardButton(text="A'zolikni tekshirish ✅", callback_data="check_sub")]
        ]
    )
    return keyboard

# /start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Bazada mavjud bo'lmasa ro'yxatga olamiz
    if user_id not in users_db:
        referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        users_db[user_id] = {"referrer_id": referrer_id, "referrals_count": 0}

    # Kanallarga obunani tekshiramiz
    is_subscribed = await check_subscriptions(user_id)

    if not is_subscribed:
        await message.answer(
            " Botdan foydalanish uchun quyidagi ikkala kanalga a'zo bo'ling va **'A'zolikni tekshirish'** tugmasini bosing:",
            reply_markup=get_check_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await process_referral_system(message)

# Obunani tekshirish tugmasi bosilganda
@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscriptions(user_id)

    if not is_subscribed:
        await callback.answer("❌ Ikkala kanalga ham obuna bo'lmadingiz!", show_alert=True)
    else:
        await callback.message.delete()
        
        # Taklif qilgan insonining hisobiga referal qo'shish
        referrer_id = users_db.get(user_id, {}).get("referrer_id")
        if referrer_id and referrer_id in users_db:
            # O'zini o'zi taklif qilgan bo'lmasa
            if referrer_id != user_id:
                users_db[referrer_id]["referrals_count"] += 1
                users_db[user_id]["referrer_id"] = None  # Qayta hisoblanmasligi uchun o'chirish

        await process_referral_system(callback.message, user_id)

# Referal tizimini ko'rsatish
async def process_referral_system(message: types.Message, user_id: int = None):
    if not user_id:
        user_id = message.from_user.id

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_count = users_db.get(user_id, {}).get("referrals_count", 0)

    if ref_count >= 5:
        text = (
            f" Tabriklaymiz! Siz **{ref_count}/5** ta do'stingizni taklif qildingiz.\n\n"
            f"Yopiq guruhga kirish havolasi: [Yopiq Guruhga Kirish]({CLOSED_GROUP_LINK})"
        )
    else:
        text = (
            f" Yopiq guruhga kirish uchun **5 ta do'stingizni** taklif qilishingiz kerak.\n\n"
            f" Siz taklif qildingiz: **{ref_count} / 5** ta\n\n"
            f"Sizning taklif havolangiz:\n`{ref_link}`\n\n"
            f"Ushbu havolani do'stlaringizga yuboring!"
        )

    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
