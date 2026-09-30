import asyncio
import os
import glob
import json
import time
import logging
import base64
import uuid
import subprocess
import shutil
import requests as http_requests
from urllib.parse import urlparse, urlunparse
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
import yt_dlp
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Токен не найден! Убедитесь, что в файле .env указан BOT_TOKEN.")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Путь к файлу с куки Instagram
INSTAGRAM_COOKIES = "instagram_cookies.txt"

# Если запускаем на сервере (Heroku/VPS) — восстанавливаем cookies из переменной окружения
_cookies_b64 = os.getenv("INSTAGRAM_COOKIES_B64")
if _cookies_b64:
    try:
        with open(INSTAGRAM_COOKIES, "wb") as _f:
            _f.write(base64.b64decode(_cookies_b64.strip()))
        logger.info(f"✅ {INSTAGRAM_COOKIES} успешно создан/обновлен из переменной INSTAGRAM_COOKIES_B64")
    except Exception as e:
        logger.error(f"❌ Ошибка при восстановлении кук: {e}")
else:
    logger.warning("⚠️ Переменная INSTAGRAM_COOKIES_B64 не найдена в окружении!")

# Увеличиваем таймаут для загрузки больших видео в Telegram (по умолчанию 60 сек)
session = AiohttpSession(timeout=600)
bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ────────────────────────────────────────
#  Языковые настройки и локализация
# ────────────────────────────────────────
USER_LANGUAGES_FILE = "user_languages.json"
user_languages = {}

def load_languages():
    global user_languages
    if os.path.exists(USER_LANGUAGES_FILE):
        try:
            with open(USER_LANGUAGES_FILE, "r", encoding="utf-8") as f:
                user_languages = json.load(f)
            logger.info("✅ Загружены языковые настройки пользователей.")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки языковых настроек: {e}")
            user_languages = {}

