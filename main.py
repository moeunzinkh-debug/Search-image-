import os
import logging
import threading
import datetime
import sqlite3
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Setup Logging & Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

# 2. Database Setup (សម្រាប់ទុក ID អ្នកប្រើប្រាស់ និងការកំណត់ Ads)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, ads_enabled INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

def register_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def update_ads_status(user_id, status):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET ads_enabled = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

# 3. មុខងារផ្ញើ Ads (២ ដងក្នុងមួយថ្ងៃ)
async def send_broadcast_ads(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE ads_enabled = 1')
    active_users = c.fetchall()
    conn.close()

    ad_text = "📢 *ការផ្សព្វផ្សាយពិសេស:* សូមកុំភ្លេចចូលមើល Channel របស់យើងសម្រាប់ទំនិញថ្មីៗ!"
    keyboard = [
        [InlineKeyboardButton("🔗 ចូលមើលឥឡូវនេះ", url="https://t.me/YourChannel")],
        [InlineKeyboardButton("❌ បិទការរំលឹក (Stop Ads)", callback_data="stop_ads")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for user in active_users:
        try:
            await context.bot.send_message(chat_id=user[0], text=ad_text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            continue # បើ User block bot វានឹងរំលង

# 4. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)
    await update.message.reply_text("សួស្តី! សូមផ្ញើរូបភាពមកដើម្បីស្វែងរក។")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "stop_ads":
        update_ads_status(query.from_user.id, 0)
        await query.answer("បិទការរំលឹកជោគជ័យ!")
        await query.edit_message_text("✅ អ្នកបានបិទការរំលឹក Ads រួចរាល់។ អ្នកនៅតែអាចប្រើ Bot ស្វែងរករូបភាពបានធម្មតា។")

# 5. Main Function
def main():
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # កំណត់ម៉ោងផ្ញើ Ads ២ ដងក្នុងមួយថ្ងៃ (ម៉ោង ៨ ព្រឹក និង ៨ យប់)
    timezone = pytz.timezone("Asia/Phnom_Penh")
    job_queue = app.job_queue
    job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=8, minute=0, tzinfo=timezone))
    job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=20, minute=0, tzinfo=timezone))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo)) # ប្រើ handle_photo ពីកូដមុន
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    app.run_polling()

if __name__ == '__main__':
    main()
