from urllib.request import Request, urlopen
from html.parser import HTMLParser
import re

URL = "https://www.keibure.com/42/20261101/1"

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.matches = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs))
        info = " ".join(str(v) for v in attrs.values())
        if any(w in info.lower() for w in ("lineup", "score", "rider", "racecard", "narabi")):
            self.matches.append((tag, info[:160]))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

req = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req, timeout=20) as response:
    html = response.read().decode("utf-8", errors="replace")
    print("HTTP:", response.status)

parser = Inspector()
parser.feed(html)

print("\n=== TABLE STRUCTURE ===")
print("Tables:", len(re.findall(r"<table\\b", html, re.I)))
print("JSON scripts:", len(re.findall(r'application/json', html, re.I)))

print("\n=== POSSIBLE DATA ATTRIBUTES ===")
for tag, info in parser.matches[:35]:
    print(tag, info)

print("\n=== HTML AROUND KEYWORDS ===")
for word in ("競走得点", "並び予想", "lineup", "racecard", "riders"):
    match = re.search(re.escape(word), html, re.I)
    if match:
        start = max(0, match.start() - 180)
        end = min(len(html), match.end() + 400)
        print("\n", word, ":", re.sub(r"\\s+", " ", html[start:end])[:600])
    else:
        print("\n", word, ": NOT FOUND")
