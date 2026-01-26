import os
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. ការកំណត់ Logging និង Flask
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Image Search Bot is Active!", 200

def run_flask():
    server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

TOKEN = os.environ.get("BOT_TOKEN")

# 2. មុខងារបង្កើត Buttons សម្រាប់ស្វែងរក
def get_search_buttons(image_url):
    # បង្កើត Links សម្រាប់ស្វែងរក
    google_url = f"https://lens.google.com/uploadbyurl?url={image_url}"
    yandex_url = f"https://yandex.com/images/search?rpt=imageview&url={image_url}"
    baidu_url = f"https://graph.baidu.com/details?is_not_show_man_search=1&image={image_url}"
    bing_url = f"https://www.bing.com/images/searchbyimage?cbir=sbi&imgurl={image_url}"

    # បង្កើតប៊ូតុងចុច (Inline Buttons)
    keyboard = [
        [InlineKeyboardButton("🔍 Google Lens", url=google_url)],
        [InlineKeyboardButton("🖼 Yandex Images", url=yandex_url)],
        [InlineKeyboardButton("🇨🇳 Baidu Search", url=baidu_url)],
        [InlineKeyboardButton("🔎 Bing Visual", url=bing_url)]
    ]
    return InlineKeyboardMarkup(keyboard)

# 3. Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("សួស្តី! សូមផ្ញើរូបភាពមក ដើម្បីស្វែងរកប្រភពលើ Google, Yandex, Baidu និង Bing។")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("កំពុងរៀបចំលទ្ធផល... ⏳")
    
    try:
        # ទាញយក Link រូបភាពពី Telegram (Link នេះរស់បាន 1 ម៉ោង)
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path

        reply_markup = get_search_buttons(image_url)
        
        await status_msg.delete() # លុបសារ "កំពុងរៀបចំ" ចេញ
        await update.message.reply_text(
            "✅ ស្វែងរករួចរាល់! សូមជ្រើសរើស Browser ខាងក្រោម៖",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ មានបញ្ហាបច្ចេកទេស។ សូមព្យាយាមផ្ញើរូបភាពម្តងទៀត។")

# 4. ដំណើរការចម្បង
def main():
    if not TOKEN:
        logger.error("សូមដាក់ BOT_TOKEN ក្នុង Environment Variables!")
        return
        
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    logger.info("Image Search Bot with Baidu started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
