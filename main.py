import os
import logging
import threading
import datetime
import sqlite3
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# 1. Setup Logging & Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

# 2. Database Setup (សម្រាប់កត់ទុក ID អ្នកប្រើប្រាស់)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # រក្សាទុកតែ user_id បានហើយ ព្រោះយើងមិនបាច់បិទ Ads ជារៀងរហូតទេ
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def register_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# 3. មុខងារផ្ញើ Ads (២ ដងក្នុងមួយថ្ងៃ)
async def send_broadcast_ads(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    active_users = c.fetchall()
    conn.close()

    ad_text = "📢 *ការផ្សព្វផ្សាយពាណិជ្ជកម្ម*\n\nសូមស្វាគមន៍មកកាន់សេវាកម្មរបស់យើង! សូមចុចប៊ូតុងខាងក្រោមសម្រាប់ព័ត៌មានបន្ថែម។"
    
    # ប៊ូតុង Ads និងប៊ូតុង "បិទ"
    keyboard = [
        [InlineKeyboardButton("🔗 ចូលទៅកាន់គេហទំព័រ", url="https://yourlink.com")],
        [InlineKeyboardButton("❌ បិទការបង្ហាញ (Close)", callback_data="close_ad")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for user in active_users:
        try:
            await context.bot.send_message(
                chat_id=user[0], 
                text=ad_text, 
                reply_markup=reply_markup, 
                parse_mode="Markdown"
            )
        except Exception:
            continue

# 4. Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)
    await update.message.reply_text("សួស្តី! សូមផ្ញើរូបភាពមកដើម្បីស្វែងរកប្រភព។")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # នៅពេល User ចុចប៊ូតុង "បិទ"
    if query.data == "close_ad":
        try:
            await query.message.delete() # លុបសារ Ads នោះចោល
            await query.answer("Ads ត្រូវបានបិទ")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

# 5. Main Function
def main():
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # កំណត់ម៉ោងផ្ញើ Ads ២ ដងក្នុងមួយថ្ងៃ (ម៉ោង ៨ ព្រឹក និង ៨ យប់)
    timezone = pytz.timezone("Asia/Phnom_Penh")
    job_queue = app.job_queue
    
    # បាញ់ Ads ម៉ោង ៨ ព្រឹក
    job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=8, minute=0, tzinfo=timezone))
    # បាញ់ Ads ម៉ោង ៨ យប់
    job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=20, minute=0, tzinfo=timezone))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    # កុំភ្លេច add_handler សម្រាប់ handle_photo របស់បងពីកូដមុនចូលទីនេះផង...
    
    app.run_polling()

if __name__ == '__main__':
    main()
