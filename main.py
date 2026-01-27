import os
import logging
import threading
import datetime
import sqlite3
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# 1. កំណត់ Logging & Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

# 2. ការគ្រប់គ្រង Database (SQLite)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def register_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# 3. មុខងារផ្សាយ Ads (២ ដងក្នុងមួយថ្ងៃ)
async def send_broadcast_ads(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    active_users = c.fetchall()
    conn.close()

    ad_text = "📢 *ការផ្សព្វផ្សាយពាណិជ្ជកម្មប្រចាំថ្ងៃ*\n\nសូមអរគុណដែលបានប្រើប្រាស់បូតរបស់យើង! សូមកុំភ្លេចចូលរួមជាមួយ Channel របស់យើងដើម្បីទទួលបានព័ត៌មានថ្មីៗ។"
    
    keyboard = [
        [InlineKeyboardButton("🔗 ចូលទៅកាន់ Channel", url="https://t.me/YourChannel")],
        [InlineKeyboardButton("❌ បិទ (Close)", callback_data="close_ad")]
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

# 4. មុខងារស្វែងរករូបភាព (Google, Bing, Yandex, Baidu)
def get_search_markup(image_url):
    keyboard = [
        [InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={image_url}")],
        [InlineKeyboardButton("🔵 Bing Search", url=f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={image_url}")],
        [InlineKeyboardButton("🖼 Yandex Images", url=f"https://yandex.com/images/search?rpt=imageview&url={image_url}")],
        [InlineKeyboardButton("🇨🇳 Baidu Search", url=f"https://graph.baidu.com/details?is_not_show_man_search=1&image={image_url}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id) # ចុះឈ្មោះអ្នកប្រើពេលគេផ្ញើរូប
    status = await update.message.reply_text("🔎 កំពុងរៀបចំ Link ស្វែងរក...")
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_url = file.file_path
        await status.delete()
        await update.message.reply_text("✅ រួចរាល់! សូមជ្រើសរើស Browser៖", reply_markup=get_search_markup(image_url))
    except Exception as e:
        await status.edit_text(f"❌ កំហុស៖ {e}")

# 5. Handlers ផ្សេងៗ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id) # ចុះឈ្មោះអ្នកប្រើពេលគេចុច Start
    await update.message.reply_text("សួស្តី! សូមផ្ញើរូបភាពមក ដើម្បីស្វែងរកប្រភព។")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "close_ad":
        try:
            await query.message.delete()
            await query.answer("បិទរួចរាល់")
        except:
            await query.answer("មិនអាចលុបសារបានឡើយ")

# 6. ដំណើរការចម្បង
def main():
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN: return

    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # កំណត់ម៉ោងផ្សាយ Ads (៨ ព្រឹក និង ៨ យប់ ម៉ោងនៅកម្ពុជា)
    timezone = pytz.timezone("Asia/Phnom_Penh")
    app.job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=8, minute=0, tzinfo=timezone))
    app.job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=20, minute=0, tzinfo=timezone))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot is running with Image Search & 2x Daily Ads...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
