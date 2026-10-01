import os
import logging
import asyncio
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# TO'G'RI TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN", "8836453685:AAH-98gMP_sWlhgN_PT9PQoH_jKCN25lEsw")

# ADMIN ID
ADMIN_ID = 6505527953  

CHANNELS = [
    "@yuristkonsult0",
    "@Yangirenessansyoshlari"
]

PRIVATE_GROUP_LINK = "https://t.me/+utM5W-bXIN1lOTk6"
REQUIRED_REFERRALS = 5
DB_NAME = "bot_database.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- DATABASE MANAGEMENT ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            invited_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            is_confirmed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def register_user(user_id: int, referrer_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
    
    if referrer_id and referrer_id != user_id:
        cursor.execute("INSERT OR IGNORE INTO referrals (invited_id, referrer_id, is_confirmed) VALUES (?, ?, 0)", (user_id, referrer_id))
    
    conn.commit()
    conn.close()

def confirm_referral(invited_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT referrer_id FROM referrals WHERE invited_id = ?", (invited_id,))
    row = cursor.fetchone()
    
    referrer_id = None
    if row:
        referrer_id = row[0]
        cursor.execute("UPDATE referrals SET is_confirmed = 1 WHERE invited_id = ?", (invited_id,))
        conn.commit()
    
    conn.close()
    return referrer_id

async def count_valid_referrals(referrer_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND is_confirmed = 1", (referrer_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# --- CHECK SUBSCRIPTION ---
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

# --- HELP COMMAND ---
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    text = (
        "❓ **Yordam va ko'rsatmalar:**\n\n"
        "Bot bo'yicha savollar yoki texnik muammolar yuzasidan adminga murojaat qilishingiz mumkin:\n"
        "👉 @prepgrants"
    )
    await message.answer(text, parse_mode="Markdown")

# --- ADMIN XABAR YUBORISH BUYRUG'I ---
@dp.message(Command("send"))
async def broadcast_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text_to_send = message.text.replace("/send", "").strip()
    
    if not text_to_send:
        await message.answer(
            "⚠️️ Iltimos, buyruqdan keyin yubormoqchi bo'lgan xabaringizni yozing.\n\n"
            "Masalan:\n`/send Texnik muammo uchun uzr so'raymiz !!! Botdan foydalanishingiz mumkin`", 
            parse_mode="Markdown"
        )
        return

    users = get_all_users()
    success_count = 0
    fail_count = 0

    await message.answer(f"📢 Xabar yuborish boshlandi. Bazadagi barcha foydalanuvchilar soni: **{len(users)}**...")

    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text_to_send, parse_mode="Markdown")
            success_count += 1
            await asyncio.sleep(0.05)
        except TelegramForbiddenError:
            fail_count += 1
        except Exception as e:
            logging.error(f"{user_id} ga xabar yuborishda xatolik: {e}")
            fail_count += 1

    await message.answer(
        f"✅ **Xabar yuborish yakunlandi!**\n\n"
        f"🎯 Yetib bordi: **{success_count}**\n"
        f"❌ Yetib bormadi (botni bloklaganlar): **{fail_count}**",
        parse_mode="Markdown"
    )

# --- HANDLERS ---
@dp.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args

    referrer_id = None
    if args and args.isdigit():
        possible_referrer = int(args)
        if possible_referrer != user_id:
            referrer_id = possible_referrer

    register_user(user_id, referrer_id)

    is_subscribed = await check_subscriptions(user_id)
    if not is_subscribed:
        await message.answer(
            "Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_subscribe_keyboard()
        )
    else:
        await show_main_menu(message, user_id)

async def show_main_menu(target, user_id: int):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    ref_count = await count_valid_referrals(user_id)

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

    if isinstance(target, types.Message):
        await target.answer(text, parse_mode="Markdown", reply_markup=kb)
    else:
        try:
            await target.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        except TelegramBadRequest:
            await target.message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscriptions(user_id)

    if is_subscribed:
        referrer_id = confirm_referral(user_id)
        
        if referrer_id:
            new_count = await count_valid_referrals(referrer_id)
            try:
                await bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 **Bitta do'stingiz kanallarga obuna bo'ldi!**\nSiz taklif qilgan jami do'stlar soni: **{new_count} / {REQUIRED_REFERRALS}**",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Bildirishnoma yuborishda xatolik: {e}")

        try:
            await callback.message.delete()
        except Exception:
            pass
            
        await show_main_menu(callback, user_id)
    else:
        await callback.answer("Siz hali barcha kanallarga obuna bo'lmadingiz! ❌", show_alert=True)

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats_callback(callback: types.CallbackQuery):
    await show_main_menu(callback, callback.from_user.id)

# --- WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va ko'rsatmalar")
    ]
    await bot.set_my_commands(commands)

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await setup_bot_commands()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