def save_languages():
    try:
        with open(USER_LANGUAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(user_languages, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения языковых настроек: {e}")

def get_lang(user_id):
    return user_languages.get(str(user_id), "ru")

# Загружаем языки при старте модуля
load_languages()

# ────────────────────────────────────────
#  Защита от спама и Кэширование
# ────────────────────────────────────────
COOLDOWN_SECONDS = 15
user_cooldowns = {}

CACHE_FILE = "download_cache.json"
download_cache = {}

def normalize_url(url: str) -> str:
    """Нормализует URL, удаляя query-параметры (трекеры) и приводя к единому виду."""
    try:
        parsed = urlparse(url.strip())
        clean_parsed = parsed._replace(query="", fragment="")
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        path = clean_parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]
            
        return f"{scheme}://{netloc}{path}"
    except Exception as e:
        logger.error(f"Ошибка при нормализации URL {url}: {e}")
        return url

def load_cache():
    global download_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                download_cache = json.load(f)
            logger.info(f"✅ Загружен кэш загрузок: {len(download_cache)} записей.")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки кэша: {e}")
            download_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(download_cache, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения кэша: {e}")

# Загружаем кэш при старте модуля
load_cache()

MESSAGES = {
    "ru": {
        "welcome": (
            "Привет! Я бот-помощник для загрузки контента \n\n"
            "• Кидай ссылку — я скачаю видео с <b>Instagram</b>, <b>Pinterest</b>, <b>TikTok</b> и <b>YouTube Shorts</b> \n\n"
            "• Работаю быстро, без воды и лишних кнопок 🚀"
        ),
        "invalid_link": "Пожалуйста, отправьте корректную ссылку на Instagram, TikTok, YouTube или Pinterest.",
        "yt_dev": "🛠 Данный метод скачивания (YouTube Shorts) всё ещё в разработке",
        "analyzing": "⏳ Анализирую ссылку...",
        "pinterest_downloading": "⏳ Скачиваю с Pinterest...",
        "pinterest_error": "❌ Не удалось скачать с Pinterest. Убедитесь, что пин публичный и ссылка корректная.",
        "tiktok_error": "❌ Ошибка при скачивании TikTok. Возможно, видео удалено или приватное.",
        "download_error": "❌ Ошибка при скачивании! Возможно, медиа удалено, аккаунт приватный, или платформа временно блокирует запросы.",
        "cookies_not_found": "❌ Этот пост содержит только фотографии, но файл `{cookies}` не найден. Пожалуйста, добавьте его в папку бота.",
        "gallery_downloading": "⏳ Скачиваю фото через gallery-dl...",
        "gallery_error": "❌ Не удалось скачать фото. Возможно, аккаунт приватный или cookies устарели (попробуйте обновить instagram_cookies.txt).",
        "processing": "⏳ Обработка ({current}/{total})...",
        "too_large": "❌ Не удалось обработать файлы. Возможно, все они слишком большие.",
        "sending": "⏳ Отправка ...",
        "select_lang": "Select language / Выберите язык / Dil seçin 👇",
        "spam_warning": "⚠️ Пожалуйста, подождите {seconds} сек. перед следующей загрузкой."
    },
    "en": {
        "welcome": (
            "Hello! I am a bot helper for downloading content \n\n"
            "• Send a link — I will download video from <b>Instagram</b>, <b>Pinterest</b>, <b>TikTok</b> and <b>YouTube Shorts</b> \n\n"
            "• I work fast, no water, no extra buttons 🚀"
        ),
        "invalid_link": "Please send a valid link to Instagram, TikTok, YouTube, or Pinterest.",
        "yt_dev": "🛠 This download method (YouTube Shorts) is still under development",
        "analyzing": "⏳ Analyzing link...",
        "pinterest_downloading": "⏳ Downloading from Pinterest...",
        "pinterest_error": "❌ Failed to download from Pinterest. Make sure the pin is public and the link is correct.",
        "tiktok_error": "❌ Error downloading TikTok. Maybe the video was deleted or is private.",
        "download_error": "❌ Download error! Maybe the media was deleted, the account is private, or the platform is temporarily blocking requests.",
        "cookies_not_found": "❌ This post contains only photos, but the file `{cookies}` was not found. Please add it to the bot folder.",
        "gallery_downloading": "⏳ Downloading photos...",
        "gallery_error": "❌ Failed to download photos. Maybe the account is private or cookies have expired (try updating instagram_cookies.txt).",
        "processing": "⏳ Processing ({current}/{total})...",
        "too_large": "❌ Failed to process files. Maybe they are all too large.",
        "sending": "⏳ Sending...",
        "select_lang": "Select language / Выберите язык / Dil seçin 👇",
        "spam_warning": "⚠️ Please wait {seconds} sec. before your next download."
    },
    "tr": {
        "welcome": (
            "Merhaba! İçerik indirmek için yardımcı bir botum \n\n"
            "• Link gönder — <b>Instagram</b>, <b>Pinterest</b>, <b>TikTok</b> ve <b>YouTube Shorts</b> platformlarından video indireyim \n\n"
            "• Hızlı çalışırım, gereksiz konuşmalar ve ekstra butonlar olmadan 🚀"
        ),
        "invalid_link": "Lütfen geçerli bir Instagram, TikTok, YouTube veya Pinterest linki gönderin.",
        "yt_dev": "🛠 Bu indirme yöntemi (YouTube Shorts) hala geliştirilme aşamasındadır",
        "analyzing": "⏳ Link analiz ediliyor...",
        "pinterest_downloading": "⏳ Pinterest'ten indiriliyor...",
        "pinterest_error": "❌ Pinterest'ten indirilemedi. Pin'in herkese açık olduğundan ve linkin doğru olduğundan emin olun.",
        "tiktok_error": "❌ TikTok indirilirken hata oluştu. Video silinmiş veya gizli olabilir.",
        "download_error": "❌ İndirme hatası! Belki medya silindi, hesap gizli veya platform geçici olarak istekleri engelliyor.",
        "cookies_not_found": "❌ Bu gönderi yalnızca fotoğraflar içeriyor, ancak `{cookies}` dosyası bulunamadı. Lütfen bot klasörüne ekleyin.",
        "gallery_downloading": "⏳ Fotoğraflar indiriliyor...",
        "gallery_error": "❌ Fotoğraflar indirilemedi. Belki hesap gizli veya çerezlerin süresi dolmuş (instagram_cookies.txt dosyasını güncellemeyi deneyin).",
        "processing": "⏳ İşleniyor ({current}/{total})...",
        "too_large": "❌ Dosyalar işlenemedi. Belki hepsi çok büyük.",
        "sending": "⏳ Gönderiliyor...",
        "select_lang": "Select language / Выберите язык / Dil seçin 👇",
        "spam_warning": "⚠️ Lütfen bir sonraki indirmeden önce {seconds} saniye bekleyin."
    }
}

def get_language_keyboard():
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"),
            types.InlineKeyboardButton(text="English 🇬🇧", callback_data="lang_en"),
            types.InlineKeyboardButton(text="Türkçe 🇹🇷", callback_data="lang_tr")
        ]
    ])
    return keyboard



