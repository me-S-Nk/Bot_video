FROM python:3.11-slim-bullseye

WORKDIR /app

# Установка FFmpeg и очистка кэша
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем папку для временных файлов
RUN mkdir -p /tmp/video_downloads

CMD ["python", "bot.py"]