import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN, TEMP_DIR
from handlers.main import start, handle_message
from healthcheck import app as health_app
import uvicorn
import threading

def ensure_temp_folder():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

def run_health_check():
    uvicorn.run(health_app, host="0.0.0.0", port=8000)

def main():
    ensure_temp_folder()
    
    # Запускаем health check в отдельном потоке
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()