# ────────────────────────────────────────
#  Загрузчик 0: Pinterest (gallery-dl → yt-dlp)
# ────────────────────────────────────────
def sync_download_pinterest(url):
    """
    Скачивает видео или фото из Pinterest.
    Попытка 1 — gallery-dl (нативная поддержка Pinterest pin/board).
    Попытка 2 — yt-dlp (встроенный Pinterest-экстрактор).
    Возвращает (list[filepath], caption).
    """
    import time

    out_dir = os.path.abspath("downloads")
    os.makedirs(out_dir, exist_ok=True)

    # ── Попытка 1: gallery-dl ──────────────────────────────────
    gallery_dl_path = shutil.which("gallery-dl")
    if not gallery_dl_path:
        if os.name == 'nt':
            gallery_dl_path = os.path.join(".venv", "Scripts", "gallery-dl")
        else:
            gallery_dl_path = os.path.join(".venv", "bin", "gallery-dl")
        if not os.path.exists(gallery_dl_path):
            gallery_dl_path = "gallery-dl"

    try:
        cmd = [
            gallery_dl_path,
            "--directory", out_dir,   # -D: точный путь без подкатегорий
            "--filename", "pinterest_{id}.{extension}",
            "--no-part",
            url,
        ]
        # Снимаем все файлы до
        before = set()
        for root, _, files in os.walk(out_dir):
            for f in files:
                before.add(os.path.join(root, f))

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        logger.info(f"gallery-dl pinterest rc={result.returncode} stdout={result.stdout[:300]}")

        # Собираем новые файлы (рекурсивный diff)
        after = set()
        for root, _, files in os.walk(out_dir):
            for f in files:
                after.add(os.path.join(root, f))
        new_files = list(after - before)

        # Запасной — файлы из stdout (gallery-dl печатает полные пути)
        if not new_files:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and os.path.isfile(line):
                    new_files.append(line)

        # Последний шанс — недавние файлы (30 сек)
        if not new_files:
            now = time.time()
            for root, _, files in os.walk(out_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if (now - os.path.getmtime(fpath)) < 30:
                        new_files.append(fpath)

        if new_files:
            logger.info(f"gallery-dl Pinterest: {len(new_files)} файл(ov) скачано")
            return sorted(new_files), ""

        raise Exception(f"gallery-dl не нашёл файлов. stderr: {result.stderr[:300]}")

    except Exception as e:
        logger.warning(f"Pinterest gallery-dl failed ({e}), trying yt-dlp...")

    # ── Попытка 2: yt-dlp ──────────────────────────────────
    try:
        ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'downloads/pinterest_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': ffmpeg_exe,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'X-Pinterest-PWS-Handler': 'www/[username].js',
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            caption = info.get('description') or info.get('title') or ""
            return [filepath], caption
    except Exception as e:
        logger.warning(f"Pinterest yt-dlp also failed ({e})")

    raise Exception(
        "Не удалось скачать пин. Убедитесь, что пин публичный "
        "и ссылка ведёт на конкретный пин (/pin/XXXXX/)."
    )


# ────────────────────────────────────────
#  Загрузчик 1: TikWM (Специально для TikTok)
# ────────────────────────────────────────
def sync_download_tiktok(url):
    """Скачивает видео или фото из TikTok через бесплатный API tikwm.com."""
    api_url = f"https://www.tikwm.com/api/?url={url}&hd=1"
    resp = http_requests.get(api_url, timeout=15)
    data = resp.json()
    
    if data.get("code") != 0:
        raise Exception(f"TikWM API error: {data.get('msg')}")
        
    video_data = data.get("data", {})
    caption = video_data.get("title", "")
    video_id = video_data.get("id", str(uuid.uuid4()))
    
    filepaths = []
    
    # Если это фото-карусель
    if "images" in video_data and video_data["images"]:
        for i, img_url in enumerate(video_data["images"]):
            img_resp = http_requests.get(img_url, timeout=15)
            filepath = f"downloads/tiktok_{video_id}_{i}.jpg"
            with open(filepath, "wb") as f:
                f.write(img_resp.content)
            filepaths.append(filepath)
    # Если это видео
    elif "play" in video_data:
        vid_url = video_data["play"]
        vid_resp = http_requests.get(vid_url, timeout=30)
        filepath = f"downloads/tiktok_{video_id}.mp4"
        with open(filepath, "wb") as f:
            f.write(vid_resp.content)
        filepaths.append(filepath)
    else:
        raise Exception("Не найдено ни видео, ни фото в ответе API TikTok")
        
    return filepaths, caption


# ────────────────────────────────────────
#  Загрузчик 2: yt-dlp (видео / Reels / YouTube)
# ────────────────────────────────────────
def sync_download_ytdlp(url):
    """Скачивает медиа через yt-dlp. Возвращает список путей."""
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/%(extractor)s_%(id)s.%(ext)s',
        'playlistend': 10,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_exe,
    }

    # Подключаем нужные куки в зависимости от платформы
    has_cookies = False
    if "instagram.com" in url and os.path.exists(INSTAGRAM_COOKIES):
        ydl_opts['cookiefile'] = INSTAGRAM_COOKIES
        logger.info(f"Использую файл кук для Instagram: {INSTAGRAM_COOKIES}")
        has_cookies = True
    elif ("youtube.com" in url or "youtu.be" in url) and os.path.exists("youtube_cookies.txt"):
        ydl_opts['cookiefile'] = "youtube_cookies.txt"
        logger.info("Использую файл кук для YouTube: youtube_cookies.txt")
        has_cookies = True
    elif ("youtube.com" in url or "youtu.be" in url):
        # Если кук нет, пытаемся обойти JS-проверку через мобильные клиенты
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['ios', 'android', 'web']}}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filepaths = []
            if '_type' in info_dict and info_dict['_type'] == 'playlist':
                for entry in (info_dict.get('entries') or []):
                    if entry:
                        filepaths.append(ydl.prepare_filename(entry))
            else:
                filepaths.append(ydl.prepare_filename(info_dict))
            caption = info_dict.get('description') or info_dict.get('title') or ""
            return filepaths, caption
    except Exception as e:
        # Если первая попытка была с куками и провалилась, пробуем без кук
        if has_cookies and ("youtube.com" in url or "youtu.be" in url):
            logger.warning(f"Ошибка при скачивании YouTube с куками: {e}. Пробую без кук с эмуляцией клиентов...")
            if 'cookiefile' in ydl_opts:
                del ydl_opts['cookiefile']
            ydl_opts['extractor_args'] = {'youtube': {'player_client': ['ios', 'android', 'web']}}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    filepaths = []
                    if '_type' in info_dict and info_dict['_type'] == 'playlist':
                        for entry in (info_dict.get('entries') or []):
                            if entry:
                                filepaths.append(ydl.prepare_filename(entry))
                    else:
                        filepaths.append(ydl.prepare_filename(info_dict))
                    caption = info_dict.get('description') or info_dict.get('title') or ""
                    return filepaths, caption
            except Exception as retry_err:
                logger.error(f"Повторная попытка скачивания без кук также провалилась: {retry_err}")
                raise
        else:
            raise


