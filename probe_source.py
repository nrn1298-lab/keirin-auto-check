from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

url = "https://www.keibure.com/42/20261101/1"

try:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")
        print("HTTP:", response.status)
        print("HTML length:", len(html))
        for word in ["競走得点", "並び", "出走表"]:
            print(word, ":", word in html)
except (HTTPError, URLError, TimeoutError) as e:
    print("取得失敗:", e)
    raise SystemExit(1)
