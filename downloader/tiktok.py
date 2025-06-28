import os
import re
import yt_dlp
from config import TEMP_DIR
from urllib.parse import urlparse

def clean_filename(filename: str) -> str:
    return re.sub(r'[^\w\-_]', '', filename)

def download_tiktok(url: str) -> str | None:
    try:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_DIR, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'max_filesize': 50 * 1024 * 1024,  # 50MB limit
            'timeout': 30
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
                
            filename = ydl.prepare_filename(info)
            safe_name = clean_filename(os.path.basename(filename))
            new_path = os.path.join(TEMP_DIR, f"tiktok_{safe_name}")
            os.rename(filename, new_path)
            
            return new_path
    except Exception as e:
        print(f"[TikTok Error] {e}")
        return None