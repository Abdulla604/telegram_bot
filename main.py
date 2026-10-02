import os
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# 1. ATROF-MUHIT O'ZGARUVCHILARI VA SOZLAMALAR
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6505527953

# Bot ADMIN bo'lgan va API orqali avtomatik tekshiriladigan kanal
ADMIN_CHANNELS = ["@yuristkonsult0"]
CHANNELS = ADMIN_CHANNELS  # NameError xatosining oldini olish uchun

# Qo'lda ulanadigan 2-kanal va taklif havolalari
SECOND_CHANNEL_LINK = "https://t.me/Yangirenessansyoshlari"
PRIVATE_GROUP_LINK = "https://t.me/+utM5W-bXIN1lOTk6"

REQUIRED_REFERRALS = 5
DB_NAME = "bot_database.db"

# Bot va Dispatcher ob'ektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# 2. MA'LUMOTLAR BAZASI (SQLITE) BILAN ISHLASH
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            referrals_count INTEGER DEFAULT 0,
            has_bought INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()


def add_user(user_id: int, referrer_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()
    conn.close()


def get_user_data(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT referrals_count, has_bought FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (0, 0)


# 3. OBUNA VA TUGMALARNI SOZLASH
async def check_subscriptions(user_id: int) -> bool:
    for channel in ADMIN_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Obuna tekshirishda xatolik ({channel}): {e}")
            return False
    return True


def get_subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-kanalga obuna bo'lish 📢", url="https://t.me/yuristkonsult0")],
        [InlineKeyboardButton(text="2-kanalga obuna bo'lish 📢", url=SECOND_CHANNEL_LINK)],
        [InlineKeyboardButton(text="Obunani tekshirish 🔄", callback_data="check_sub")]
    ])
    return keyboard


# 4. HANDLERLAR (BUYRUQLAR VA TUGMALAR)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    add_user(user_id, referrer_id)
    is_subscribed = await check_subscriptions(user_id)

    if is_subscribed:
        ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
        refs_count, _ = get_user_data(user_id)
        
        await message.answer(
            f"Xush kelibsiz! 👋\n\n"
            f"🔗 Sizning referal havolangiz:\n`{ref_link}`\n\n"
            f"👥 Siz taklif qilgan do'stlar: **{refs_count}**/5\n\n"
            f"Botdan to'liq foydalanishingiz mumkin!",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_subscribe_keyboard()
        )


@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscriptions(user_id):
        await callback.message.delete()
        await callback.message.answer("Rahmat! Obunangiz tasdiqlandi. /start buyrug'ini bosing.")
    else:
        await callback.answer("Siz hali 1-kanalga obuna bo'lmadingiz!", show_alert=True)


@dp.message(Command("buy_guide"))
async def buy_guide_handler(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    # Adminga so'rov yuborish
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"approve_{user_id}")]
    ])
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💳 **Yangi to'lov so'rovi!**\nFoydalanuvchi: {user_name} (`{user_id}`)",
        reply_markup=admin_keyboard,
        parse_mode="Markdown"
    )
    
    await message.answer("To'lov so'rovingiz adminga yuborildi. Tasdiqlangach PDF qo'llanma yuboriladi.")


@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    target_user_id = int(callback.data.split("_")[1])
    
    # Bazada statusni yangilash
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET has_bought = 1 WHERE user_id = ?", (target_user_id,))
    conn.commit()
    conn.close()

    # Foydalanuvchiga xabar yuborish
    await bot.send_message(
        chat_id=target_user_id,
        text=f"To'lovingiz tasdiqlandi! 🎉\nPDF qo'llanma va yopiq guruh havolasi: {PRIVATE_GROUP_LINK}"
    )
    
    await callback.message.edit_text("To'lov tasdiqlandi va foydalanuvchiga xabar yuborildi ✅")


# 5. BOTNI ISHGA TUSHIRISH
if __name__ == "__main__":
    import asyncio
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())
