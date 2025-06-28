import os
import re
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from downloader.tiktok import download_tiktok
from downloader.instagram import download_instagram
from utils.spam_protection import is_spam

LINK_PATTERNS = {
    "tiktok": r"(https?://)?(www\.)?(tiktok\.com|tiktok\.app\.link|vm\.tiktok\.com)",
    "instagram": r"(https?://)?(www\.)?instagram\.com/(reel|p)/"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Отправь ссылку из TikTok или Instagram.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if is_spam(user_id):
        await update.message.reply_text("🚫 Подожди немного перед следующей ссылкой.")
        return

    # Определяем тип ссылки с помощью регулярных выражений
    video_type = None
    for platform, pattern in LINK_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            video_type = platform
            break

    if not video_type:
        await update.message.reply_text("❗ Отправь корректную ссылку из TikTok или Instagram.")
        return

    try:
        await update.message.reply_text(f"⏳ Скачиваю видео с {video_type.capitalize()}...")
        
        # Запускаем загрузку с таймаутом
        download_func = download_tiktok if video_type == "tiktok" else download_instagram
        file_path = await asyncio.wait_for(
            asyncio.to_thread(download_func, text),
            timeout=180  # 3 минуты на загрузку
        )

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "rb") as video:
                    await update.message.reply_video(
                        video=video,
                        supports_streaming=True,
                        read_timeout=60,
                        write_timeout=60
                    )
            except Exception as e:
                print(f"[Send Error] {e}")
                await update.message.reply_text("⚠️ Ошибка при отправке видео.")
            finally:
                os.remove(file_path)
        else:
            await update.message.reply_text("❌ Не удалось скачать видео. Проверь ссылку.")
            
    except asyncio.TimeoutError:
        await update.message.reply_text("⌛ Время загрузки истекло. Попробуй позже.")
    except Exception as e:
        print(f"[General Error] {e}")
        await update.message.reply_text("🚧 Произошла ошибка. Попробуй другую ссылку.")