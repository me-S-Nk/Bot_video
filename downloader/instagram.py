import os
import yt_dlp
from config import TEMP_DIR, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

def download_instagram(url: str) -> str | None:
    try:
        ydl_opts = {
            'outtmpl': os.path.join(TEMP_DIR, 'insta_%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'max_filesize': 100 * 1024 * 1024,  # 100MB limit
            'extractor_args': {
                'instagram': {
                    'requested_quality': 'hd'
                }
            }
        }

        # Если есть логин/пароль - используем их
        if INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD:
            ydl_opts.update({
                'username': INSTAGRAM_USERNAME,
                'password': INSTAGRAM_PASSWORD,
                'cookiefile': 'cookies.txt'
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
                
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as e:
        if "login" in str(e).lower():
            return None  # Пропускаем приватный контент
        print(f"[Instagram DownloadError] {e}")
        return None
    except Exception as e:
        print(f"[Instagram Error] {e}")
        return None