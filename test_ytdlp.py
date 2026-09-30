import yt_dlp
url = "https://www.instagram.com/p/DXCcXeuiGXj/?utm_source=ig_web_button_share_sheet"
ydl_opts = {'quiet': False, 'extract_flat': False}
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success:", info.get('id', 'NO ID'))
except Exception as e:
    print("ERROR:", e)
