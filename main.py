import os
import logging
import threading
import datetime
import pytz  # សម្រាប់កំណត់ម៉ោងនៅកម្ពុជា
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Logging & Flask Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__)
@server.route('/')
def health(): return "Bot is Active!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("BOT_TOKEN")
MY_USER_ID = os.environ.get("MY_USER_ID") # ប្រាកដថាបានដាក់ ID ក្នុង Render

# 2. មុខងារផ្ញើសាររំលឹក (១ ថ្ងៃម្តង)
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    if MY_USER_ID:
        try:
            await context.bot.send_message(
                chat_id=MY_USER_ID,
                text="☀️ *សួស្តី! រំលឹកប្រចាំថ្ងៃ:* បូតរបស់អ្នកកំពុងដំណើរការយ៉ាងរលូន។",
                parse_mode="Markdown"
            )
            logger.info("Daily reminder sent.")
        except Exception as e:
            logger.error(f"Reminder error: {e}")

# 3. មុខងារស្វែងរករូបភាព
def get_search_markup(image_url):
    keyboard = [
        [InlineKeyboardButton("🔍 Google Lens", url=f"https://lens.google.com/uploadbyurl?url={image_url}")],
        [InlineKeyboardButton("🖼 Yandex Images", url=f"https://yandex.com/images/search?rpt=imageview&url={image_url}")],
        [InlineKeyboardButton("🇨🇳 Baidu Search", url=f"https://graph.baidu.com/details?is_not_show_man_search=1&image={image_url}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("🔎 កំពុងរៀបចំ Link...")
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_url = file.file_path
        await status.delete()
        await update.message.reply_text("✅ រួចរាល់! សូមជ្រើសរើស Browser៖", reply_markup=get_search_markup(image_url))
    except Exception as e:
        await status.edit_text(f"❌ កំហុស៖ {e}")

# 4. ដំណើរការចម្បង
def main():
    if not TOKEN:
        logger.error("សូមដាក់ BOT_TOKEN!")
        return
        
    threading.Thread(target=run_flask, daemon=True).start()
    
    # បង្កើត Application
    app = Application.builder().token(TOKEN).build()
    
    # --- កំណត់ម៉ោងផ្ញើសាររំលឹក ---
    # កំណត់ឱ្យផ្ញើរាល់ថ្ងៃ ម៉ោង ៨:០០ ព្រឹក (ម៉ោងនៅកម្ពុជា)
    timezone = pytz.timezone("Asia/Phnom_Penh")
    job_queue = app.job_queue
    job_queue.run_daily(
        send_daily_reminder, 
        time=datetime.time(hour=8, minute=0, second=0, tzinfo=timezone)
    )
    
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("សូមផ្ញើរូបភាពមក!")))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("Bot started with Daily Reminder (8:00 AM)...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
