import os
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. កំណត់ Logging & Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    # Render ប្រើ Port 10000 ជាលំនាំដើម
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("BOT_TOKEN")
MY_USER_ID = os.environ.get("MY_USER_ID")

# 2. មុខងារផ្ញើសារដាស់រាល់ ១០ នាទី (៦០០ វិនាទី)
async def keep_alive(app: Application):
    while True:
        try:
            if MY_USER_ID:
                await app.bot.send_message(
                    chat_id=MY_USER_ID, 
                    text="⏳ *Keep-alive:* ១០ នាទីបានកន្លងផុតទៅ បូតនៅតែដំណើរការ។", 
                    parse_mode="Markdown",
                    disable_notification=True
                )
            logger.info("Sent keep-alive ping (10 min).")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
        
        # ប្តូរមក ៦០០ វិនាទី = ១០ នាទី
        await asyncio.sleep(600) 

# 3. មុខងារស្វែងរករូបភាព (Google, Yandex, Baidu)
def get_search_markup(image_url):
    keyboard = [
        [InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={image_url}")],
        [InlineKeyboardButton("🖼 Yandex Images", url=f"https://yandex.com/images/search?rpt=imageview&url={image_url}")],
        [InlineKeyboardButton("🇨🇳 Baidu Search", url=f"https://graph.baidu.com/details?is_not_show_man_search=1&image={image_url}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("🔎 កំពុងរៀបចំ Link ស្វែងរក...")
    try:
        # ទាញយក Link រូបភាព
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_url = file.file_path
        
        reply_markup = get_search_markup(image_url)
        await status.delete()
        await update.message.reply_text("✅ រួចរាល់! សូមជ្រើសរើស Browser៖", reply_markup=reply_markup)
    except Exception as e:
        await status.edit_text(f"❌ កំហុស៖ {e}")

# 4. ដំណើរការចម្បង
def main():
    if not TOKEN:
        logger.error("សូមដាក់ BOT_TOKEN ក្នុង Environment Variables!")
        return
        
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # ចាប់ផ្តើម Task ដាស់បូត
    asyncio.get_event_loop().create_task(keep_alive(app))
    
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("សូមផ្ញើរូបភាពមក ដើម្បីស្វែងរក!")))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("Bot started on Render (10 min interval)...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
