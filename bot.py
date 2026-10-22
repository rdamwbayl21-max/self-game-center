import os
import random
import sqlite3
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
TOKEN = os.environ["BOT_TOKEN"]
DB = sqlite3.connect("game.db", check_same_thread=False)
DB.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    coins INTEGER DEFAULT 0,
    last_daily TEXT DEFAULT ''
)
""")
DB.commit()
def get_user(user):
    name = user.first_name or "بازیکن"
    DB.execute(
        "INSERT OR IGNORE INTO users(user_id, name) VALUES (?, ?)",
        (user.id, name)
    )
    DB.execute("UPDATE users SET name=? WHERE user_id=?", (name, user.id))
    DB.commit()
    return DB.execute(
        "SELECT coins, last_daily FROM users WHERE user_id=?",
        (user.id,)
    ).fetchone()
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 بازی‌ها", callback_data="games")],
        [
            InlineKeyboardButton("💰 موجودی من", callback_data="balance"),
            InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily")
        ],
        [InlineKeyboardButton("🏆 جدول امتیازات", callback_data="top")]
    ])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user)
    await update.effective_message.reply_text(
        "🎮 به Self Game Center خوش اومدی!\n"
        "بازی کن، سکه جمع کن و رکورد بزن! 🏆",
        reply_markup=main_menu()
    )
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    coins, last_daily = get_user(user)
    if q.data == "balance":
        await q.message.reply_text(f"💰 موجودی تو: {coins} سکه")
    elif q.data == "daily":
        today = date.today().isoformat()
        if last_daily == today:
            await q.message.reply_text("🎁 جایزه امروزت رو قبلاً گرفتی!")
        else:
            DB.execute(
                "UPDATE users SET coins=coins+10, last_daily=? WHERE user_id=?",
                (today, user.id)
            )
            DB.commit()
            await q.message.reply_text("🎉 ۱۰ سکه جایزه گرفتی!")
    elif q.data == "games":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎲 حدس عدد", callback_data="guess")
        ]])
        await q.message.reply_text("یک بازی انتخاب کن:", reply_markup=keyboard)
    elif q.data == "guess":
        context.user_data["guess_number"] = random.randint(1, 5)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(str(n), callback_data=f"pick:{n}")
            for n in range(1, 6)
        ]])
        await q.message.reply_text(
            "🎲 عدد مخفی بین ۱ تا ۵ رو حدس بزن!",
            reply_markup=keyboard
        )
    elif q.data.startswith("pick:"):
        chosen = int(q.data.split(":")[1])
        secret = context.user_data.pop("guess_number", None)
        if secret is None:
            await q.message.reply_text("برای شروع، دوباره بازی حدس عدد رو باز کن.")
        elif chosen == secret:
            DB.execute(
                "UPDATE users SET coins=coins+5 WHERE user_id=?",
                (user.id,)
            )
            DB.commit()
            await q.message.reply_text("🎉 درست حدس زدی! ۵ سکه گرفتی.")
        else:
            await q.message.reply_text(f"😄 این بار نشد! عدد درست {secret} بود.")
    elif q.data == "top":
        rows = DB.execute(
            "SELECT name, coins FROM users ORDER BY coins DESC LIMIT 10"
        ).fetchall()
        if not rows:
            await q.message.reply_text("هنوز امتیازی ثبت نشده.")
        else:
            result = "🏆 جدول امتیازات:\n\n"
            result += "\n".join(
                f"{i}. {name}: {coins} سکه"
                for i, (name, coins) in enumerate(rows, 1)
            )
            await q.message.reply_text(result)
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()
if __name__ == "__main__":
    main()
