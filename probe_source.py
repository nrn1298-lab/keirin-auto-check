from urllib.request import Request, urlopen
import re
import json

url = "https://www.keibure.com/42/20261101/1"
req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urlopen(req, timeout=20) as response:
    html = response.read().decode("utf-8", errors="replace")

print("HTTP:", response.status)

def extract_array(name):
    match = re.search(r"(?:window\.)?" + re.escape(name) + r"\s*=\s*(\[)", html)
    if not match:
        print(name, "NOT FOUND")
        return None
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(html[match.start(1):])
        return value
    except json.JSONDecodeError as e:
        print(name, "JSON ERROR:", e)
        return None

entries = extract_array("__ents")
if isinstance(entries, list):
    print("\n=== RIDERS ===")
    print("Count:", len(entries))
    for entry in entries[:9]:
        print(json.dumps(entry, ensure_ascii=False)[:1500])

print("\n=== LINEUP ===")
match = re.search(r"var __comp\s*=\s*(\[)", html)
if match:
    try:
        comp, _ = json.JSONDecoder().raw_decode(html[match.start(1):])
        print(json.dumps(comp, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print("LINEUP ERROR:", e)
else:
    print("LINEUP NOT FOUND")
print("\n=== SCORE FIELDS ===")
for e in entries or []:
    fields = {k: v for k, v in e.items() if any(w in k.lower() for w in ("score", "point", "tokuten", "rate"))}
    print(e.get("car_no"), e.get("name"), fields)