# ────────────────────────────────────────
#  Загрузчик 2: gallery-dl (фото / карусели Instagram)
# ────────────────────────────────────────
def sync_download_gallerydl(url):
    """
    Скачивает медиа через gallery-dl с cookies файлом.
    Возвращает список путей к скачанным файлам.
    """
    out_dir = os.path.abspath("downloads")
    cookie_path = os.path.abspath(INSTAGRAM_COOKIES)

    # Определяем путь к gallery-dl
    gallery_dl_path = shutil.which("gallery-dl")
    if not gallery_dl_path:
        if os.name == 'nt':
            gallery_dl_path = os.path.join(".venv", "Scripts", "gallery-dl")
        else:
            gallery_dl_path = os.path.join(".venv", "bin", "gallery-dl")
            if not os.path.exists(gallery_dl_path):
                gallery_dl_path = "gallery-dl"

    cmd = [
        gallery_dl_path,
        "--cookies", cookie_path,
        "--dest", out_dir,
        "--filename", "{extractor}_{id}_{num}.{extension}",
        url
    ]

    # Запускаем gallery-dl как подпроцесс
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info(f"gallery-dl stdout: {result.stdout}")
    if result.returncode != 0:
        logger.error(f"gallery-dl stderr: {result.stderr}")
        raise Exception(f"gallery-dl failed: {result.stderr}")

    # Собираем только недавно скачанные файлы
    downloaded = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and os.path.isfile(line):
            downloaded.append(line)

    # Запасной вариант: найти все файлы в downloads/ с недавней датой
    if not downloaded:
        import time
        now = time.time()
        for fname in os.listdir(out_dir):
            fpath = os.path.join(out_dir, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) < 60:
                downloaded.append(fpath)

    return sorted(downloaded)


