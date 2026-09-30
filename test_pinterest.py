"""
Тест скачивания с Pinterest.
Использование:
    python test_pinterest.py https://www.pinterest.com/pin/XXXXXXXXXX/
"""
import sys
import os
import shutil
import yt_dlp
import requests

os.makedirs("downloads", exist_ok=True)

TEST_URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.pinterest.com/pin/1015703408904946795/"

print(f"Тестируем URL: {TEST_URL}\n")

# ── Метод 1: yt-dlp ──────────────────────────────────────────────
print("=== Метод 1: yt-dlp ===")
try:
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads/pinterest_%(id)s.%(ext)s',
        'quiet': False,
        'no_warnings': False,
        'ffmpeg_location': ffmpeg_exe,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(TEST_URL, download=True)
        filepath = ydl.prepare_filename(info)
        print(f"\n✅ Скачано: {filepath}")
        print(f"   Заголовок: {info.get('title', '')}")
        print(f"   Размер:    {os.path.getsize(filepath) / 1024:.1f} КБ")
    sys.exit(0)
except Exception as e:
    print(f"❌ yt-dlp не сработал: {e}")

# ── Метод 2: Pinterest JSON API ───────────────────────────────────
print("\n=== Метод 2: Pinterest JSON API (fallback) ===")
import re
pin_id_match = re.search(r'/pin/([0-9]+)', TEST_URL)
if not pin_id_match:
    print("❌ Не удалось извлечь ID пина из URL")
    sys.exit(1)

pin_id = pin_id_match.group(1)
print(f"Pin ID: {pin_id}")

api_url = (
    f"https://www.pinterest.com/resource/PinResource/get/"
    f"?data=%7B%22options%22%3A%7B%22id%22%3A%22{pin_id}%22%2C%22field_set_key%22%3A%22detailed%22%7D%7D"
)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "X-APP-VERSION": "3a1de9f",
    "X-Pinterest-AppState": "active",
    "Accept": "application/json, text/javascript, */*, q=0.01",
    "Referer": TEST_URL,
}

resp = requests.get(api_url, headers=headers, timeout=15)
print(f"HTTP статус: {resp.status_code}")

data = resp.json()
pin_data = data.get("resource_response", {}).get("data", {})
print(f"Заголовок пина: {pin_data.get('title') or pin_data.get('description') or '(нет)'}")

videos = pin_data.get("videos") or {}
video_list = videos.get("video_list") or {}
images = pin_data.get("images") or {}

if video_list:
    print(f"✅ Найдено {len(video_list)} вариантов видео:")
    for k, v in video_list.items():
        print(f"   {k}: {v.get('width')}x{v.get('height')} — {v.get('url', '')[:80]}...")
elif images:
    print(f"✅ Найдено {len(images)} вариантов фото:")
    for k, v in images.items():
        print(f"   {k}: {v.get('width')}x{v.get('height')} — {v.get('url', '')[:80]}...")
else:
    print("❌ Ни видео, ни фото не найдено в ответе API")
    print("Ключи data:", list(pin_data.keys()))
