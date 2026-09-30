import requests

url = "https://www.instagram.com/p/DXCcXeuiGXj/"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}
data = {
    "url": url
}
try:
    response = requests.post("https://api.cobalt.tools/api/json", json=data, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
