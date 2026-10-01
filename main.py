import os
import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN", "8836453685:AAEJHWQHHv3Qni_k9dosQodq0cEUsG7PfSw")

# Majburiy kanallar ro'yxati (Bot ikkala kanalda ham ADMIN bo'lishi shart!)
CHANNELS = [
    "@yuristkonsult0",
    "@Yangirenessansyoshlari"
]

# Yopiq guruh havolasi va kerakli takliflar soni
PRIVATE_GROUP_LINK = "https://t.me/+utM5W-bXIN1lOTk6"
REQUIRED_REFERRALS = 5

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            referral_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, referrer_id, referral_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_user(user_id: int, referrer_id: int = None):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, referrer_id, referral_count) VALUES (?, ?, 0)", (user_id, referrer_id))
    conn.commit()
    conn.close()

def increment_referral(referrer_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    conn.close()

# --- HELPER FUNCTIONS ---
async def check_subscriptions(user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Obuna tekshirishda xatolik ({channel}): {e}")
            return False
    return True

def get_subscribe_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1-kanalga obuna bo'lish 📢", url="https://t.me/yuristkonsult0")],
        [InlineKeyboardButton(text="2-kanalga obuna bo'lish 📢", url="https://t.me/Yangirenessansyoshlari")],
        [InlineKeyboardButton(text="Obunani tekshirish 🔄", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- HANDLERS ---
@dp.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args

    # Referal ID o'g'irlash
    referrer_id = None
    if args and args.isdigit():
        possible_referrer = int(args)
        if possible_referrer != user_id:
            referrer_id = possible_referrer

    user = get_user(user_id)
    if not user:
        add_user(user_id, referrer_id)
        # Agar taklif qilgan odam bo'lsa va obuna bo'lsa
        if referrer_id:
            is_sub = await check_subscriptions(user_id)
            if is_sub:
                increment_referral(referrer_id)

    is_subscribed = await check_subscriptions(user_id)
    if not is_subscribed:
        await message.answer(
            "Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_subscribe_keyboard()
        )
    else:
        await show_main_menu(message, user_id)

async def show_main_menu(message_or_callback, user_id: int):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    user = get_user(user_id)
    ref_count = user[2] if user else 0

    if ref_count >= REQUIRED_REFERRALS:
        text = (
            f"🎉 **Tabriklaymiz!** Siz {ref_count}/{REQUIRED_REFERRALS} ta odam taklif qildingiz.\n\n"
            f"Siz uchun yopiq guruh havolasi ochiq:\n👉 {PRIVATE_GROUP_LINK}"
        )
    else:
        text = (
            f"✅ **Kanallarga obuna bo'lgansiz!**\n\n"
            f"🔒 Yopiq guruhga kirish uchun kamida **{REQUIRED_REFERRALS} ta do'stingizni** taklif qilishingiz kerak.\n\n"
            f"Siz taklif qilgan odamlar soni: **{ref_count} / {REQUIRED_REFERRALS}**\n\n"
            f"Sizning shaxsiy taklif havolangiz:\n`{ref_link}`\n\n"
            f"Ushbu havolani do'stlaringizga yuboring!"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Hisobimni tekshirish 🔄", callback_data="refresh_stats")]
    ])

    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await message_or_callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscriptions(user_id)

    if is_subscribed:
        user = get_user(user_id)
        # Agar yangi a'zo bo'lsa va uni kimdir taklif qilgan bo'lsa, taklif qilganga ochko beramiz
        if user and user[1]: # referrer_id mavjud bo'lsa
            referrer_id = user[1]
            increment_referral(referrer_id)
            # Referrer_id ni tozalash (takroran qo'shilmasligi uchun)
            conn = sqlite3.connect("bot_database.db")
            conn.cursor().execute("UPDATE users SET referrer_id = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()

        await callback.message.delete()
        await show_main_menu(callback, user_id)
    else:
        await callback.answer("Siz hali barcha kanallarga obuna bo'lmadingiz! ❌", show_alert=True)

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats_callback(callback: types.CallbackQuery):
    await show_main_menu(callback, callback.from_user.id)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
