import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPAM_TIME_WINDOW = int(os.getenv("SPAM_TIME_WINDOW", "10"))  # секунд
SPAM_MAX_REQUESTS = int(os.getenv("SPAM_MAX_REQUESTS", "3"))
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/video_downloads")

# Instagram credentials
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")