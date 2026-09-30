import urllib.request
import zipfile
import os
import ssl

# Игнорируем ошибки SSL если они будут
ssl._create_default_https_context = ssl._create_unverified_context

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"

print(f"Скачиваю FFmpeg из {url}...")
urllib.request.urlretrieve(url, zip_path)
print("Распаковка...")

with zipfile.ZipFile(zip_path, 'r') as z:
    for file in z.namelist():
        if file.endswith('ffmpeg.exe') or file.endswith('ffprobe.exe'):
            filename = os.path.basename(file)
            print(f"Извлекаю {filename}...")
            with open(filename, 'wb') as f:
                f.write(z.read(file))

os.remove(zip_path)
print("Готово! FFmpeg установлен в папку проекта.")
