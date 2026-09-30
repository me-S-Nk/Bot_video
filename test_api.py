import requests

url = "https://www.instagram.com/p/DXCcXeuiGXj/"
try:
    response = requests.get(f"https://api.akuari.my.id/downloader/igdl?link={url}")
    print("Status:", response.status_code)
    print("Response:", response.text[:200])
except Exception as e:
    print("Error:", e)
