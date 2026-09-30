import urllib.request
import urllib.parse
import json

url = "https://www.instagram.com/p/DXCcXeuiGXj/"
req = urllib.request.Request("https://api.cobalt.tools/api/json", data=json.dumps({"url": url}).encode('utf-8'))
req.add_header('Accept', 'application/json')
req.add_header('Content-Type', 'application/json')
req.add_header('User-Agent', 'Mozilla/5.0')
try:
    response = urllib.request.urlopen(req)
    res = json.loads(response.read())
    print("Cobalt Response:", res)
except Exception as e:
    print("Cobalt error:", e)
