import requests, json

COBALT_INSTANCES = [
    "https://cobalt-api.meowing.de",
    "https://cobalt-backend.canine.tools",
    "https://capi.3kh0.net",
]

test_url = "https://www.instagram.com/p/DXCcXeuiGXj/?utm_source=ig_web_button_share_sheet"

for instance in COBALT_INSTANCES:
    print(f"\nTrying {instance}...")
    try:
        resp = requests.post(
            f"{instance}/",
            json={"url": test_url},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response status: {data.get('status')}")
        if data.get('status') == 'picker':
            print(f"Found {len(data['picker'])} items!")
            for item in data['picker']:
                print(f"  - type: {item.get('type')}, url: {item.get('url')[:80]}...")
        else:
            print(f"Full response: {json.dumps(data, indent=2)[:300]}")
    except Exception as e:
        print(f"Error: {e}")
