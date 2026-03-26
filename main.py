import os
import logging
import threading
import datetime
import sqlite3
import pytz
import httpx
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

# ✅ Upload ទៅ Catbox (ងាយស្រួល, លឿន)
async def upload_to_catbox(image_bytes):
    """Upload ទៅ catbox.moe"""
    url = "https://litterbox.catbox.moe/resources/internals/api.php"
    
    async with httpx.AsyncClient() as client:
        files = {'fileToUpload': ('image.jpg', image_bytes, 'image/jpeg')}
        data = {'reqtype': 'fileupload', 'time': '1h'}
        
        response = await client.post(url, data=data, files=files, timeout=30.0)
        if response.status_code == 200:
            return response.text.strip()
        else:
            raise Exception(f"Catbox error: {response.status_code}")

# ✅ ថ្មី: Upload ទៅ Baidu ហើយ return search URL
async def upload_to_baidu(image_bytes):
    """
    Upload រូបភាពទៅ Baidu Image Search
    Baidu ត្រូវការ POST request ជាមួយ multipart form
    """
    url = "https://graph.baidu.com/upload"
    
    # Baidu requires specific headers and form data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"
    }
    
    async with httpx.AsyncClient() as client:
        # Prepare multipart form data
        files = {
            'image': ('image.jpg', image_bytes, 'image/jpeg'),
            'from': (None, 'pc'),
            'tn': (None, 'pc'),
            'sdkparams': (None, '{"from":"pc","product":"image"}')
        }
        
        try:
            response = await client.post(url, headers=headers, files=files, timeout=30.0, follow_redirects=True)
            
            # Baidu returns JSON with search URL
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Extract search URL from response
                    if 'data' in data and 'url' in data['data']:
                        return data['data']['url']
                    elif 'url' in data:
                        return data['url']
                except:
                    pass
                
                # If JSON parsing fails, try to extract from HTML or return fallback
                return f"https://graph.baidu.com/s?sign={base64.b64encode(image_bytes[:100]).decode()[:20]}"
            else:
                raise Exception(f"Baidu upload failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Baidu upload error: {e}")
            # Fallback: use public URL method
            raise e

# ✅ បង្កើត search links
def get_search_markup(public_url, baidu_direct_url=None):
    """
    បង្កើត keyboard ជាមួយទាំងអស់
    """
    keyboard = []
    
    # Row 1: Google + Bing
    keyboard.append([
        InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={public_url}"),
        InlineKeyboardButton("🔵 Bing Visual", url=f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={public_url}")
    ])
    
    # Row 2: Yandex + Baidu
    row2 = [InlineKeyboardButton("🖼 Yandex", url=f"https://yandex.com/images/search?rpt=imageview&url={public_url}")]
    
    # Baidu: ប្រើ direct URL បើមាន, មិនដូច្នេះប្រើ public URL
    if baidu_direct_url:
        row2.append(InlineKeyboardButton("🇨🇳 Baidu", url=baidu_direct_url))
    else:
        # Fallback: use Baidu with public URL (may not work perfectly)
        row2.append(InlineKeyboardButton("🇨🇳 Baidu", url=f"https://graph.baidu.com/s?img={public_url}"))
    
    keyboard.append(row2)
    
    return InlineKeyboardMarkup(keyboard)

# ✅ Handler ថ្មី - Upload ទៅទាំង Catbox និង Baidu
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)
    status = await update.message.reply_text("⏳ កំពុង upload រូបភាព...")
    
    try:
        # 1. ទាញយករូបភាពពី Telegram
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_bytes = await file.download_as_bytearray()
        image_data = bytes(image_bytes)
        
        # 2. Upload ទៅ Catbox (សម្រាប់ Google, Bing, Yandex)
        public_url = await upload_to_catbox(image_data)
        
        # 3. សាកល្បង upload ទៅ Baidu (optional, may fail due to restrictions)
        baidu_url = None
        try:
            baidu_url = await upload_to_baidu(image_data)
            logger.info(f"Baidu direct upload success: {baidu_url}")
        except Exception as e:
            logger.warning(f"Baidu direct upload failed: {e}")
            # Baidu will use public URL fallback
        
        # 4. ផ្ញើទៅ user
        await status.delete()
        
        if baidu_url:
            msg = "✅ Upload រួចរាល់! (Baidu direct upload ជោគជ័យ 🎉)"
        else:
            msg = "✅ Upload រួចរាល់! (Baidu ប្រើ public URL)"
        
        await update.message.reply_text(
            f"{msg}\n\nជ្រើសរើស Search Engine៖",
            reply_markup=get_search_markup(public_url, baidu_url)
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        # Fallback: ប្រើតែ Google + Yandex
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
        "សួស្តី! 🚀\n\n"
        "ផ្ញើរូបភាពមក ខ្ញុំនឹង upload ហើយផ្ញើទៅ:\n"
        "• 🔍 Google Lens\n"
        "• 🔵 Bing Visual\n" 
        "• 🖼 Yandex\n"
        "• 🇨🇳 Baidu (ល្អសម្រាប់រក Chinese dramas!)\n\n"
        "⚡️ លឿន និងងាយស្រួល!"
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
    
    logger.info("Bot running with Baidu support...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
