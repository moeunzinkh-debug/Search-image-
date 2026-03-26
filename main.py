import os
import logging
import threading
import datetime
import sqlite3
import pytz
import aiohttp
import base64
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

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

async def send_broadcast_ads(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    active_users = c.fetchall()
    conn.close()

    ad_text = "📢 *ការផ្សព្វផ្សាយពាណិជ្ជកម្មប្រចាំថ្ងៃ*\n\nសូមអរគុណដែលបានប្រើប្រាស់បូតរបស់យើង!"
    
    keyboard = [
        [InlineKeyboardButton("🔗 ចូលទៅកាន់ Channel", url="https://t.me/YourChannel")],
        [InlineKeyboardButton("❌ បិទ", callback_data="close_ad")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for user in active_users:
        try:
            await context.bot.send_message(chat_id=user[0], text=ad_text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            continue

# ✅ Upload ទៅ Imgur
async def upload_to_imgur(image_bytes):
    """Upload រូបភាពទៅ Imgur ហើយយក public URL"""
    client_id = os.environ.get("IMGUR_CLIENT_ID")
    if not client_id:
        raise Exception("IMGUR_CLIENT_ID not found")
    
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {client_id}"}
    
    async with aiohttp.ClientSession() as session:
        data = {"image": base64.b64encode(image_bytes).decode(), "type": "base64"}
        async with session.post(url, headers=headers, data=data) as resp:
            result = await resp.json()
            if result.get("success"):
                return result["data"]["link"]
            else:
                raise Exception(f"Imgur error: {result}")

# ✅ Upload ទៅ Catbox (ជម្រើសទី 2 - ងាយស្រួលជាង, មិនត្រូវការ API key)
async def upload_to_catbox(image_bytes):
    """Upload ទៅ catbox.moe (ឥតគិតថ្លៃ, មិនត្រូវការ account)"""
    url = "https://litterbox.catbox.moe/resources/internals/api.php"
    
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('reqtype', 'fileupload')
        data.add_field('time', '1h')  # 1 hour expiry (ឬ '24h', '72h')
        data.add_field('fileToUpload', image_bytes, filename='image.jpg', content_type='image/jpeg')
        
        async with session.post(url, data=data) as resp:
            if resp.status == 200:
                return await resp.text()  # Returns direct URL
            else:
                raise Exception(f"Catbox error: {resp.status}")

# ✅ បង្កើត search links (ប្រើ public URL សម្រាប់ Bing/Baidu)
def get_search_markup(public_url):
    keyboard = [
        [
            InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={public_url}"),
            InlineKeyboardButton("🔵 Bing Visual", url=f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={public_url}")
        ],
        [
            InlineKeyboardButton("🖼 Yandex", url=f"https://yandex.com/images/search?rpt=imageview&url={public_url}"),
            InlineKeyboardButton("🇨🇳 Baidu", url=f"https://graph.baidu.com/s?img={public_url}")  # ✅ ឥឡូវ Baidu ដំណើរការបាន!
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ✅ Handler ថ្មី - Upload មុនពេលផ្ញើ links
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)
    status = await update.message.reply_text("⏳ កំពុង upload រូបភាពទៅ server...")
    
    try:
        # 1. ទាញយករូបភាពពី Telegram
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_bytes = await file.download_as_bytearray()
        
        # 2. Upload ទៅ hosting ដើម្បីយក public URL
        # ជម្រើស A: Imgur (រហ័ស, តែត្រូវការ API key)
        # public_url = await upload_to_imgur(bytes(image_bytes))
        
        # ជម្រើស B: Catbox (ងាយស្រួល, មិនត្រូវការ API key) ✅ ណែនាំ
        public_url = await upload_to_catbox(bytes(image_bytes))
        
        # 3. ផ្ញើទៅ user
        await status.delete()
        await update.message.reply_text(
            f"✅ Upload រួចរាល់!\n\n"
            f"🔗 *Public URL:* `{public_url}`\n\n"
            f"ជ្រើសរើស Search Engine៖",
            reply_markup=get_search_markup(public_url),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        # Fallback: ប្រើតែ Google + Yandex ជាមួយ Telegram URL
        try:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            await status.delete()
            await update.message.reply_text(
                "⚠️ Upload មិនជោគជ័យ ប៉ុន្តែអាចប្រើ Google និង Yandex៖",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={file.file_path}"),
                        InlineKeyboardButton("🖼 Yandex", url=f"https://yandex.com/images/search?rpt=imageview&url={file.file_path}")
                    ]
                ])
            )
        except Exception as e2:
            await status.edit_text(f"❌ កំហុស៖ {str(e)[:200]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)
    await update.message.reply_text(
        "សួស្តី! ផ្ញើរូបភាពមក ខ្ញុំនឹង upload ហើយផ្ញើទៅ Search Engines (ឥឡូវ Baidu ក៏ដំណើរការបានដែរ!) 🚀"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "close_ad":
        try:
            await query.message.delete()
            await query.answer("បិទរួចរាល់")
        except:
            await query.answer("មិនអាចលុបបាន")

def main():
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN: 
        logger.error("No BOT_TOKEN!")
        return

    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    timezone = pytz.timezone("Asia/Phnom_Penh")
    app.job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=8, minute=0, tzinfo=timezone))
    app.job_queue.run_daily(send_broadcast_ads, time=datetime.time(hour=20, minute=0, tzinfo=timezone))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot running with Catbox upload (Baidu now works!)...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
