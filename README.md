<div align="center">

# 🤖 Telegram Media Downloader Bot

### Fast & Reliable Media Downloader for Telegram

A multilingual Telegram bot for downloading media from **Instagram, TikTok, Pinterest and YouTube** directly into Telegram.

The bot automatically detects the source platform, selects the appropriate download engine, processes the media when necessary, and sends the resulting photos or videos directly to the user.

<br>

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=for-the-badge\&logo=telegram\&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Media%20Processing-007808?style=for-the-badge\&logo=ffmpeg\&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Downloader-red?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge\&logo=docker\&logoColor=white)

</div>

---

## 📖 Overview

This project is a production-oriented Telegram bot designed to simplify media downloading from popular social platforms.

The user only needs to **send a supported URL**. The bot analyzes the link, selects the appropriate downloader, retrieves the media, processes it for Telegram compatibility, and sends it back automatically.

The project also includes:

* 🌍 Multilingual interface
* ⚡ Download caching
* 🛡️ Anti-spam protection
* 🎞️ Automatic video transcoding
* 🖼️ Photo and carousel support
* 📦 Multiple download engines
* 🔐 Environment-based configuration
* 📝 Structured logging

---

## ✨ Features

### 📥 Multi-platform Downloads

The bot supports media downloads from:

| Platform          | Support                                                 |
| ----------------- | ------------------------------------------------------- |
| 📸 Instagram      | Videos, Reels & photo posts                             |
| 🎵 TikTok         | Videos & photo carousels                                |
| 📌 Pinterest      | Photos & videos                                         |
| ▶️ YouTube        | Media through `yt-dlp`                                  |
| 📱 YouTube Shorts | Supported through the YouTube downloader when available |

---

### 🌍 Multilingual Interface

Users can choose between three languages:

* 🇷🇺 Russian
* 🇬🇧 English
* 🇹🇷 Turkish

The selected language is saved for each Telegram user and automatically restored on future interactions.

---

### ⚡ Smart Download Routing

The bot does not use a single downloader for every platform.

Instead, it automatically selects the appropriate method:

```text
Incoming URL
     │
     ▼
Platform Detection
     │
     ├── Pinterest ──► gallery-dl
     │                    │
     │                    └──► yt-dlp fallback
     │
     ├── TikTok ─────► TikWM API
     │
     └── Instagram /
         YouTube ───► yt-dlp
                          │
                          └──► gallery-dl fallback
                               for Instagram photos
```

This architecture allows different platforms to use specialized download methods.

---

## 🖼️ Media Processing

Downloaded media is prepared before being sent to Telegram.

### Video Processing

The bot uses **FFmpeg** to ensure video compatibility.

It can:

* Detect the existing video codec
* Skip unnecessary transcoding when the video is already H.264
* Convert
