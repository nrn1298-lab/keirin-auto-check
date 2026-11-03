from urllib.request import Request, urlopen
import re

url = "https://www.keibure.com/42/20261101/1"
req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urlopen(req, timeout=20) as response:
    html = response.read().decode("utf-8", errors="replace")
    print("HTTP:", response.status)

patterns = [
    r"window\.__narabi",
    r"window\.__lineType",
    r"window\.__[A-Za-z_]*",
    r"競走得点",
    r"得点[0-9]",
    r"cars\s*:",
]

for pattern in patterns:
    print("\n=== SEARCH:", pattern, "===")
    matches = list(re.finditer(pattern, html))
    print("Count:", len(matches))
    for m in matches[:8]:
        start = max(0, m.start() - 250)
        end = min(len(html), m.end() + 700)
        snippet = html[start:end]
        snippet = re.sub(r"data:image/[^\s\"']+", "[IMAGE]", snippet)
        print(snippet[:1000])
        print("---")