# ────────────────────────────────────────
#  Перекодирование видео через FFmpeg
# ────────────────────────────────────────
async def reencode_video(filepath):
    """Перекодирует видео в H.264 для 100% совместимости с Telegram."""
    if not filepath or not os.path.exists(filepath):
        return filepath

    base = os.path.splitext(filepath)[0]
    ext = filepath.lower().rsplit('.', 1)[-1]
    safe_path = f"{base}_safe.mp4"
    
    # Сначала проверим, возможно видео уже в нужном формате (H.264 + MP4)
    if ext == 'mp4':
        try:
            ffprobe_exe = shutil.which("ffprobe") or "ffprobe"
            probe_cmd = f'{ffprobe_exe} -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "{filepath}"'
            proc = await asyncio.create_subprocess_shell(probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate()
            codec = stdout.decode().strip()
            if codec == 'h264':
                logger.info(f"Видео уже в формате H.264, пропускаю перекодирование: {filepath}")
                return filepath
        except Exception as e:
            logger.error(f"Ошибка ffprobe при проверке {filepath}: {e}")
    
    # Пытаемся перекодировать (ограничиваем ресурсы и фиксим размер для Telegram)
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    cmd = (
        f'{ffmpeg_exe} -y -i "{filepath}" '
        f'-c:v libx264 -preset fast -crf 32 -threads 2 '
        f'-vf "scale=\'min(iw,1280)\':trunc(ow/a/2)*2" '
        f'-pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 128k '
        f'-fs 45M "{safe_path}" -loglevel error'
    )
    
    logger.info(f"Начинаю перекодирование: {filepath}")
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if os.path.exists(safe_path) and os.path.getsize(safe_path) > 1000:
        logger.info(f"✅ Видео успешно перекодировано: {safe_path}")
        try:
            os.remove(filepath)
        except:
            pass
        return safe_path
    else:
        if stderr:
            logger.error(f"❌ Ошибка FFmpeg: {stderr.decode()}")
        logger.warning(f"⚠️ Перекодирование не удалось или файл пустой, использую оригинал: {filepath}")
        return filepath


async def get_video_dimensions(filepath: str):
    """Извлекает ширину и высоту видео с помощью ffprobe."""
    try:
        cmd = (
            f'ffprobe -v error -select_streams v:0 '
            f'-show_entries stream=width,height '
            f'-of csv=s=x:p=0 "{filepath}"'
        )
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if stdout:
            parts = stdout.decode().strip().split('x')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as e:
        logger.error(f"Не удалось получить размеры видео {filepath}: {e}")
    return None, None

# ────────────────────────────────────────
#  Сборка и отправка медиагруппы
# ────────────────────────────────────────
async def send_media(message: types.Message, msg: types.Message, filepaths: list, caption: str = ""):
    """
    Обрабатывает список файлов и отправляет их пользователю.
    Возвращает список кортежей (file_id, media_type) для кэширования.
    """
    lang = get_lang(message.from_user.id)
    if caption and len(caption) > 1024:
        caption = caption[:1021] + "..."
    ready_files = []

    for i, filepath in enumerate(filepaths):
        # Ищем фактический файл (yt-dlp мог изменить расширение)
        base = os.path.splitext(filepath)[0]
        candidates = glob.glob(f"{base}.*")
        actual = candidates[0] if candidates else (filepath if os.path.isfile(filepath) else None)
        if not actual:
            continue

        ext = actual.lower().rsplit('.', 1)[-1]

        # Перекодируем видео
        if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
            await msg.edit_text(MESSAGES[lang]["processing"].format(current=i + 1, total=len(filepaths)))
            actual = await reencode_video(actual)
            ext = 'mp4'

        # Проверка размера (лимит Telegram — 50 МБ)
        if os.path.getsize(actual) / (1024 * 1024) > 50:
            logger.warning(f"Пропускаю {actual} — слишком большой файл (>50 МБ)")
            os.remove(actual)
            continue

        ready_files.append((actual, ext))

    if not ready_files:
        await msg.edit_text(MESSAGES[lang]["too_large"])
        return []

    await msg.edit_text(MESSAGES[lang]["sending"])

    sent_media = []  # список (file_id, media_type) для кэша

    try:
        if len(ready_files) == 1:
            path, ext = ready_files[0]
            fobj = FSInputFile(path)
            if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
                w, h = await get_video_dimensions(path)
                kwargs = {'supports_streaming': True}
                if w and h:
                    kwargs['width'] = w
                    kwargs['height'] = h
                sent = await bot.send_video(message.chat.id, fobj, caption=caption, **kwargs)
                if sent and sent.video:
                    sent_media.append({'file_id': sent.video.file_id, 'type': 'video'})
            elif ext in ('jpg', 'jpeg', 'png', 'webp'):
                sent = await bot.send_photo(message.chat.id, fobj, caption=caption)
                if sent and sent.photo:
                    sent_media.append({'file_id': sent.photo[-1].file_id, 'type': 'photo'})
            else:
                sent = await bot.send_document(message.chat.id, fobj, caption=caption)
                if sent and sent.document:
                    sent_media.append({'file_id': sent.document.file_id, 'type': 'document'})
        else:
            # Telegram принимает до 10 элементов в группе
            for chunk_idx, chunk in enumerate([ready_files[i:i+10] for i in range(0, len(ready_files), 10)]):
                builder = MediaGroupBuilder()
                for i, (path, ext) in enumerate(chunk):
                    # Добавляем описание только к первому элементу первой группы
                    cap = caption if chunk_idx == 0 and i == 0 else None
                    if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
                        w, h = await get_video_dimensions(path)
                        kwargs = {'type': 'video', 'media': FSInputFile(path), 'supports_streaming': True}
                        if w and h:
                            kwargs['width'] = w
                            kwargs['height'] = h
                        if cap:
                            kwargs['caption'] = cap
                        builder.add(**kwargs)
                    else:
                        builder.add(type='photo', media=FSInputFile(path), caption=cap)
                sent_msgs = await message.answer_media_group(builder.build())
                # Извлекаем file_id из каждого отправленного сообщения
                for sm in (sent_msgs or []):
                    if sm.video:
                        sent_media.append({'file_id': sm.video.file_id, 'type': 'video'})
                    elif sm.photo:
                        sent_media.append({'file_id': sm.photo[-1].file_id, 'type': 'photo'})
                    elif sm.document:
                        sent_media.append({'file_id': sm.document.file_id, 'type': 'document'})

        await msg.delete()
    finally:
        for path, _ in ready_files:
            if os.path.exists(path):
                os.remove(path)

    return sent_media


# ────────────────────────────────────────
#  Обработчики команд
# ────────────────────────────────────────
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    keyboard = get_language_keyboard()
    await message.answer(MESSAGES["ru"]["select_lang"], reply_markup=keyboard)

@dp.message(Command("help"))
async def send_help(message: types.Message):
    lang = get_lang(message.from_user.id)
    await message.answer(MESSAGES[lang]["welcome"])

@dp.callback_query(F.data.startswith("lang_"))
async def select_language_callback(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]  # "ru", "en", "tr"
    user_id = str(callback.from_user.id)
    
    # Сохраняем язык пользователя
    user_languages[user_id] = lang_code
    save_languages()
    
    # Отвечаем на callback
    await callback.answer()
    
    # Удаляем сообщение с выбором языка и шлем приветствие
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    welcome_text = MESSAGES[lang_code]["welcome"]
    await callback.message.answer(welcome_text)

@dp.message(F.text)
async def handle_message(message: types.Message):
    url = message.text.strip()
    lang = get_lang(message.from_user.id)
    user_id = str(message.from_user.id)

    allowed_domains = ["instagram.com", "tiktok.com", "youtube.com", "youtu.be", "pinterest.com", "pinterest.ru", "pin.it"]
    if not any(domain in url for domain in allowed_domains):
        await message.answer(MESSAGES[lang]["invalid_link"])
        return

    # ── Защита от спама (cooldown) ───────────────────────────────────
    now = time.time()
    last_time = user_cooldowns.get(user_id, 0)
    remaining = COOLDOWN_SECONDS - (now - last_time)
    if remaining > 0:
        await message.answer(
            MESSAGES[lang]["spam_warning"].format(seconds=int(remaining) + 1)
        )
        return

    # ── Проверка кэша ────────────────────────────────────────────────
    norm_url = normalize_url(url)
    cached = download_cache.get(norm_url)
    if cached:
        logger.info(f"Cache hit for {norm_url}")
        try:
            for item in cached["media"]:
                fid = item["file_id"]
                mtype = item["type"]
                if mtype == "video":
                    await bot.send_video(message.chat.id, fid, caption=cached.get("caption", ""))
                elif mtype == "photo":
                    await bot.send_photo(message.chat.id, fid, caption=cached.get("caption", ""))
                else:
                    await bot.send_document(message.chat.id, fid, caption=cached.get("caption", ""))
            user_cooldowns[user_id] = time.time()
            return
        except Exception as e:
            logger.warning(f"Cache replay failed for {norm_url}: {e}. Falling back to fresh download.")
            del download_cache[norm_url]
            save_cache()

    msg = await message.answer(MESSAGES[lang]["analyzing"])

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # ── Pinterest ────────────────────────────────────────────────────
    if any(d in url for d in ("pinterest.com", "pinterest.ru", "pin.it")):
        try:
            await msg.edit_text(MESSAGES[lang]["pinterest_downloading"])
            filepaths, caption = await asyncio.to_thread(sync_download_pinterest, url)
            sent = await send_media(message, msg, filepaths, caption)
            if sent:
                user_cooldowns[user_id] = time.time()
                download_cache[norm_url] = {"media": sent, "caption": caption[:1024] if caption else ""}
                save_cache()
            return
        except Exception as e:
            logger.error(f"Pinterest download error for {url}: {e}")
            await msg.edit_text(MESSAGES[lang]["pinterest_error"])
            return

    # ── TikTok ──────────────────────────────────────────────────────
    if "tiktok.com" in url:
        try:
            filepaths, caption = await asyncio.to_thread(sync_download_tiktok, url)
            sent = await send_media(message, msg, filepaths, caption)
            if sent:
                user_cooldowns[user_id] = time.time()
                download_cache[norm_url] = {"media": sent, "caption": caption[:1024] if caption else ""}
                save_cache()
            return
        except Exception as e:
            logger.error(f"TikTok download error for {url}: {e}")
            await msg.edit_text(MESSAGES[lang]["tiktok_error"])
            return

    # ── Попытка 1: yt-dlp (работает для видео, Reels, YouTube) ──
    try:
        filepaths, caption = await asyncio.to_thread(sync_download_ytdlp, url)
        sent = await send_media(message, msg, filepaths, caption)
        if sent:
            user_cooldowns[user_id] = time.time()
            download_cache[norm_url] = {"media": sent, "caption": caption[:1024] if caption else ""}
            save_cache()
        return
    except Exception as e:
        error_str = str(e)
        is_photo_only = "There is no video in this post" in error_str or "No video formats found" in error_str
        if not is_photo_only:
            # Реальная ошибка — не пытаемся делать запасной вариант
            logger.error(f"yt-dlp error for {url}: {e}")
            await msg.edit_text(MESSAGES[lang]["download_error"])
            return
        logger.info(f"yt-dlp: пост без видео — переключаюсь на gallery-dl для {url}")

    # ── Попытка 2: gallery-dl + cookies (для фото-постов Instagram) ──
    if not os.path.exists(INSTAGRAM_COOKIES):
        await msg.edit_text(MESSAGES[lang]["cookies_not_found"].format(cookies=INSTAGRAM_COOKIES))
        return

    try:
        await msg.edit_text(MESSAGES[lang]["gallery_downloading"])
        filepaths = await asyncio.to_thread(sync_download_gallerydl, url)
        if not filepaths:
            raise Exception("gallery-dl не нашел ни одного файла")
            
        # Пытаемся быстро получить описание через yt-dlp
        caption = ""
        try:
            ydl_opts = {'quiet': True, 'cookiefile': INSTAGRAM_COOKIES} if os.path.exists(INSTAGRAM_COOKIES) else {'quiet': True}
            def fetch_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            info = await asyncio.to_thread(fetch_info)
            if info:
                caption = info.get('description') or info.get('title') or ""
        except:
            pass
            
        sent = await send_media(message, msg, filepaths, caption)
        if sent:
            user_cooldowns[user_id] = time.time()
            download_cache[norm_url] = {"media": sent, "caption": caption[:1024] if caption else ""}
            save_cache()
    except Exception as e:
        logger.error(f"gallery-dl error for {url}: {e}")
        await msg.edit_text(MESSAGES[lang]["gallery_error"])


# ────────────────────────────────────────
#  Запуск
# ────────────────────────────────────────
async def main():
    logger.info("Бот запущен (yt-dlp + gallery-dl)!")
    
    # Проверка FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        logger.info(f"✅ FFmpeg найден: {ffmpeg_path}")
        # Проверим версию
        proc = await asyncio.create_subprocess_shell("ffmpeg -version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        logger.info(f"Версия FFmpeg: {stdout.decode().splitlines()[0] if stdout else 'неизвестно'}")
    else:
        logger.error("❌ FFmpeg НЕ НАЙДЕН в системе! Перекодирование работать не будет.")

    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен.")
