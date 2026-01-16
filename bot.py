import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(TOKEN)
dp = Dispatcher()

# ---------- БАЗА ----------
db = sqlite3.connect("database.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    blocked INTEGER DEFAULT 0
)
""")
db.commit()


def is_blocked(user_id: int) -> bool:
    cur.execute("SELECT blocked FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row and row[0] == 1


# ---------- USER ----------
@dp.message(Command("start"))
async def start(message: Message):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()
    await message.answer("✉️ Напиши сообщение. Администратор ответит анонимно.")


@dp.message(F.from_user.id != ADMIN_ID)
async def user_message(message: Message):
    if is_blocked(message.from_user.id):
        await message.answer("🚫 Вы заблокированы.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✉ Ответить", callback_data=f"reply:{message.from_user.id}"),
            InlineKeyboardButton(text="🚫 Блок", callback_data=f"block:{message.from_user.id}")
        ]
    ])

    await bot.send_message(
        ADMIN_ID,
        f"👤 Аноним\nID: {message.from_user.id}\n\n{message.text}",
        reply_markup=kb
    )


# ---------- ADMIN ----------
@dp.callback_query(F.data.startswith("block:"))
async def block_user(call: CallbackQuery):
    uid = int(call.data.split(":")[1])
    cur.execute("UPDATE users SET blocked=1 WHERE user_id=?", (uid,))
    db.commit()
    await call.answer("Пользователь заблокирован")
    await bot.send_message(uid, "🚫 Вы заблокированы администратором.")


@dp.callback_query(F.data.startswith("reply:"))
async def reply_request(call: CallbackQuery):
    uid = int(call.data.split(":")[1])
    await call.message.answer(f"✍ Ответь на сообщение (ID {uid})\nНапиши текст и ответ уйдёт анонимно.")

    @dp.message(F.from_user.id == ADMIN_ID)
    async def send_reply(message: Message):
        await bot.send_message(uid, f"📩 Ответ:\n{message.text}")
        dp.message.handlers.remove(send_reply)


# ---------- START ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

