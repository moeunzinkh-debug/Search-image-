import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Setup Logging & Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Render is keeping me alive!", 200

def run_flask():
    # Render ជាទូទៅប្រើ Port 10000
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("BOT_TOKEN")
MY_USER_ID = os.environ.get("MY_USER_ID")

# 2. Wakeup Task (ដាស់រាល់ ៥ នាទី ដើម្បីការពារ Render Sleep)
async def keep_alive(app: Application):
    while True:
        try:
            if MY_USER_ID:
                await app.bot.send_message(chat_id=MY_USER_ID, text="💤 Render Keep-alive", disable_notification=True)
            logger.info("Keep-alive ping sent.")
        except: pass
        await asyncio.sleep(300) 

# 3. Image Search Logic
def get_buttons(img_url):
    keyboard = [
        [InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={img_url}")],
        [InlineKeyboardButton("🖼 Yandex Images", url=f"https://yandex.com/images/search?rpt=imageview&url={img_url}")],
        [InlineKeyboardButton("🇨🇳 Baidu Search", url=f"https://graph.baidu.com/details?is_not_show_man_search=1&image={img_url}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_photo(u, c):
    msg = await u.message.reply_text("🔎 កំពុងស្វែងរក...")
    try:
        file = await c.bot.get_file(u.message.photo[-1].file_id)
        markup = get_buttons(file.file_path)
        await msg.delete()
        await u.message.reply_text("✅ ជ្រើសរើសប្រភពស្វែងរក៖", reply_markup=markup)
    except: await msg.edit_text("❌ Error!")

# 4. Main
def main():
    if not TOKEN: return
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    asyncio.get_event_loop().create_task(keep_alive(app))
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("ផ្ញើរូបមក!")))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
